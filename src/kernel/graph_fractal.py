import time, math, uuid

PHI = (1 + 5 ** 0.5) / 2.0

class GraphFractal:
    def __init__(self):
        self.nodes = {}   # desc -> node
        self.edges = []   # {src, dst, w}
        self.id_index = {}

    def ensure_node(self, desc: str, weight=1.0, summary="", seed=None):
        if desc in self.nodes:
            n = self.nodes[desc]
            n["weight"] = max(n["weight"], float(weight))
            if summary: n["summary"] = summary
            return n["id"]

        nid = str(uuid.uuid4())
        self.nodes[desc] = dict(id=nid, desc=desc, weight=float(weight), summary=summary, seed=seed, t=time.time())
        self.id_index[nid] = desc
        return nid

    def add_edge(self, a_desc: str, b_desc: str, w: float = 1.0):
        if a_desc in self.nodes and b_desc in self.nodes:
            self.edges.append(dict(src=self.nodes[a_desc]["id"], dst=self.nodes[b_desc]["id"], w=float(w)))

    def layout_phi(self):
        nodes = list(self.nodes.values())
        nodes.sort(key=lambda n: (-(n["weight"]), -(n["t"])))
        coords = {}
        for i, n in enumerate(nodes):
            theta = math.radians(137.5) * i
            r = 1.0 + (i ** 0.55) / PHI
            x = r * math.cos(theta); y = r * math.sin(theta)
            coords[n["id"]] = (x, y)
        return coords

    def snapshot(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}
