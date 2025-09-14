# living_os_showtime.py — LivingOS Mini (Showtime Edition)
import os, math, time, json, random, hashlib, uuid
from flask import Flask, request, jsonify, Response

PHI = (1 + 5 ** 0.5) / 2.0
PI = math.pi

def sha256_int32(s: str) -> int:
    h = hashlib.sha256((s or "").encode("utf-8")).hexdigest()
    return int(h[:16], 16) & 0x7FFFFFFF

class FractalSignature:
    def __init__(self, seed: int, size: int = 256, iters: int = 64):
        self.seed = int(seed) & 0x7FFFFFFF
        rng = random.Random(self.seed)
        self.c_re = (rng.random() - 0.5) * 1.5
        self.c_im = (rng.random() - 0.5) * 1.5
        self.zoom = 1.0 + rng.random() * 2.0
        self.ox = (rng.random() - 0.5) * 1.2
        self.oy = (rng.random() - 0.5) * 1.2

    def descriptor(self) -> str:
        return f"frsig://{self.seed}:{self.size}:{self.iters}:{self.c_re:.6f}:{self.c_im:.6f}:{self.zoom:.6f}:{self.ox:.6f}:{self.oy:.6f}"

    @staticmethod
    def from_descriptor(desc: str):
        parts = desc[8:].split(":")
        fs = FractalSignature(int(parts[0]), int(parts[1]), int(parts[2]))
        fs.c_re, fs.c_im, fs.zoom, fs.ox, fs.oy = map(float, parts[3:8])
        return fs

class GraphFractal:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.id_index = {}

    def ensure_node(self, desc: str, summary="", seed=None):
        if desc in self.nodes:
            return self.nodes[desc]["id"]
        nid = str(uuid.uuid4())
        self.nodes[desc] = dict(id=nid, desc=desc, summary=summary, seed=seed, t=time.time())
        self.id_index[nid] = desc
        return nid

    def add_edge(self, a_desc, b_desc):
        if a_desc in self.nodes and b_desc in self.nodes:
            self.edges.append(dict(src=self.nodes[a_desc]["id"], dst=self.nodes[b_desc]["id"]))

    def snapshot(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}

class MiniOS:
    def __init__(self):
        self.graph = GraphFractal()
        self.prev = None

    def ingest_text(self, text: str):
        seed = sha256_int32(text)
        desc = FractalSignature(seed).descriptor()
        self.graph.ensure_node(desc, summary=text[:64], seed=seed)
        if self.prev:
            self.graph.add_edge(self.prev, desc)
        self.prev = desc
        return desc

    def merge(self, desc_a, desc_b):
        sa = FractalSignature.from_descriptor(desc_a).seed
        sb = FractalSignature.from_descriptor(desc_b).seed
        m = (sa ^ (sb << 1)) & 0x7FFFFFFF
        desc = FractalSignature(m).descriptor()
        self.graph.ensure_node(desc, summary=f"merge:{desc_a[:8]}+{desc_b[:8]}", seed=m)
        self.graph.add_edge(desc_a, desc)
        self.graph.add_edge(desc_b, desc)
        self.prev = desc
        return desc

    def export_state(self):
        return {"nodes": list(self.graph.nodes.values()), "edges": self.graph.edges}

# Flask App
app = Flask(__name__)
kernel = MiniOS()

@app.route("/")
def index():
    with open("статичний/index.html", "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")

@app.route("/state")
def state():
    return jsonify(kernel.export_state())

@app.route("/api/add", methods=["POST"])
def api_add():
    text = (request.json or {}).get("text", "")
    return jsonify({"desc": kernel.ingest_text(text)})

@app.route("/api/merge", methods=["POST"])
def api_merge():
    data = request.json or {}
    return jsonify({"desc": kernel.merge(data["a"], data["b"])})

if __name__ == "__main__":
    print("[LivingOS Showtime] Running at http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000)
