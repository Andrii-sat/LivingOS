"""
MiniOS — kernel: ingest, merge, export/import, clear
"""

import json
import time
from .fractal_signature import FractalSignature, FractalCodec
from .graph_fractal import GraphFractal

class MiniOS:
    def __init__(self):
        self.graph = GraphFractal()
        self.prev = None

    def ingest_text(self, text: str, x=None, y=None) -> str:
        enc = FractalCodec.encode_text(text)
        d, s = enc["descriptor"], enc["seed"]
        self.graph.ensure_node(d, weight=1.0, summary=(text or "")[:64], seed=s, x=x, y=y)
        if self.prev:
            self.graph.add_edge(self.prev, d, w=0.8)
        self.prev = d
        return d

    def merge(self, desc_a: str, desc_b: str, mix: float = 0.5) -> str:
        sa = FractalSignature.from_descriptor(desc_a).seed
        sb = FractalSignature.from_descriptor(desc_b).seed
        # детерміністичне «гібридне» змішування
        m  = (sa ^ ((sb << 16) | (sb >> 15))) & 0x7FFFFFFF
        m  = (int(mix * 1000003) + (m * 1664525 + 1013904223)) & 0x7FFFFFFF
        md = FractalSignature(m).descriptor()
        self.graph.ensure_node(md, 1.0, summary=f"merge:{desc_a[:10]}+{desc_b[:10]}", seed=m)
        self.graph.add_edge(desc_a, md, w=1.0)
        self.graph.add_edge(desc_b, md, w=1.0)
        self.prev = md
        return md

    def export_state(self, path: str = "vr_state.json") -> str:
        snap = self.graph.snapshot()
        # якщо хтось уже має x/y — використовуємо їх, інакше розклад
        use_xy = any(("x" in n and "y" in n) for n in snap["nodes"])
        if use_xy:
            positions = { n["id"]: {"x": float(n.get("x", 0.0)), "y": float(n.get("y", 0.0))} for n in snap["nodes"] }
        else:
            pos = self.graph.layout_phi()
            positions = { k: {"x": v[0], "y": v[1]} for k, v in pos.items() }
        state = {
            "meta": {"t": time.time()},
            "nodes": snap["nodes"],
            "edges": snap["edges"],
            "positions": positions
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return path

    def import_state(self, payload: dict, path: str = "vr_state.json"):
        nodes = payload.get("nodes") or []
        edges = payload.get("edges") or []
        positions = payload.get("positions") or {}

        self.graph = GraphFractal()
        # відновлюємо ноди з позиціями
        for n in nodes:
            desc = n["desc"]
            pos = positions.get(n["id"], {})
            self.graph.ensure_node(
                desc,
                weight=n.get("weight", 1.0),
                summary=n.get("summary", ""),
                seed=n.get("seed"),
                x=pos.get("x"),
                y=pos.get("y"),
            )
        # мапимо edges по id -> desc
        id_to_desc = { v["id"]: d for d, v in self.graph.nodes.items() }
        for e in edges:
            src_desc = id_to_desc.get(e.get("src"))
            dst_desc = id_to_desc.get(e.get("dst"))
            if src_desc and dst_desc:
                self.graph.add_edge(src_desc, dst_desc, w=e.get("w", 1.0))

        self.export_state(path)
        self.prev = None

    def clear(self):
        self.graph = GraphFractal()
        self.prev = None
