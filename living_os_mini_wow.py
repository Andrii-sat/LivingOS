# living_os_mini_wow.py — LivingOS Mini (showtime edition, patched)
# Flask one-file app + canvas UI.
# Додано захисти: безпечний MERGE, пустий ADD, перевірка state.
# Python 3.8+ ; pip install flask

import os, math, time, json, random, hashlib, uuid
from flask import Flask, request, jsonify, Response

PHI = (1 + 5 ** 0.5) / 2.0
PI  = math.pi

def sha256_int32(s: str) -> int:
    h = hashlib.sha256((s or "").encode("utf-8")).hexdigest()
    return int(h[:16], 16) & 0x7FFFFFFF

# ── Fractal seed/signature
class FractalSignature:
    def __init__(self, seed: int, size: int = 256, iters: int = 64):
        self.seed = int(seed) & 0x7FFFFFFF
        self.size = size; self.iters = iters
        rng = random.Random(self.seed)
        self.c_re = (rng.random() - 0.5) * 1.5
        self.c_im = (rng.random() - 0.5) * 1.5
        self.zoom = 1.0 + rng.random() * 2.0
        self.ox = (rng.random() - 0.5) * 1.2
        self.oy = (rng.random() - 0.5) * 1.2
    def descriptor(self) -> str:
        return f"frsig://{self.seed}:{self.size}:{self.iters}:{self.c_re:.6f}:{self.c_im:.6f}:{self.zoom:.6f}:{self.ox:.6f}:{self.oy:.6f}"
    @staticmethod
    def from_descriptor(desc: str) -> "FractalSignature":
        parts = desc[8:].split(":")
        fs = FractalSignature(int(parts[0]), int(parts[1]), int(parts[2]))
        fs.c_re, fs.c_im, fs.zoom, fs.ox, fs.oy = map(float, parts[3:8])
        return fs

class FractalCodec:
    @staticmethod
    def encode_text(text: str) -> dict:
        seed = sha256_int32(text or "")
        return {"seed": seed, "descriptor": FractalSignature(seed).descriptor(), "summary": (text or "")[:120]}

# ── Graph
class GraphFractal:
    def __init__(self):
        self.nodes = {}   # desc -> {id, desc, weight, summary, seed, t, x?, y?}
        self.edges = []   # {src, dst, w}
        self.id_index = {}
    def ensure_node(self, desc: str, weight=1.0, summary="", seed=None, x=None, y=None):
        if desc in self.nodes:
            n = self.nodes[desc]
            n["weight"] = max(n["weight"], float(weight))
            if summary: n["summary"] = summary
            if x is not None: n["x"] = float(x)
            if y is not None: n["y"] = float(y)
            return n["id"]
        nid = str(uuid.uuid4())
        node = dict(id=nid, desc=desc, weight=float(weight), summary=summary, seed=seed, t=time.time())
        if x is not None: node["x"] = float(x)
        if y is not None: node["y"] = float(y)
        self.nodes[desc] = node
        self.id_index[nid] = desc
        return nid
    def add_edge(self, a_desc: str, b_desc: str, w: float = 1.0):
        if a_desc in self.nodes and b_desc in self.nodes:
            self.edges.append(dict(src=self.nodes[a_desc]["id"], dst=self.nodes[b_desc]["id"], w=float(w)))
    def layout_phi(self):
        nodes = list(self.nodes.values())
        nodes.sort(key=lambda n: (-(n.get("weight",1.0)), -(n.get("t",0.0))))
        coords = {}
        for i, n in enumerate(nodes):
            theta = math.radians(137.5) * i
            r = 1.0 + (i ** 0.55) / PHI
            x = (r * math.cos(theta)) * 80.0
            y = (r * math.sin(theta)) * 80.0
            coords[n["id"]] = (x, y)
        return coords
    def snapshot(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}

# ── Kernel
class MiniOS:
    def __init__(self):
        self.graph = GraphFractal()
        self.prev = None
    def ingest_text(self, text: str, x=None, y=None) -> str:
        enc = FractalCodec.encode_text(text)
        d, s = enc["descriptor"], enc["seed"]
        self.graph.ensure_node(d, 1.0, summary=(text or "")[:64], seed=s, x=x, y=y)
        if self.prev: self.graph.add_edge(self.prev, d, w=0.8)
        self.prev = d
        return d
    def merge(self, desc_a: str, desc_b: str, mix: float = 0.5) -> str:
        sa = FractalSignature.from_descriptor(desc_a).seed
        sb = FractalSignature.from_descriptor(desc_b).seed
        m  = (sa ^ ((sb << 16) | (sb >> 15))) & 0x7FFFFFFF
        m  = (int(mix*1000003) + (m * 1664525 + 1013904223)) & 0x7FFFFFFF
        md = FractalSignature(m).descriptor()
        self.graph.ensure_node(md, 1.0, summary=f"merge:{desc_a[:10]}+{desc_b[:10]}", seed=m)
        self.graph.add_edge(desc_a, md, w=1.0)
        self.graph.add_edge(desc_b, md, w=1.0)
        self.prev = md
        return md
    def export_state(self, path: str = "vr_state.json") -> str:
        snap = self.graph.snapshot()
        use_xy = any(("x" in n and "y" in n) for n in snap["nodes"])
        if use_xy:
            positions = { n["id"]: {"x": float(n.get("x",0.0)), "y": float(n.get("y",0.0))} for n in snap["nodes"] }
        else:
            pos = self.graph.layout_phi()
            positions = { k: {"x": v[0], "y": v[1]} for k,v in pos.items() }
        state = {"meta":{"phi":PHI,"t":time.time()},"nodes":snap["nodes"],"edges":snap["edges"],"positions":positions}
        with open(path,"w",encoding="utf-8") as f: json.dump(state,f,ensure_ascii=False,indent=2)
        return path
    def import_state(self, payload: dict, path: str = "vr_state.json"):
        nodes = payload.get("nodes") or []
        edges = payload.get("edges") or []
        positions = payload.get("positions") or {}
        self.graph = GraphFractal()
        for n in nodes:
            desc = n["desc"]
            self.graph.ensure_node(
                desc,
                weight=n.get("weight",1.0),
                summary=n.get("summary",""),
                seed=n.get("seed"),
                x=positions.get(n["id"],{}).get("x"),
                y=positions.get(n["id"],{}).get("y"),
            )
        for e in edges:
            src_id, dst_id = e.get("src"), e.get("dst")
            src_desc = None; dst_desc = None
            for d,v in self.graph.nodes.items():
                if v["id"] == src_id: src_desc = d
                if v["id"] == dst_id: dst_desc = d
            if src_desc and dst_desc:
                self.graph.add_edge(src_desc, dst_desc, w=e.get("w",1.0))
        self.export_state(path)
        self.prev = None
    def clear(self):
        self.graph = GraphFractal()
        self.prev = None

# ── FCP
import urllib.parse as _url
def fcp_pack(op: str, **kwargs) -> str:
    kv = []
    for k,v in kwargs.items():
        if isinstance(v,(dict,list)): v = json.dumps(v, ensure_ascii=False)
        kv.append(f"{k}={_url.quote(str(v))}")
    kv.append(f"t={int(time.time())}")
    return f"fcp://{op}|"+ ";".join(kv)
def fcp_parse(msg: str):
    head, payload = msg[6:].split("|",1)
    op = head.strip(); args={}
    for part in payload.split(";"):
        if part and "=" in part:
            k,v = part.split("=",1); args[k] = _url.unquote(v)
    return op, args

# ── Flask + UI
app = Flask(__name__)
kernel = MiniOS()

@app.route("/")
def index():
    return Response("LivingOS running (patched). Open in browser.", mimetype="text/plain")

@app.route("/state")
def state():
    path = "vr_state.json"
    if not os.path.isfile(path):
        kernel.export_state(path)
    try:
        with open(path,"r",encoding="utf-8") as f:
            return Response(f.read(), mimetype="application/json")
    except Exception:
        kernel.export_state(path)
        with open(path,"r",encoding="utf-8") as f:
            return Response(f.read(), mimetype="application/json")

@app.route("/api/fcp", methods=["POST"])
def api_fcp():
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("msg","")
    if not (msg.startswith("fcp://") and "|" in msg):
        return jsonify({"resp": fcp_pack("ERR", reason="bad msg")})
    op,args = fcp_parse(msg)
    try:
        if op=="T":
            text = (args.get("text") or "").strip()
            if not text:
                return jsonify({"resp": fcp_pack("ERR", reason="empty text")})
            x = float(args["x"]) if "x" in args else None
            y = float(args["y"]) if "y" in args else None
            d = kernel.ingest_text(text, x=x, y=y)
            kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", d=d)})
        elif op=="M":
            a = args.get("a"); b = args.get("b")
            if not a or not b:
                return jsonify({"resp": fcp_pack("ERR", reason="merge needs a & b")})
            d = kernel.merge(a, b, float(args.get("mix","0.5")))
            kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", d=d)})
        elif op=="E":
            p = kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", path=p)})
        elif op=="CLR":
            kernel.clear(); kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", cleared=1)})
        else:
            return jsonify({"resp": fcp_pack("ERR", reason=f"unknown op {op}")})
    except Exception as e:
        return jsonify({"resp": fcp_pack("ERR", reason=str(e))})

@app.route("/import", methods=["POST"])
def import_state():
    data = request.get_json(force=True, silent=True) or {}
    try:
        kernel.import_state(data, "vr_state.json")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

if __name__ == "__main__":
    print("[LivingOS WOW] http://0.0.0.0:5000  → open in your browser")
    app.run(host="0.0.0.0", port=5000, debug=False)
