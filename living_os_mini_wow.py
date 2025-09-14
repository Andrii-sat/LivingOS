# living_os_mini_wow.py — LivingOS Mini (showtime edition)
# Flask one-file app + canvas UI.
# Нове: MERGE кнопкою + дабл-тап (600мс), DEMO без автозливу, Auto-merge,
# EXPORT/IMPORT, автокластеризація (силова), підсвітка зв’язків (hover/вибір),
# пульсація вибраних, Story Mode (кінематографічне авто-злиття), статус-панель.
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

HTML = r"""<!doctype html><meta charset="utf-8">
<title>LivingOS Mini — Showtime</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<style>
:root{--bg:#050814;--ink:#e6ecff;--sub:#9fb0ff;--line:#213357;--glow:#5aa2ff;--accent:#7cf6d8}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,Segoe UI,Arial}
header{position:sticky;top:0;z-index:5;background:linear-gradient(180deg, rgba(11,16,35,.95), rgba(11,16,35,.85));backdrop-filter:blur(6px);border-bottom:1px solid #111831}
.container{padding:10px 14px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.input{flex:1;min-width:160px;padding:10px 12px;border:1px solid #1a2344;border-radius:10px;background:#0a0f21;color:var(--ink);outline:none}
.btn{padding:10px 14px;border-radius:10px;border:1px solid #1a2344;background:#0a0f21;color:var(--ink);cursor:pointer}
.btn:hover{border-color:#28408a}
.badge{font-size:12px;color:var(--sub);padding:6px 10px;border:1px dashed #2a3a6b;border-radius:999px}
#log{font-size:12px;color:#a8b8ff;padding:6px 14px;border-top:1px solid #111831;background:#070c1a;white-space:pre-wrap}
#canvas{display:block;width:100vw;height:calc(100vh - 172px);touch-action:none;background:radial-gradient(1200px 1000px at 70% 30%, #0f172a 0%, #0b1220 45%, #07101c 100%)}
footer{position:fixed;bottom:0;left:0;right:0;background:rgba(8,12,22,.85);backdrop-filter:blur(6px);border-top:1px solid #111831;padding:6px 12px;color:#aaccff;font-size:12px;display:flex;gap:12px;justify-content:space-between;align-items:center}
footer .tips{display:flex;gap:10px;flex-wrap:wrap}
footer .tip{padding:4px 8px;border:1px dashed #28408a;border-radius:999px}
</style>
<header>
  <div class="container">
    <div class="row">
      <input id="txt" class="input" placeholder="Type text → ADD to birth an agent">
      <button class="btn" id="btn-add">ADD</button>
      <button class="btn" id="btn-merge" disabled>MERGE</button>
      <button class="btn" id="btn-export">EXPORT</button>
      <button class="btn" id="btn-import">IMPORT</button>
      <button class="btn" id="btn-clear">CLEAR</button>
      <button class="btn" id="btn-demo">DEMO</button>
      <label class="badge" style="display:flex;align-items:center;gap:6px;">
        <input type="checkbox" id="ck-auto"> Auto-merge
      </label>
      <button class="btn" id="btn-story">Story Mode</button>
      <button class="btn" id="zoom-in">＋</button>
      <button class="btn" id="zoom-out">－</button>
      <button class="btn" id="zoom-reset">Reset</button>
    </div>
  </div>
</header>
<canvas id="canvas"></canvas>
<pre id="log">Ready.</pre>
<footer>
  <div class="tips">
    <span class="tip">Tap nodes to select (2) → MERGE</span>
    <span class="tip">Double-tap second = quick MERGE</span>
    <span class="tip">Drag = move, Wheel/Pinch = zoom</span>
    <span class="tip">Export/Import = persistent worlds</span>
  </div>
  <div id="status">Agents: 0 • Links: 0</div>
</footer>
<script>
const cvs = document.getElementById('canvas'), ctx = cvs.getContext('2d');
const log = (...a)=>{ const out = a.join(" "); document.getElementById('log').textContent = out; console.log(out); };
function resize(){ cvs.width = innerWidth; cvs.height = innerHeight - 172; } resize(); addEventListener('resize', resize);

// UI elements
const btnAdd = document.getElementById('btn-add');
const btnMerge = document.getElementById('btn-merge');
const btnExport = document.getElementById('btn-export');
const btnImport = document.getElementById('btn-import');
const btnClear = document.getElementById('btn-clear');
const btnDemo = document.getElementById('btn-demo');
const btnStory = document.getElementById('btn-story');
const ckAuto = document.getElementById('ck-auto');
const input = document.getElementById('txt');
const btnZoomIn = document.getElementById('zoom-in');
const btnZoomOut = document.getElementById('zoom-out');
const btnZoomReset = document.getElementById('zoom-reset');
const statusEl = document.getElementById('status');

// camera/world
let cam = {x:0,y:0,scale:1};
let nodes=[], edges=[], positions={};
let sim = {}; // id -> {x,y,vx,vy,m,seed}
let particles=[];
let selected=new Set(), lastTapTime=0, lastTapId=null;
let hoverId=null;

// adjacency (для підсвітки/кластеризації)
let adj = new Map(); // id -> Set(nei)
function rebuildAdj(){
  adj.clear();
  for(const n of nodes) adj.set(n.id, new Set());
  for(const e of edges){
    if(!adj.has(e.src)) adj.set(e.src,new Set());
    if(!adj.has(e.dst)) adj.set(e.dst,new Set());
    adj.get(e.src).add(e.dst);
    adj.get(e.dst).add(e.src);
  }
}

function rndColor(seed){ return '#'+((seed&0xFFFFFF).toString(16)).padStart(6,'0'); }
function worldToScreen(p){ return {x:(p.x - cam.x)*cam.scale + cvs.width/2, y:(p.y - cam.y)*cam.scale + cvs.height/2}; }
function screenToWorld(p){ return {x:(p.x - cvs.width/2)/cam.scale + cam.x, y:(p.y - cvs.height/2)/cam.scale + cam.y}; }

async function apiFCP(op, kv={}) {
  const pairs = Object.entries(kv).map(([k,v]) => `${k}=${encodeURIComponent(v)}`).join(';');
  const msg = `fcp://${op}|${pairs}`;
  const r = await fetch('/api/fcp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg})});
  const j = await r.json(); return j.resp;
}

function randomSpawn(){
  const pad = 140;
  const sx = Math.random()*(cvs.width - pad*2) + pad;
  const sy = Math.random()*(cvs.height - pad*2) + pad + 10;
  const w = screenToWorld({x:sx,y:sy});
  return {x:w.x, y:w.y};
}

async function addText(){
  const v = (input.value || "hello agent").trim();
  const p = randomSpawn();
  const resp = await apiFCP('T', {text: v, x: p.x, y: p.y});
  log("🌌 Created agent:", v);
  await syncState(); burstParticles(lastNodeCenter(), 22);
}

async function doExport(){ const resp = await apiFCP('E'); log("💾 Exported → vr_state.json"); await syncState(); }
async function doImport(){
  const raw = prompt("Paste JSON state (vr_state.json) here:");
  if(!raw) return;
  try{
    const data = JSON.parse(raw);
    const r = await fetch('/import', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
    const j = await r.json();
    log(j.ok ? "📥 Imported OK" : "Import error");
    await syncState(true);
  }catch(e){ alert("Bad JSON"); }
}
async function doClear(){ const resp = await apiFCP('CLR'); log("🧹 Cleared"); await syncState(true); }

async function demo(){
  await doClear();
  const words=["sun","moon","river","forest","code","dream"];
  for (const w of words){
    const p = randomSpawn();
    await apiFCP('T', {text: w, x: p.x, y: p.y});
    await syncState(); burstParticles(lastNodeCenter(), 16);
  }
  log("✨ DEMO world created. Toggle Auto-merge or use MERGE.");
  if (ckAuto.checked){
    const pick = (name)=> nodes.find(n=> (n.summary||"").startsWith(name) || (n.desc||"").includes(name));
    const pairs = [["sun","moon"],["river","forest"],["code","dream"]];
    for (const [A,B] of pairs){
      const a = pick(A), b = pick(B);
      if (a && b) { await mergeByIds(a.id, b.id); await new Promise(r=>setTimeout(r, 600)); }
    }
  }
}

async function storyMode(){
  // серійні злиття у випадковому, але «логічному» порядку
  if (nodes.length < 3) { await demo(); }
  log("🎬 Story Mode: evolving world…");
  // зробимо копію списку, щоб зливати попарно
  let pool = [...nodes.map(n=>n.id)];
  function byDegree(id){ return (adj.get(id)?.size || 0); }
  pool.sort((a,b)=>byDegree(b)-byDegree(a));
  while (pool.length > 1){
    // беремо «найзв’язанішого» + найближчого до нього
    const a = pool.shift();
    let best=null, bestD=1e9;
    for(const cand of pool){
      const da = (adj.get(a)?.has(cand) ? 0 : 1); // пріоритезуємо зв’язаних
      const pa = sim[a], pb = sim[cand];
      const dist = pa&&pb ? Math.hypot(pa.x-pb.x, pa.y-pb.y) : 999;
      const score = da*1000 + dist;
      if (score < bestD) { bestD = score; best = cand; }
    }
    if (!best) break;
    await mergeByIds(a, best);
    await new Promise(r=>setTimeout(r, 700));
    await syncState();
    // оновлюємо пул
    pool = [...nodes.map(n=>n.id)];
    pool.sort((x,y)=>byDegree(y)-byDegree(x));
  }
  log("🏁 Story complete.");
}

// state
async function fetchState(){ const r = await fetch('/state'); return await r.json(); }
async function syncState(reset=false){
  const s = await fetchState(); nodes=s.nodes; edges=s.edges; positions=s.positions;
  rebuildAdj();
  if(reset){ cam.x=0; cam.y=0; cam.scale=1; sim={}; selected.clear(); hoverId=null; }
  for (const n of nodes){
    if(!sim[n.id]){
      const p = positions[n.id] || {x: 0, y: 0};
      sim[n.id] = {x:p.x, y:p.y, vx:0, vy:0, m:1+(n.weight||1)*0.4, seed:n.seed||0, pulse:0};
    }
  }
  statusEl.textContent = `Agents: ${nodes.length} • Links: ${edges.length}`;
}

function lastNodeCenter(){
  if(!nodes.length) return {x:cvs.width/2,y:cvs.height/2};
  const n=nodes[nodes.length-1], s=sim[n.id]; if(!s) return {x:cvs.width/2,y:cvs.height/2};
  return worldToScreen({x:s.x,y:s.y});
}

// physics (з автокластеризацією)
function stepPhysics(){
  const kSpring=0.002, kRepel=2000, damp=0.86, kCluster=0.006, rest=110;

  // відштовхування усіх
  for(let i=0;i<nodes.length;i++){
    for(let j=i+1;j<nodes.length;j++){
      const A=sim[nodes[i].id], B=sim[nodes[j].id]; if(!A||!B) continue;
      let dx=B.x-A.x, dy=B.y-A.y; let d2=dx*dx+dy*dy; if(d2<0.01) d2=0.01;
      const f=kRepel/d2; const invd=1/Math.sqrt(d2); dx*=invd; dy*=invd;
      A.vx -= f*dx/A.m; A.vy -= f*dy/A.m; B.vx += f*dx/B.m; B.vy += f*dy/B.m;
    }
  }
  // пружини по ребрах + кластери (сильніший «магніт» між сусідами)
  for(const e of edges){
    const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    let dx=B.x-A.x, dy=B.y-A.y; const dist=Math.sqrt(dx*dx+dy*dy)||1;
    const ext=dist-rest; const ux=dx/dist, uy=dy/dist;
    const F = kSpring*ext + kCluster;  // трохи сильніше тримаємо
    A.vx += F*ux/A.m; A.vy += F*uy/A.m; B.vx -= F*ux/B.m; B.vy -= F*uy/B.m;
  }
  // легка «гравітація» до центру, щоб не розлітались
  for(const n of nodes){
    const s=sim[n.id]; if(!s) continue;
    s.vx += (-s.x)*0.0005; s.vy += (-s.y)*0.0005;
  }
  // демпфування, інтегрування
  for(const n of nodes){ const s=sim[n.id]; if(!s) continue; s.vx*=damp; s.vy*=damp; s.x+=s.vx; s.y+=s.vy;
    if (selected.has(n.id)) s.pulse = Math.min(1, s.pulse + 0.07); else s.pulse = Math.max(0, s.pulse - 0.05);
  }
}

// particles
function burstParticles(center, n=28, color="#7cf6d8"){
  for(let i=0;i<n;i++){
    const a=(Math.PI*2)*Math.random(), sp=1+Math.random()*3.8;
    particles.push({x:center.x,y:center.y,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp,life:1,color});
  }
}
function drawParticles(){
  for(const p of particles){ p.x+=p.vx; p.y+=p.vy; p.life-=0.02;
    ctx.globalAlpha=Math.max(0,p.life); ctx.fillStyle=p.color||"#7cf6d8";
    ctx.beginPath(); ctx.arc(p.x,p.y,2.2,0,Math.PI*2); ctx.fill();
  }
  ctx.globalAlpha=1.0; particles = particles.filter(p=>p.life>0);
}

// render
function draw(){
  ctx.clearRect(0,0,cvs.width,cvs.height);

  // позаду — «слабкі» лінки
  ctx.lineWidth=1.1; ctx.strokeStyle="rgba(80,120,200,0.35)"; ctx.shadowColor="rgba(100,140,255,0.15)"; ctx.shadowBlur=3;
  for(const e of edges){
    const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    const a=worldToScreen(A), b=worldToScreen(B);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }
  ctx.shadowBlur=0;

  // зверху — підсвітка активних зв’язків
  if (hoverId || selected.size){
    const focus = hoverId ? new Set([hoverId]) : new Set(selected);
    for(const fid of [...focus]){
      const neigh = adj.get(fid) || new Set();
      const A = sim[fid]; if(!A) continue;
      for(const nid of neigh){
        const B = sim[nid]; if(!B) continue;
        const a=worldToScreen(A), b=worldToScreen(B);
        ctx.strokeStyle="rgba(124,246,216,0.9)"; ctx.lineWidth=2;
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
      }
    }
  }

  // ноди
  for(const n of nodes){
    const s=sim[n.id]; if(!s) continue; const p=worldToScreen(s); const base=10+(n.weight||1)*3;
    const r = base + s.pulse*3; // пульс вибраних

    // glow
    ctx.beginPath(); ctx.arc(p.x,p.y,r+8,0,Math.PI*2); ctx.fillStyle="rgba(100,160,255,0.08)"; ctx.fill();
    // core
    const grad=ctx.createRadialGradient(p.x,p.y,2,p.x,p.y,r); const col=rndColor(s.seed||0);
    grad.addColorStop(0,col); grad.addColorStop(1,"#0a1230");
    ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle=grad; ctx.fill();

    // label з ореолом
    ctx.save();
    ctx.font="12px system-ui";
    ctx.lineWidth=3; ctx.strokeStyle="#0b1220"; ctx.fillStyle="#a8b8ff";
    const label=(n.summary||"agent").slice(0,22);
    ctx.strokeText(label, p.x+12, p.y-12);
    ctx.fillText(label, p.x+12, p.y-12);
    ctx.restore();

    // selection рамка / hover
    if(selected.has(n.id) || hoverId===n.id){
      ctx.strokeStyle = hoverId===n.id ? "#60a5fa" : "#7cf6d8";
      ctx.lineWidth=2;
      ctx.beginPath(); ctx.arc(p.x,p.y,r+3,0,Math.PI*2); ctx.stroke();
    }
  }
  drawParticles();
}

// picking
function nodeAt(x,y){
  for(let i=nodes.length-1;i>=0;i--){
    const n=nodes[i], s=sim[n.id]; if(!s) continue;
    const p=worldToScreen(s); const r=10+(n.weight||1)*3+6;
    const dx=x-p.x, dy=y-p.y; if(dx*dx+dy*dy<=r*r) return n.id;
  } return null;
}

// interactions
let dragging=null, dragOffset={x:0,y:0};
cvs.addEventListener('pointermove', ev=>{
  const id=nodeAt(ev.clientX, ev.clientY);
  hoverId = id;
});

cvs.addEventListener('pointerdown', ev=>{
  const id=nodeAt(ev.clientX, ev.clientY);
  if(id){
    const now=performance.now();
    if(selected.has(id) && lastTapId && lastTapId!==id && (now-lastTapTime)<600){
      mergeByIds(lastTapId, id); selected.clear(); dragging=null; return;
    }
    if(selected.has(id)) selected.delete(id); else {
      if (selected.size >= 2) selected.clear();
      selected.add(id);
    }
    lastTapTime=now; lastTapId=id;

    dragging=id;
    const s=sim[id], w=screenToWorld({x:ev.clientX,y:ev.clientY});
    dragOffset.x=s.x-w.x; dragOffset.y=s.y-w.y;
    btnMerge.disabled = (selected.size !== 2);
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
  cam.scale = Math.min(3, Math.max(0.33, cam.scale*factor));
  const after=screenToWorld({x:ev.clientX,y:ev.clientY});
  cam.x+=before.x-after.x; cam.y+=before.y-after.y;
},{passive:false});

btnZoomIn.onclick = () => { cam.scale = Math.min(3, cam.scale*1.15); };
btnZoomOut.onclick = () => { cam.scale = Math.max(0.33, cam.scale/1.15); };
btnZoomReset.onclick = () => { cam.scale=1; cam.x=0; cam.y=0; };

async function mergeByIds(idA,idB){
  const a=nodes.find(n=>n.id===idA), b=nodes.find(n=>n.id===idB);
  if(!a||!b) return;
  const resp = await apiFCP('M', {a:a.desc, b:b.desc, mix:0.5});
  log(`⚡ Merged: ${(a.summary||'A')} + ${(b.summary||'B')}`);
  await syncState();
  burstParticles(lastNodeCenter(), 36, "#60a5fa");
}

// buttons
btnAdd.onclick = addText;
btnMerge.onclick = () => {
  if (selected.size !== 2) return;
  const [a,b] = [...selected]; mergeByIds(a,b); selected.clear(); btnMerge.disabled = true;
};
btnExport.onclick = doExport;
btnImport.onclick = doImport;
btnClear.onclick = doClear;
btnDemo.onclick  = demo;
btnStory.onclick = storyMode;

// main loop
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
            x = float(args["x"]) if "x" in args else None
            y = float(args["y"]) if "y" in args else None
            d = kernel.ingest_text(args.get("text",""), x=x, y=y)
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
