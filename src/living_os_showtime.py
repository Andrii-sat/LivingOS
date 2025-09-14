# src/living_os_showtime.py
# LivingOS Mini (Showtime Edition)
# Flask one-file app + static UI frontend
# Python 3.8+ ; pip install -r requirements.txt

import os, math, time, json, random, hashlib, uuid
from flask import Flask, request, jsonify, Response, send_from_directory

app = Flask(__name__, static_folder="../static", static_url_path="/static")

PHI = (1 + 5 ** 0.5) / 2.0

def sha256_int32(s: str) -> int:
    h = hashlib.sha256((s or "").encode("utf-8")).hexdigest()
    return int(h[:16], 16) & 0x7FFFFFFF

# ── Fractal seed/signature
class FractalSignature:
    def __init__(self, seed: int, size: int = 256, iters: int = 64):
        self.seed = int(seed) & 0x7FFFFFFF
        rng = random.Random(self.seed)
        self.c_re = (rng.random() - 0.5) * 1.5
        self.c_im = (rng.random() - 0.5) * 1.5
    def descriptor(self) -> str:
        return f"frsig://{self.seed}:{self.c_re:.5f}:{self.c_im:.5f}"

class FractalCodec:
    @staticmethod
    def encode_text(text: str) -> dict:
        seed = sha256_int32(text or "")
        return {
            "seed": seed,
            "descriptor": FractalSignature(seed).descriptor(),
            "summary": (text or "")[:64]
        }

# ── Graph
class GraphFractal:
    def __init__(self):
        self.nodes = {}
        self.edges = []
    def ensure_node(self, desc: str, summary=""):
        if desc in self.nodes: return self.nodes[desc]["id"]
        nid = str(uuid.uuid4())
        self.nodes[desc] = dict(id=nid, desc=desc, summary=summary, t=time.time())
        return nid
    def add_edge(self, a_desc, b_desc):
        if a_desc in self.nodes and b_desc in self.nodes:
            self.edges.append(dict(src=self.nodes[a_desc]["id"], dst=self.nodes[b_desc]["id"]))

    def snapshot(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}

# ── Kernel
class MiniOS:
    def __init__(self):
        self.graph = GraphFractal()
        self.prev = None
    def ingest_text(self, text: str) -> str:
        enc = FractalCodec.encode_text(text)
        d = enc["descriptor"]
        self.graph.ensure_node(d, summary=text)
        if self.prev: self.graph.add_edge(self.prev, d)
        self.prev = d
        return d
    def merge(self, a_desc, b_desc):
        merged = f"{a_desc}+{b_desc}"
        self.graph.ensure_node(merged, summary="merge")
        self.graph.add_edge(a_desc, merged)
        self.graph.add_edge(b_desc, merged)
        self.prev = merged
        return merged
    def clear(self):
        self.graph = GraphFractal()
        self.prev = None
    def export_state(self, path="vr_state.json"):
        snap = self.graph.snapshot()
        with open(path,"w",encoding="utf-8") as f: json.dump(snap,f,ensure_ascii=False,indent=2)
        return path

kernel = MiniOS()

# ── Routes
@app.route("/")
def index(): return send_from_directory("../static", "index.html")

@app.route("/state")
def state():
    kernel.export_state("vr_state.json")
    return send_from_directory(".", "vr_state.json")

@app.route("/api/add", methods=["POST"])
def api_add():
    text = request.json.get("text","")
    d = kernel.ingest_text(text)
    kernel.export_state()
    return jsonify({"ok": True, "desc": d})

@app.route("/api/merge", methods=["POST"])
def api_merge():
    a = request.json.get("a")
    b = request.json.get("b")
    d = kernel.merge(a,b)
    kernel.export_state()
    return jsonify({"ok": True, "desc": d})

@app.route("/api/clear", methods=["POST"])
def api_clear():
    kernel.clear()
    return jsonify({"ok": True})

if __name__ == "__main__":
    print("[LivingOS Showtime] running → http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
