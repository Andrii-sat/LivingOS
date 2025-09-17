// ---------- Canvas & UI ----------
const cvs = document.getElementById("canvas");
const ctx = cvs.getContext("2d");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");

const input = document.getElementById("txt");
const btnAdd = document.getElementById("btn-add");
const btnMerge = document.getElementById("btn-merge");
const btnExport = document.getElementById("btn-export");
const fileImport = document.getElementById("file-import");
const btnClear = document.getElementById("btn-clear");
const btnDemo = document.getElementById("btn-demo");
const btnDemo10k = document.getElementById("btn-demo10k");
const btnStory = document.getElementById("btn-story");
const btnChain = document.getElementById("btn-chain");
const btnMine = document.getElementById("btn-mine");
const autoMergeChk = document.getElementById("auto-merge");
const btnZoomIn = document.getElementById("zoom-in");
const btnZoomOut = document.getElementById("zoom-out");
const btnZoomReset = document.getElementById("zoom-reset");

function log(msg){ logEl.textContent = msg; console.log(msg); }
function resize(){ cvs.width = innerWidth; cvs.height = innerHeight - 210; }
resize(); addEventListener("resize", resize);

// ---------- World state ----------
let nodes=[], edges=[], positions={};
let sim = {};               // id -> {x,y,vx,vy,m,seed,pulse}
let adj = new Map();        // id -> Set(nei)
let selected = new Set();   // selected node ids
let hoverId = null;
let lastTapTime = 0, lastTapId = null;

let cam = {x:0, y:0, scale:1};

// ---------- API helpers ----------
async function api(path, method="GET", body=null){
  const opt = { method, headers:{ "Content-Type":"application/json" } };
  if (body) opt.body = JSON.stringify(body);
  const r = await fetch(path, opt);
  const ct = (r.headers.get("content-type")||"");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  if (ct.includes("application/json")) return await r.json();
  return await r.text();
}
async function fcp(op, kv={}){
  const pairs = Object.entries(kv).map(([k,v])=>`${k}=${encodeURIComponent(v)}`).join(";");
  const msg = `fcp://${op}|${pairs}`;
  const j = await api("/api/fcp", "POST", {msg});
  return j?.resp || "";
}

// ---------- State sync ----------
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
async function refreshState(resetCam=false){
  const s = await api("/state");
  nodes = s.nodes || []; edges = s.edges || []; positions = s.positions || {};
  rebuildAdj();
  for(const n of nodes){
    if(!sim[n.id]){
      const p = positions[n.id] || {x: 0, y: 0};
      sim[n.id] = {x:p.x, y:p.y, vx:0, vy:0, m:1+(n.weight||1)*0.4, seed:n.seed||0, pulse:0};
    }
  }
  if (resetCam){ cam = {x:0,y:0,scale:1}; selected.clear(); hoverId=null; }
  statusEl.textContent = `Agents: ${nodes.length} • Links: ${edges.length}`;
}
function worldToScreen(p){ return {x:(p.x - cam.x)*cam.scale + cvs.width/2, y:(p.y - cam.y)*cam.scale + cvs.height/2}; }
function screenToWorld(p){ return {x:(p.x - cvs.width/2)/cam.scale + cam.x, y:(p.y - cvs.height/2)/cam.scale + cam.y}; }

// ---------- Physics ----------
function stepPhysics(){
  const kRepel=1500, kSpring=0.0012, damp=0.86, rest=110;
  const N = nodes.length, STEP=(N>3000)?3:1;
  for(let i=0;i<N;i+=STEP){
    for(let j=i+1;j<N;j+=STEP){
      const A=sim[nodes[i].id], B=sim[nodes[j].id]; if(!A||!B) continue;
      let dx=B.x-A.x, dy=B.y-A.y; let d2=dx*dx+dy*dy; if(d2<0.01) d2=0.01;
      const f=kRepel/d2; const invd=1/Math.sqrt(d2); dx*=invd; dy*=invd;
      A.vx -= f*dx/A.m; A.vy -= f*dy/A.m; B.vx += f*dx/B.m; B.vy += f*dy/B.m;
    }
  }
  const E=edges.length, E_STEP=(E>6000)?3:1;
  for(let k=0;k<E;k+=E_STEP){
    const e=edges[k]; if(!e) continue;
    const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    let dx=B.x-A.x, dy=B.y-A.y; const dist=Math.hypot(dx,dy)||1;
    const ext=dist-rest; const ux=dx/dist, uy=dy/dist;
    const F=kSpring*ext;
    A.vx += F*ux/A.m; A.vy += F*uy/A.m; B.vx -= F*ux/B.m; B.vy -= F*uy/B.m;
  }
  for(const n of nodes){
    const s=sim[n.id]; if(!s) continue;
    s.vx += (-s.x)*0.00035; s.vy += (-s.y)*0.00035;
    s.vx*=damp; s.vy*=damp; s.x+=s.vx; s.y+=s.vy;
    s.pulse = selected.has(n.id) ? Math.min(1, s.pulse+0.07) : Math.max(0, s.pulse-0.05);
  }
}

// ---------- Render ----------
function rndColor(seed){ return "#"+((seed&0xFFFFFF).toString(16)).padStart(6,"0"); }
function draw(){
  ctx.clearRect(0,0,cvs.width,cvs.height);

  const MAX_EDGES=6000, step=Math.max(1,Math.floor(edges.length/MAX_EDGES));
  ctx.lineWidth=1.05; ctx.strokeStyle="rgba(80,120,200,0.35)";
  for(let i=0;i<edges.length;i+=step){
    const e=edges[i]; const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    const a=worldToScreen(A), b=worldToScreen(B);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }

  if (hoverId || selected.size){
    const focus = hoverId ? new Set([hoverId]) : new Set(selected);
    for(const fid of focus){
      const neigh = adj.get(fid) || new Set();
      const A=sim[fid]; if(!A) continue; const a=worldToScreen(A);
      for(const nid of neigh){
        const B=sim[nid]; if(!B) continue; const b=worldToScreen(B);
        ctx.strokeStyle="rgba(124,246,216,0.9)"; ctx.lineWidth=2;
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
      }
    }
  }

  for(const n of nodes){
    const s=sim[n.id]; if(!s) continue;
    const p=worldToScreen(s); const r=10+(n.weight||1)*3 + s.pulse*3;

    ctx.beginPath(); ctx.arc(p.x,p.y,r+8,0,Math.PI*2); ctx.fillStyle="rgba(100,160,255,0.08)"; ctx.fill();

    const grad=ctx.createRadialGradient(p.x,p.y,2,p.x,p.y,r);
    grad.addColorStop(0,rndColor(s.seed||0)); grad.addColorStop(1,"#0a1230");
    ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle=grad; ctx.fill();

    ctx.save(); ctx.font="12px system-ui"; ctx.lineWidth=3;
    ctx.strokeStyle="#0b1220"; ctx.fillStyle="#a8b8ff";
    const label=(n.summary||"agent").slice(0,22);
    ctx.strokeText(label, p.x+12, p.y-12);
    ctx.fillText(label, p.x+12, p.y-12);
    ctx.restore();

    if(selected.has(n.id) || hoverId===n.id){
      ctx.strokeStyle = hoverId===n.id ? "#60a5fa" : "#7cf6d8";
      ctx.lineWidth=2; ctx.beginPath(); ctx.arc(p.x,p.y,r+3,0,Math.PI*2); ctx.stroke();
    }
  }
}

function loop(){ stepPhysics(); draw(); requestAnimationFrame(loop); }

// ---------- Interactions ----------
function nodeAt(x,y){
  for(let i=nodes.length-1;i>=0;i--){
    const n=nodes[i], s=sim[n.id]; if(!s) continue;
    const p=worldToScreen(s); const r=18;
    const dx=x-p.x, dy=y-p.y;
    if(dx*dx+dy*dy<=r*r) return n.id;
  } return null;
}
let dragging=null, dragOffset={};
cvs.addEventListener("pointermove", ev=>{
  hoverId = nodeAt(ev.clientX, ev.clientY);
});
cvs.addEventListener("pointerdown", ev=>{
  const id=nodeAt(ev.clientX, ev.clientY);
  if(id){
    const now=performance.now();
    if(lastTapId && lastTapId!==id && (now-lastTapTime)<600){
      mergeByIds(lastTapId, id);
      selected.clear(); btnMerge.disabled=true;
      lastTapId=id; lastTapTime=now; return;
    }
    lastTapId=id; lastTapTime=now;

    if(selected.has(id)) selected.delete(id);
    else {
      if(selected.size>=2) selected.clear();
      selected.add(id);
    }
    btnMerge.disabled = (selected.size!==2);

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
cvs.addEventListener("pointermove", ev=>{
  if(dragging && dragging!=="pan"){
    const s=sim[dragging]; const w=screenToWorld({x:ev.clientX,y:ev.clientY});
    s.x=w.x+dragOffset.x; s.y=w.y+dragOffset.y; s.vx=0; s.vy=0;
    positions[dragging] = {x:s.x, y:s.y};
  } else if(dragging==="pan"){
    const dx=(ev.clientX-dragOffset.startX)/cam.scale, dy=(ev.clientY-dragOffset.startY)/cam.scale;
    cam.x=dragOffset.origX-dx; cam.y=dragOffset.origY-dy;
  }
});
cvs.addEventListener("pointerup", ev=>{ dragging=null; cvs.releasePointerCapture(ev.pointerId); });
cvs.addEventListener("wheel", ev=>{
  ev.preventDefault();
  const factor=Math.exp(ev.deltaY*-0.001);
  const before=screenToWorld({x:ev.clientX,y:ev.clientY});
  cam.scale = Math.min(3, Math.max(0.33, cam.scale*factor));
  const after=screenToWorld({x:ev.clientX,y:ev.clientY});
  cam.x+=before.x-after.x; cam.y+=before.y-after.y;
},{passive:false});

btnZoomIn.onclick = ()=>{ cam.scale = Math.min(3, cam.scale*1.15); };
btnZoomOut.onclick = ()=>{ cam.scale = Math.max(0.33, cam.scale/1.15); };
btnZoomReset.onclick = ()=>{ cam = {x:0,y:0,scale:1}; };

// ---------- Actions ----------
async function addAgent(){
  const v = (input.value || "agent").trim();
  const pad=140, sx=Math.random()*(cvs.width-pad*2)+pad, sy=Math.random()*(cvs.height-pad*2)+pad;
  const w = screenToWorld({x:sx,y:sy});
  await fcp("T", {text:v, x:w.x, y:w.y});
  await refreshState();
  log(`➕ Added: ${v}`);
  if (autoMergeChk.checked && selected.size===1){
    const last = nodes[nodes.length-1]?.id;
    if(last){ selected.add(last); btnMerge.disabled=(selected.size!==2); }
    if(selected.size===2) { const [a,b]=[...selected]; await mergeByIds(a,b); selected.clear(); }
  }
}
btnAdd.onclick = addAgent;

async function mergeByIds(idA,idB){
  const a=nodes.find(n=>n.id===idA), b=nodes.find(n=>n.id===idB);
  if(!a||!b) return;
  await fcp("M", {a:a.desc, b:b.desc, mix:0.5});
  await refreshState();
  log(`⚡ Merged: ${(a.summary||"A")} + ${(b.summary||"B")}`);
}
async function mergeAgents(){
  if(selected.size!==2) return;
  const [a,b]=[...selected];
  await mergeByIds(a,b);
  selected.clear(); btnMerge.disabled=true;
}
btnMerge.onclick = mergeAgents;

btnExport.onclick = async ()=>{
  try{
    const res = await fetch("/api/export");
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "vr_state.json"; a.click();
    log("💾 Exported → vr_state.json");
  }catch(e){ log("❌ Export failed: " + e.message); }
};

fileImport.addEventListener("change", async (ev)=>{
  const file = ev.target.files[0]; if(!file) return;
  try{
    const text = await file.text(); const json = JSON.parse(text);
    const r = await api("/api/import","POST", json);
    if(r && r.ok){ log(`📥 Imported OK • nodes: ${(json.nodes||[]).length}`); await refreshState(true); }
    else log("❌ Import error");
  }catch(e){ log("❌ Bad JSON"); }
});

btnClear.onclick = async ()=>{ await fcp("CLR",{}); await refreshState(true); log("🧹 Cleared"); };

btnDemo.onclick = ()=> demo(2000);
btnDemo10k.onclick = ()=> demo(10000);

async function demo(count){
  await btnClear.onclick();
  const batch=200;
  for(let i=0;i<count;i++){
    const label="agent_"+i;
    const pad=140, sx=Math.random()*(cvs.width-pad*2)+pad, sy=Math.random()*(cvs.height-pad*2)+pad;
    const w=screenToWorld({x:sx,y:sy});
    await fcp("T",{text:label,x:w.x,y:w.y});
    if(i%batch===0){ await refreshState(); log(`🌌 Created ${i+1}/${count}`); }
  }
  await refreshState(true);
  log(`✅ DEMO complete: ${count} agents.`);
}

btnStory.onclick = storyMode;
async function storyMode(){
  if (nodes.length < 50) await demo(200);
  log("🎬 Story Mode…");
  const degree = id => (adj.get(id)?.size || 0);
  for(let step=0; step<Math.min(20,nodes.length-1); step++){
    nodes.sort((a,b)=>degree(b.id)-degree(a.id));
    const a=nodes[0]?.id, b=nodes[1]?.id;
    if(a && b){ await mergeByIds(a,b); await new Promise(r=>setTimeout(r,400)); await refreshState(); }
  }
  log("🏁 Story complete.");
}

// blockchain
btnChain.onclick = async ()=>{
  try{
    const j = await api("/chain");
    log(`⛓ Chain • height: ${j.height} • pending: ${j.pending} • tip: ${String(j.tip).slice(0,10)}…`);
  }catch(e){ log("❌ Chain error: "+e.message); }
};
btnMine.onclick = async ()=>{
  try{
    const j = await api("/mine","POST",{max_iters:80000, difficulty:2});
    if(j.mined){ log(`🪙 Mined block #${j.block.index} • ${j.block.hash.slice(0,10)}…`); }
    else log("⛏ No solution this round");
  }catch(e){ log("❌ Mine error: "+e.message); }
};

// auto-mine toggle (використовуй вручну через DevTools за бажанням)
let mineTimer=null;
function toggleAutoMine(){
  if(mineTimer){ clearInterval(mineTimer); mineTimer=null; log("⛏ Auto-mine OFF"); return; }
  mineTimer = setInterval(async ()=>{
    try{
      await api("/mine","POST",{max_iters:50000, difficulty:2});
      const j = await api("/chain");
      statusEl.textContent = `Agents: ${nodes.length} • Links: ${edges.length} • Blocks: ${j.height}`;
    }catch(e){ /* ігноруємо */ }
  }, 1800);
  log("⛏ Auto-mine ON");
}
window.toggleAutoMine = toggleAutoMine;

// zoom buttons
btnZoomIn.onclick = ()=>{ cam.scale = Math.min(3, cam.scale*1.15); };
btnZoomOut.onclick = ()=>{ cam.scale = Math.max(0.33, cam.scale/1.15); };
btnZoomReset.onclick = ()=>{ cam = {x:0,y:0,scale:1}; };

// init
(async()=>{ await refreshState(true); loop(); })();
