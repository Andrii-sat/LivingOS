# src/kernel/graph_fractal.py
import math, time, uuid

PHI = (1 + 5 ** 0.5) / 2.0

class GraphFractal:
    """
    Lightweight in-memory graph:
      nodes: {desc -> {id, desc, weight, summary, seed, t, (x?,y?), group?}}
      edges: [{src, dst, w}]
    """
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.id_index = {}  # id -> desc

    def ensure_node(self, desc: str, weight=1.0, summary="", seed=None, x=None, y=None, group=None):
        if desc in self.nodes:
            n = self.nodes[desc]
            n["weight"] = max(float(weight), n.get("weight", 1.0))
            if summary: n["summary"] = summary
            if x is not None: n["x"] = float(x)
            if y is not None: n["y"] = float(y)
            if group is not None: n["group"] = group
            return n["id"]
        nid = str(uuid.uuid4())
        node = dict(id=nid, desc=desc, weight=float(weight), summary=summary, seed=seed, t=time.time())
        if x is not None: node["x"] = float(x)
        if y is not None: node["y"] = float(y)
        if group is not None: node["group"] = group
        self.nodes[desc] = node
        self.id_index[nid] = desc
        return nid

    def add_edge(self, a_desc: str, b_desc: str, w: float = 1.0):
        if a_desc in self.nodes and b_desc in self.nodes:
            self.edges.append(dict(src=self.nodes[a_desc]["id"], dst=self.nodes[b_desc]["id"], w=float(w)))

    def layout_phi(self):
        """Phyllotaxis layout: compact, stable, no heavy force simulation."""
        nodes = list(self.nodes.values())
        nodes.sort(key=lambda n: (-(n.get("weight",1.0)), -(n.get("t",0.0))))
        coords = {}
        for i, n in enumerate(nodes):
            theta = math.radians(137.5) * i
            r = 1.0 + (i ** 0.55) / PHI
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            coords[n["id"]] = (x, y)
        return coords

    def snapshot(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}
