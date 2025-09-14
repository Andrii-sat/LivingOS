# src/kernel/mini_os.py
import json, time
from .fractal_signature import FractalSignature, FractalCodec
from .graph_fractal import GraphFractal

class World:
    def __init__(self, name: str):
        self.name = name
        self.graph = GraphFractal()
        self.meta = {"created_at": time.time(), "mode": "REAL"}  # REAL | DREAM | WOW

class MiniOS:
    """
    Multi-world kernel:
      - worlds[name] -> GraphFractal
      - active world
      - world mode (REAL/DREAM/WOW) affects merge labeling
    """
    def __init__(self):
        self.worlds = {}
        self.active = "default"
        self._ensure_world("default")

    # worlds
    def _ensure_world(self, name: str):
        if name not in self.worlds:
            self.worlds[name] = World(name)

    def set_world(self, name: str):
        name = (name or "default").strip()
        self._ensure_world(name)
        self.active = name

    def list_worlds(self):
        return list(self.worlds.keys())

    def set_mode(self, mode: str):
        mode = (mode or "REAL").upper()
        if mode not in ("REAL", "DREAM", "WOW"):
            mode = "REAL"
        self.worlds[self.active].meta["mode"] = mode

    # shorthands
    @property
    def graph(self) -> GraphFractal:
        return self.worlds[self.active].graph

    @property
    def mode(self) -> str:
        return self.worlds[self.active].meta.get("mode", "REAL")

    # ingest
    def ingest_text(self, text: str, x=None, y=None, group=None) -> str:
        enc = FractalCodec.encode_text(text)
        d, s = enc["descriptor"], enc["seed"]
        self.graph.ensure_node(d, weight=1.0, summary=(text or "")[:64], seed=s, x=x, y=y, group=group)
        return d

    def ingest_desc(self, desc: str, summary: str = "", x=None, y=None, group=None) -> str:
        fs = FractalSignature.from_descriptor(desc)
        self.graph.ensure_node(desc, weight=1.0, summary=(summary or "")[:64], seed=fs.seed, x=x, y=y, group=group)
        return desc

    # merge → creates hybrid child and two lineage edges
    def merge(self, desc_a: str, desc_b: str, mix: float = 0.5) -> str:
        sa = FractalSignature.from_descriptor(desc_a).seed
        sb = FractalSignature.from_descriptor(desc_b).seed
        m  = (sa ^ ((sb << 16) | (sb >> 15))) & 0x7FFFFFFF
        m  = (int(mix * 1000003) + (m * 1664525 + 1013904223)) & 0x7FFFFFFF
        md = FractalSignature(m).descriptor()

        # group propagation: if both parents share the same group -> inherit; else form a composite
        ga = self.graph.nodes.get(desc_a, {}).get("group")
        gb = self.graph.nodes.get(desc_b, {}).get("group")
        group = ga if (ga == gb and ga is not None) else f"group:{(ga or 'A')}+{(gb or 'B')}"

        label = "merge" if self.mode == "REAL" else ("dream" if self.mode == "DREAM" else "wow")
        self.graph.ensure_node(md, 1.0, summary=f"{label}:{desc_a[:10]}+{desc_b[:10]}", seed=m, group=group)
        self.graph.add_edge(desc_a, md, w=1.0)
        self.graph.add_edge(desc_b, md, w=1.0)
        return md

    # export / import (active world)
    def export_state(self, path: str = "vr_state.json") -> str:
        w = self.worlds[self.active]
        snap = w.graph.snapshot()
        use_xy = any(("x" in n and "y" in n) for n in snap["nodes"])
        if use_xy:
            positions = { n["id"]: {"x": float(n.get("x",0.0)), "y": float(n.get("y",0.0))} for n in snap["nodes"] }
        else:
            pos = w.graph.layout_phi()
            positions = { k: {"x": v[0] * 80, "y": v[1] * 80} for k, v in pos.items() }  # scale for frontend

        state = {
            "meta": {"t": time.time(), "world": self.active, "mode": self.mode},
            "nodes": snap["nodes"],
            "edges": snap["edges"],
            "positions": positions
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return path

    def import_state(self, payload: dict, path: str = "vr_state.json"):
        name = payload.get("meta", {}).get("world") or self.active
        self._ensure_world(name)
        self.active = name
        w = self.worlds[name]

        nodes = payload.get("nodes") or []
        edges = payload.get("edges") or []
        positions = payload.get("positions") or {}

        w.graph = GraphFractal()
        for n in nodes:
            desc = n["desc"]
            p = positions.get(n["id"], {})
            w.graph.ensure_node(
                desc,
                weight=n.get("weight", 1.0),
                summary=n.get("summary", ""),
                seed=n.get("seed"),
                x=p.get("x"),
                y=p.get("y"),
                group=n.get("group")
            )
        id2desc = { v["id"]: d for d, v in w.graph.nodes.items() }
        for e in edges:
            a = id2desc.get(e.get("src"))
            b = id2desc.get(e.get("dst"))
            if a and b:
                w.graph.add_edge(a, b, w=e.get("w", 1.0))
        self.export_state(path)

    def clear(self):
        name = self.active
        self.worlds[name] = World(name)
