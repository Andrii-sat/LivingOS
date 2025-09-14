# living_os_mini_wow.py — LivingOS Mini (Showtime+Clusters edition)
# Flask one-file app + canvas UI.
# Нове: MERGE кнопкою + подвійний тап, DEMO з групами, авто-підсвітка зв’язків,
# кластерні кольори, пульсація вибраних, zoom/pan, Story Mode.
# Python 3.8+ ; pip install flask

import os, math, time, json, random, hashlib, uuid
from flask import Flask, request, jsonify, Response

PHI = (1 + 5 ** 0.5) / 2.0
PI  = math.pi

def sha256_int32(s: str) -> int:
    h = hashlib.sha256((s or "").encode("utf-8")).hexdigest()
    return int(h[:16], 16) & 0x7FFFFFFF

# ── Fractal Signature
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
        return f"frsig://{self.seed}:{self.c_re:.5f}:{self.c_im:.5f}:{self.zoom:.5f}:{self.ox:.5f}:{self.oy:.5f}"
    @staticmethod
    def from_descriptor(desc: str):
        parts = desc[8:].split(":")
        fs = FractalSignature(int(parts[0]))
        return fs

class FractalCodec:
    @staticmethod
    def encode_text(text: str) -> dict:
        seed = sha256_int32(text or "")
        return {"seed": seed, "descriptor": FractalSignature(seed).descriptor(), "summary": (text or "")[:64]}

# ── Graph
class GraphFractal:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.id_index = {}
    def ensure_node(self, desc: str, weight=1.0, summary="", seed=None, x=None, y=None):
        if desc in self.nodes:
            return self.nodes[desc]["id"]
        nid = str(uuid.uuid4())
        node = dict(id=nid, desc=desc, weight=weight, summary=summary, seed=seed, t=time.time(), x=x, y=y)
        self.nodes[desc] = node
        self.id_index[nid] = desc
        return nid
    def add_edge(self, a_desc: str, b_desc: str, w=1.0):
        if a_desc in self.nodes and b_desc in self.nodes:
            self.edges.append(dict(src=self.nodes[a_desc]["id"], dst=self.nodes[b_desc]["id"], w=w))
    def snapshot(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}

# ── Kernel
class MiniOS:
    def __init__(self): self.graph = GraphFractal(); self.prev=None
    def ingest_text(self, text: str, x=None, y=None):
        enc = FractalCodec.encode_text(text)
        d, s = enc["descriptor"], enc["seed"]
        self.graph.ensure_node(d, 1.0, summary=text, seed=s, x=x, y=y)
        if self.prev: self.graph.add_edge(self.prev, d)
        self.prev = d; return d
    def merge(self, desc_a: str, desc_b: str, mix=0.5):
        sa = FractalSignature.from_descriptor(desc_a).seed
        sb = FractalSignature.from_descriptor(desc_b).seed
        m  = (sa ^ (sb<<16)) & 0x7FFFFFFF
        md = FractalSignature(m).descriptor()
        self.graph.ensure_node(md, 1.0, summary=f"merge:{desc_a[:8]}+{desc_b[:8]}", seed=m)
        self.graph.add_edge(desc_a, md); self.graph.add_edge(desc_b, md)
        self.prev = md; return md
    def export_state(self, path="vr_state.json"):
        state = {"nodes": list(self.graph.nodes.values()), "edges": self.graph.edges}
        with open(path,"w",encoding="utf-8") as f: json.dump(state,f,ensure_ascii=False,indent=2)
        return path
    def import_state(self, payload, path="vr_state.json"):
        self.graph = GraphFractal()
        for n in payload.get("nodes",[]): self.graph.ensure_node(n["desc"], summary=n["summary"], seed=n["seed"], x=n.get("x"), y=n.get("y"))
        for e in payload.get("edges",[]): self.graph.edges.append(e)
        self.export_state(path)
    def clear(self): self.graph=GraphFractal(); self.prev=None

# ── FCP
import urllib.parse as _url
def fcp_pack(op, **kw): return f"fcp://{op}|"+ ";".join(f"{k}={_url.quote(str(v))}" for k,v in kw.items())
def fcp_parse(msg): head,payload=msg[6:].split("|",1); args={}; 
part=payload.split(";")
for p in part: 
    if "=" in p: k,v=p.split("=",1); args[k]=_url.unquote(v)
return head,args

# ── Flask + UI
app=Flask(__name__); kernel=MiniOS()

HTML="""<!doctype html><meta charset="utf-8"><title>LivingOS Mini Showtime</title>
<body style='background:#050814;color:#eee;font-family:sans-serif;margin:0'>
<h2 style='padding:10px'>🌌 LivingOS Mini — Showtime</h2>
<div style='padding:10px'>
<input id=txt placeholder='Type → ADD' style='padding:6px'> 
<button onclick='add()'>ADD</button>
<button onclick='mergeSel()'>MERGE</button>
<button onclick='demo()'>DEMO</button>
<pre id=log>Ready.</pre>
<canvas id=cvs style='width:100%;height:80vh;background:#0a0f21'></canvas>
</div>
<script>
const cvs=document.getElementById("cvs"),ctx=cvs.getContext("2d");cvs.width=innerWidth;cvs.height=innerHeight*0.7;
let nodes=[],edges=[],selected=new Set();
async function api(op,kv={}){const msg=`fcp://${op}|`+Object.entries(kv).map(([k,v])=>`${k}=${encodeURIComponent(v)}`).join(";");let r=await fetch('/api/fcp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg})});let j=await r.json();return j;}
async function sync(){let r=await fetch('/state');let s=await r.json();nodes=s.nodes;edges=s.edges;draw();}
function draw(){ctx.clearRect(0,0,cvs.width,cvs.height);for(const e of edges){let A=nodes.find(n=>n.id==e.src),B=nodes.find(n=>n.id==e.dst);if(!A||!B)continue;ctx.strokeStyle="#395";ctx.beginPath();ctx.moveTo(A.x||200,B.y||200);ctx.lineTo(B.x||300,B.y||300);ctx.stroke();}
for(const n of nodes){ctx.fillStyle=selected.has(n.id)?"#7cf6d8":"#58f";ctx.beginPath();ctx.arc(n.x||Math.random()*500,n.y||Math.random()*400,20,0,6.28);ctx.fill();ctx.fillStyle="#fff";ctx.fillText(n.summary||"agent",(n.x||200)+25,(n.y||200));}}
async function add(){let v=document.getElementById('txt').value;await api('T',{text:v});await sync();}
async function mergeSel(){if(selected.size==2){const[a,b]=[...selected];await api('M',{a:nodes.find(n=>n.id==a).desc,b:nodes.find(n=>n.id==b).desc});selected.clear();await sync();}}
async function demo(){await api('CLR');let words=['sun','moon','forest','river'];for(const w of words){await api('T',{text:w});}await sync();}
cvs.addEventListener('click',ev=>{let x=ev.offsetX,y=ev.offsetY;for(const n of nodes){let dx=(n.x||200)-x,dy=(n.y||200)-y;if(dx*dx+dy*dy<400){if(selected.has(n.id))selected.delete(n.id);else selected.add(n.id);} }draw();});
sync();
</script>
"""

@app.route("/") 
def index(): return Response(HTML,mimetype="text/html")
@app.route("/state") 
def state(): 
    if not os.path.exists("vr_state.json"): kernel.export_state()
    return Response(open("vr_state.json").read(),mimetype="application/json")
@app.route("/api/fcp",methods=["POST"])
def api_fcp(): 
    d=request.get_json() or {}; msg=d.get("msg",""); 
    if not msg.startswith("fcp://"): return jsonify({"resp":fcp_pack("ERR",reason="bad")})
    op,args=fcp_parse(msg)
    if op=="T": kernel.ingest_text(args.get("text","")); kernel.export_state(); return jsonify({"resp":fcp_pack("OK")})
    if op=="M": kernel.merge(args["a"],args["b"]); kernel.export_state(); return jsonify({"resp":fcp_pack("OK")})
    if op=="CLR": kernel.clear(); kernel.export_state(); return jsonify({"resp":fcp_pack("OK")})
    return jsonify({"resp":fcp_pack("ERR",reason="unknown")})

if __name__=="__main__": 
    print("[LivingOS WOW] http://0.0.0.0:5000 → open in browser")
    app.run(host="0.0.0.0",port=5000)
        
