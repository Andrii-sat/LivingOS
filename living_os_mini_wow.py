# living_os_mini_wow.py
# LivingOS Mini (final): DEMO mode, double-tap MERGE, drag, zoom/pan, particles.
# One-file Flask app + animated canvas UI. Python 3.8+ ; pip install flask

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
        self.nodes = {}   # desc -> {id, desc, weight, summary, seed, t}
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

# ── Kernel
class MiniOS:
    def __init__(self):
        self.graph = GraphFractal()
        self.prev = None
    def ingest_text(self, text: str) -> str:
        enc = FractalCodec.encode_text(text)
        d, s = enc["descriptor"], enc["seed"]
        self.graph.ensure_node(d, 1.0, summary=(text or "")[:64], seed=s)
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
        pos = self.graph.layout_phi()
        state = {"meta":{"phi":PHI,"t":time.time()},
                 "nodes":snap["nodes"], "edges":snap["edges"],
                 "positions":{k:{"x":v[0],"y":v[1]} for k,v in pos.items()}}
        with open(path,"w",encoding="utf-8") as f: json.dump(state,f,ensure_ascii=False,indent=2)
        return path
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

HTML = r"""<!doctype html><meta charset="utf-8">
<title>LivingOS Mini — WOW</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<style>
:root{--bg:#050814;--panel:#0b1023;--ink:#e6ecff;--sub:#9fb0ff;--line:#203059;--glow:#5aa2ff;--accent:#7cf6d8}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,Segoe UI,Arial}
header{position:sticky;top:0;z-index:5;background:linear-gradient(180deg, rgba(11,16,35,.95), rgba(11,16,35,.85));backdrop-filter:blur(6px);border-bottom:1px solid #111831}
.container{padding:10px 14px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.input{flex:1;min-width:160px;padding:10px 12px;border:1px solid #1a2344;border-radius:10px;background:#0a0f21;color:var(--ink);outline:none}
.btn{padding:10px 14px;border-radius:10px;border:1px solid #1a2344;background:#0a0f21;color:var(--ink);cursor:pointer}
.btn:hover{border-color:#28408a}
.badge{font-size:12px;color:var(--sub);padding:6px 10px;border:1px dashed #2a3a6b;border-radius:999px}
#log{font-size:12px;color:#a8b8ff;padding:6px 14px;border-top:1px solid #111831;background:#070c1a}
#canvas{display:block;width:100vw;height:calc(100vh - 136px);touch-action:none}
.legend{display:flex;gap:12px;align-items:center;color:#aaccff;font-size:12px;margin-top:8px;flex-wrap:wrap}
.dot{width:10px;height:10px;border-radius:50%;background:var(--glow);box-shadow:0 0 10px var(--glow),0 0 18px rgba(124,246,216,.2)}
.line{width:18px;height:2px;background:#31467a}
</style>
<header>
  <div class="container">
    <div class="row">
      <input id="txt" class="input" placeholder="Type text → ADD to birth an agent">
      <button class="btn" onclick="addText()">ADD</button>
      <button class="btn" onclick="doExport()">EXPORT</button>
      <button class="btn" onclick="doClear()">CLEAR</button>
      <button class="btn" onclick="demo()">DEMO</button>
    </div>
    <div class="legend">
      <span class="badge">Drag nodes</span>
      <span class="badge">Tap to select</span>
      <span class="badge">Double-tap two selected = MERGE</span>
      <span class="badge">Wheel or pinch to zoom</span>
    </div>
  </div>
</header>
<canvas id="canvas"></canvas>
<pre id="log"></pre>
<script>
const cvs = document.getElementById('canvas'), ctx = cvs.getContext('2d');
const log = (...a)=>{ document.getElementById('log').textContent = a.join(" "); };
function resize(){ cvs.width = innerWidth; cvs.height = innerHeight - 136; } resize(); addEventListener('resize', resize);

// camera/world
let cam = {x:0,y:0,scale:1};
let nodes=[], edges=[], positions={};
let sim = {}; // id -> {x,y,vx,vy,m,seed}
let particles=[];

function rndColor(seed){ return '#'+((seed&0xFFFFFF).toString(16)).padStart(6,'0'); }
function worldToScreen(p){ return {x:(p.x - cam.x)*cam.scale + cvs.width/2, y:(p.y - cam.y)*cam.scale + cvs.height/2}; }
function screenToWorld(p){ return {x:(p.x - cvs.width/2)/cam.scale + cam.x, y:(p.y - cvs.height/2)/cam.scale + cam.y}; }

async function callFCP(msg){
  const r = await fetch('/api/fcp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg})});
  const j = await r.json(); return j.resp;
}
async function addText(){
  const v = document.getElementById('txt').value || "hello agent";
  const resp = await callFCP("fcp://T|text="+encodeURIComponent(v));
  log(resp); await syncState(); burstParticles(lastNodeCenter());
}
async function doExport(){ const resp = await callFCP("fcp://E|"); log(resp); await syncState(); }
async function doClear(){ const resp = await callFCP("fcp://CLR|"); log(resp); await syncState(true); }

async function demo(){
  await doClear();
  const words=["sun","moon","river","forest","code","dream"];
  for (const w of words){ await callFCP("fcp://T|text="+encodeURIComponent(w)); await syncState(); burstParticles(lastNodeCenter(), 22); }
  setTimeout(async()=>{
    if(nodes.length>1){
      const a=nodes[0], b=nodes[1];
      await callFCP("fcp://M|a="+encodeURIComponent(a.desc)+";b="+encodeURIComponent(b.desc)+";mix=0.5");
      await syncState(); burstParticles(lastNodeCenter(), 36);
    }
  }, 1000);
}

// state
async function fetchState(){ const r = await fetch('/state'); return await r.json(); }
async function syncState(reset=false){
  const s = await fetchState(); nodes=s.nodes; edges=s.edges; positions=s.positions;
  if(reset){ cam.x=0; cam.y=0; cam.scale=1; sim={}; selected.clear(); }
  for (const n of nodes){
    if(!sim[n.id]){
      const p = positions[n.id] || {x:0,y:0};
      sim[n.id] = {x:p.x*80, y:p.y*80, vx:0, vy:0, m:1+(n.weight||1)*0.4, seed:n.seed||0};
    }
  }
}
function lastNodeCenter(){
  if(!nodes.length) return {x:cvs.width/2,y:cvs.height/2};
  const n=nodes[nodes.length-1], s=sim[n.id]; if(!s) return {x:cvs.width/2,y:cvs.height/2};
  return worldToScreen({x:s.x,y:s.y});
}

// physics
function stepPhysics(){
  const kSpring=0.002, kRepel=2200, damp=0.85;
  for(let i=0;i<nodes.length;i++){
    for(let j=i+1;j<nodes.length;j++){
      const A=sim[nodes[i].id], B=sim[nodes[j].id]; if(!A||!B) continue;
      let dx=B.x-A.x, dy=B.y-A.y; let d2=dx*dx+dy*dy; if(d2<0.01) d2=0.01;
      const f=kRepel/d2; const invd=1/Math.sqrt(d2); dx*=invd; dy*=invd;
      A.vx -= f*dx/A.m; A.vy -= f*dy/A.m; B.vx += f*dx/B.m; B.vy += f*dy/B.m;
    }
  }
  for(const e of edges){
    const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    let dx=B.x-A.x, dy=B.y-A.y; const dist=Math.sqrt(dx*dx+dy*dy)||1;
    const rest=90; const ext=dist-rest; const F=kSpring*ext; const ux=dx/dist, uy=dy/dist;
    A.vx += F*ux/A.m; A.vy += F*uy/A.m; B.vx -= F*ux/B.m; B.vy -= F*uy/B.m;
  }
  for(const n of nodes){ const s=sim[n.id]; if(!s) continue; s.vx*=damp; s.vy*=damp; s.x+=s.vx; s.y+=s.vy; }
}

// particles
function burstParticles(center, n=24){
  for(let i=0;i<n;i++){
    const a=(Math.PI*2)*Math.random(), sp=1+Math.random()*3;
    particles.push({x:center.x,y:center.y,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp,life:1});
  }
}
function drawParticles(){
  for(const p of particles){ p.x+=p.vx; p.y+=p.vy; p.life-=0.02;
    ctx.globalAlpha=Math.max(0,p.life); ctx.fillStyle="#7cf6d8";
    ctx.beginPath(); ctx.arc(p.x,p.y,2.2,0,Math.PI*2); ctx.fill();
  }
  ctx.globalAlpha=1.0; particles = particles.filter(p=>p.life>0);
}

// render
function draw(){
  ctx.clearRect(0,0,cvs.width,cvs.height);
  // background
  const g = ctx.createLinearGradient(0,0,cvs.width,cvs.height);
  g.addColorStop(0,"#061022"); g.addColorStop(1,"#050a19");
  ctx.fillStyle=g; ctx.fillRect(0,0,cvs.width,cvs.height);

  // edges
  ctx.lineWidth=1.2; ctx.strokeStyle="rgba(80,120,200,0.6)"; ctx.shadowColor="rgba(100,140,255,0.25)"; ctx.shadowBlur=4;
  for(const e of edges){ const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    const a=worldToScreen(A), b=worldToScreen(B);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }
  ctx.shadowBlur=0;

  // nodes
  for(const n of nodes){
    const s=sim[n.id]; if(!s) continue; const p=worldToScreen(s); const r=10+(n.weight||1)*3;
    // glow
    ctx.beginPath(); ctx.arc(p.x,p.y,r+8,0,Math.PI*2); ctx.fillStyle="rgba(100,160,255,0.08)"; ctx.fill();
    // core
    const grad=ctx.createRadialGradient(p.x,p.y,2,p.x,p.y,r); const col=rndColor(s.seed||0);
    grad.addColorStop(0,col); grad.addColorStop(1,"#0a1230");
    ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle=grad; ctx.fill();
    // label
    ctx.fillStyle="#a8b8ff"; ctx.font="12px system-ui"; const label=(n.summary||"agent").slice(0,22); ctx.fillText(label,p.x+12,p.y-12);
    // selection
    if(selected.has(n.id)){ ctx.strokeStyle="#7cf6d8"; ctx.lineWidth=2;
      ctx.beginPath(); ctx.arc(p.x,p.y,r+3,0,Math.PI*2); ctx.stroke();
    }
  }
  drawParticles();
}

// interactions
let dragging=null, dragOffset={x:0,y:0};
let selected=new Set(), lastTapTime=0, lastTapId=null;

function nodeAt(x,y){
  for(let i=nodes.length-1;i>=0;i--){
    const n=nodes[i], s=sim[n.id]; if(!s) continue;
    const p=worldToScreen(s); const r=10+(n.weight||1)*3+6;
    const dx=x-p.x, dy=y-p.y; if(dx*dx+dy*dy<=r*r) return n.id;
  } return null;
}
cvs.addEventListener('pointerdown', ev=>{
  const id=nodeAt(ev.clientX, ev.clientY);
  if(id){
    const now=performance.now();
    if(selected.has(id) && lastTapId && lastTapId!==id && (now-lastTapTime)<350){
      // double-tap on second node => merge selected pair
      mergeByIds(lastTapId, id); selected.clear(); dragging=null; return;
    }
    if(selected.has(id)) selected.delete(id); else selected.add(id);
    lastTapTime=now; lastTapId=id;

    dragging=id;
    const s=sim[id], w=screenToWorld({x:ev.clientX,y:ev.clientY});
    dragOffset.x=s.x-w.x; dragOffset.y=s.y-w.y;
  } else {
    dragging="pan";
    dragOffset.startX=ev.clientX; dragOffset.startY=ev.clientY;
    dragOffset.origX=cam.x; dragOffset.origY=cam.y;
  }
  cvs.setPointerCapture(ev.pointerId);
});
cvs.addEventListener('pointermove', ev=>{
  if(dragging && dragging!=="pan"){
    const s=sim[dragging]; const w=screenToWorld({x:ev.clientX,y:ev.clientY});
    s.x=w.x+dragOffset.x; s.y=w.y+dragOffset.y; s.vx=0; s.vy=0;
  } else if(dragging==="pan"){
    const dx=(ev.clientX-dragOffset.startX)/cam.scale, dy=(ev.clientY-dragOffset.startY)/cam.scale;
    cam.x=dragOffset.origX-dx; cam.y=dragOffset.origY-dy;
  }
});
cvs.addEventListener('pointerup', ev=>{ dragging=null; cvs.releasePointerCapture(ev.pointerId); });
cvs.addEventListener('wheel', ev=>{
  ev.preventDefault();
  const factor=Math.exp(ev.deltaY*-0.001);
  const before=screenToWorld({x:ev.clientX,y:ev.clientY});
  cam.scale*=factor;
  const after=screenToWorld({x:ev.clientX,y:ev.clientY});
  cam.x+=before.x-after.x; cam.y+=before.y-after.y;
},{passive:false});

async function mergeByIds(idA,idB){
  const a=nodes.find(n=>n.id===idA), b=nodes.find(n=>n.id===idB);
  if(!a||!b) return;
  const resp = await callFCP("fcp://M|a="+encodeURIComponent(a.desc)+";b="+encodeURIComponent(b.desc)+";mix=0.5");
  log(resp); await syncState(); burstParticles(lastNodeCenter(), 36);
}

// loop
function loop(){ stepPhysics(); draw(); requestAnimationFrame(loop); }
(async()=>{ await syncState(true); loop(); })();
</script>
"""

@app.route("/")
def index(): return Response(HTML, mimetype="text/html")

@app.route("/state")
def state():
    if not os.path.isfile("vr_state.json"):
        kernel.export_state("vr_state.json")
    with open("vr_state.json","r",encoding="utf-8") as f:
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
            d = kernel.ingest_text(args.get("text",""))
            kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", d=d)})
        elif op=="M":
            d = kernel.merge(args["a"], args["b"], float(args.get("mix","0.5")))
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

if __name__ == "__main__":
    print("[LivingOS WOW] http://0.0.0.0:5000  → open in your browser")
    app.run(host="0.0.0.0", port=5000, debug=False)
