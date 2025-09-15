import json, time
from src.kernel.graph_fractal import GraphFractal, PHI
from src.kernel.fractal_signature import FractalSignature, sha256_int32

class MiniOS:
    def __init__(self):
        self.graph = GraphFractal()
        self.prev = None

    def ingest_text(self, text: str) -> str:
        seed = sha256_int32(text or "")
        desc = FractalSignature(seed).descriptor()
        self.graph.ensure_node(desc, 1.0, summary=(text or "")[:64], seed=seed)
        if self.prev: self.graph.add_edge(self.prev, desc, w=0.8)
        self.prev = desc
        return desc

    def merge(self, desc_a: str, desc_b: str, mix: float = 0.5) -> str:
        sa = FractalSignature.from_descriptor(desc_a).seed
        sb = FractalSignature.from_descriptor(desc_b).seed
        m  = (sa ^ ((sb << 16) | (sb >> 15))) & 0x7FFFFFFF
        md = FractalSignature(m).descriptor()
        self.graph.ensure_node(md, 1.0, summary=f"merge:{desc_a[:8]}+{desc_b[:8]}", seed=m)
        self.graph.add_edge(desc_a, md, w=1.0)
        self.graph.add_edge(desc_b, md, w=1.0)
        self.prev = md
        return md

    def export_state(self, path: str = "vr_state.json") -> str:
        snap = self.graph.snapshot()
        pos = self.graph.layout_phi()
        state = {
            "meta": {"phi": PHI, "t": time.time()},
            "nodes": snap["nodes"],
            "edges": snap["edges"],
            "positions": {k: {"x": v[0], "y": v[1]} for k,v in pos.items()}
        }
        with open(path,"w",encoding="utf-8") as f: json.dump(state,f,ensure_ascii=False,indent=2)
        return path

    def clear(self):
        self.graph = GraphFractal()
        self.prev = None
