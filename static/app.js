// ===== LivingOS frontend (force-graph + FCP + blockchain buttons) =====

// Elements
const cvs = document.getElementById('canvas'), ctx = cvs.getContext('2d');
const logEl = document.getElementById('log');
const statusEl = document.getElementById('status');

const btnAdd = document.getElementById('btn-add');
const btnMerge = document.getElementById('btn-merge');
const btnExport = document.getElementById('btn-export');
const btnImport = document.getElementById('btn-import');
const btnClear = document.getElementById('btn-clear');
const btnDemo = document.getElementById('btn-demo');
const btnDemo10k = document.getElementById('btn-demo10k');
const btnStory = document.getElementById('btn-story');
const btnChain = document.getElementById('btn-chain');
const btnMine = document.getElementById('btn-mine');
const btnAutoMine = document.getElementById('btn-auto-mine');
const ckAuto = document.getElementById('ck-auto');
const input = document.getElementById('txt');
const btnZoomIn = document.getElementById('zoom-in');
const btnZoomOut = document.getElementById('zoom-out');
const btnZoomReset = document.getElementById('zoom-reset');

// Utils
function log(...a){ const s=a.join(" "); logEl.textContent = s + "\n" + logEl.textContent; console.log(s); }
function sleep(ms){ return new Promise(r=>setTimeout(r, ms)); }

// Resize canvas
function resize(){ cvs.width = innerWidth; cvs.height = innerHeight - 172; }
resize(); addEventListener('resize', resize);

// World state (from /state)
let nodes = [], edges = [], positions = {};
let sim = {}; // id -> {x,y,vx,vy,m,seed,pulse}
let particles = [];
let selected = new Set(), lastTapTime=0, lastTapId=null;
let hoverId = null;
let adj = new Map();
let autoMining = false;
let autoMineHandle = null;

// API helpers
async function apiFCP(op, kv={}){
  // kv: plain object -> build semicolon-separated k=v pairs
  const parts = Object.entries(kv).map(([k,v]) => `${k}=${encodeURIComponent(v)}`);
  const msg = `fcp://${op}|${parts.join(';')}`;
  try{
    const r = await fetch('/api/fcp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg})});
    const j = await r.json();
    return j.resp;
  }catch(e){
    log("❌ fcp err:", e);
    return null;
  }
}

async function apiPostJson(path, body={}){
  try{
    const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    return await r.json();
  }catch(e){ log("❌ api err:", e); return null; }
}
async function apiGetJson(path){
  try{ const r = await fetch(path); return await r.json(); }catch(e){ log("❌ api err:", e); return null; }
}

// Sync state
async function fetchState(){ const s = await apiGetJson('/state'); return s; }
function rebuildAdj(){
  adj.clear();
  for(const n of nodes) adj.set(n.id, new Set());
  for(const e of edges){
    if(!adj.has(e.src)) adj.set(e.src, new Set());
    if(!adj.has(e.dst)) adj.set(e.dst, new Set());
    adj.get(e.src).add(e.dst);
    adj.get(e.dst).add(e.src);
  }
}

// update UI state from server snapshot
async function syncState(reset=false){
  const s = await fetchState();
  if(!s) { log("❌ Failed to fetch /state"); return; }
  nodes = s.nodes || []; edges = s.edges || []; positions = s.positions || {};
  rebuildAdj();
  if(reset){ sim = {}; selected.clear(); hoverId = null; cam = {x:0,y:0,scale:1}; }
  for(const n of nodes){
    if(!sim[n.id]){
      const p = positions[n.id] || {x:0,y:0};
      sim[n.id] = {x: p.x, y: p.y, vx:0, vy:0, m:1+(n.weight||1)*0.4, seed: n.seed||0, pulse:0};
    } else {
      // if server provided position, trust it
      const p = positions[n.id];
      if(p){ sim[n.id].x = p.x; sim[n.id].y = p.y; }
      sim[n.id].m = 1+(n.weight||1)*0.4;
    }
  }
  // drop sim entries for removed nodes
  for(const id of Object.keys(sim)){
    if(!nodes.find(n=>n.id===id)){ delete sim[id]; selected.delete(id); }
  }
  statusEl.textContent = `Agents: ${nodes.length} • Links: ${edges.length}`;
  btnMerge.disabled = (selected.size !== 2);
}

// camera / interactions
let cam = {x:0,y:0,scale:1};
function worldToScreen(p){ return {x:(p.x - cam.x)*cam.scale + cvs.width/2, y:(p.y - cam.y)*cam.scale + cvs.height/2}; }
function screenToWorld(p){ return {x:(p.x - cvs.width/2)/cam.scale + cam.x, y:(p.y - cvs.height/2)/cam.scale + cam.y}; }

// simple color from seed
function rndColor(seed){ return '#'+((seed&0xFFFFFF).toString(16)).padStart(6,'0'); }

// physics / force layout (lightweight, cluster aware)
function stepPhysics(){
  const kSpring = 0.0016, kRepel = 1500, damp = 0.86, kCluster = 0.004, rest = 110;
  const N = nodes.length;
  const STEP = (N>3000)? 3 : 1;
  for(let i=0;i<N;i+=STEP){
    for(let j=i+1;j<N;j+=STEP){
      const A = sim[nodes[i].id], B = sim[nodes[j].id]; if(!A||!B) continue;
      let dx=B.x-A.x, dy=B.y-A.y; let d2=dx*dx+dy*dy; if(d2<0.01) d2=0.01;
      const f = kRepel/d2; const invd = 1/Math.sqrt(d2); dx*=invd; dy*=invd;
      A.vx -= f*dx/A.m; A.vy -= f*dy/A.m; B.vx += f*dx/B.m; B.vy += f*dy/B.m;
    }
  }
  const E = edges.length, E_STEP = (E>6000)? 3 : 1;
  for(let idx=0; idx<E; idx+=E_STEP){
    const e = edges[idx]; if(!e) continue;
    const A = sim[e.src], B = sim[e.dst]; if(!A||!B) continue;
    let dx=B.x-A.x, dy=B.y-A.y; const dist=Math.sqrt(dx*dx+dy*dy)||1;
    const ext = dist - rest; const ux = dx/dist, uy = dy/dist;
    const F = kSpring*ext + kCluster;
    A.vx += F*ux/A.m; A.vy += F*uy/A.m; B.vx -= F*ux/B.m; B.vy -= F*uy/B.m;
  }
  for(const n of nodes){
    const s = sim[n.id]; if(!s) continue;
    s.vx += (-s.x)*0.0004; s.vy += (-s.y)*0.0004; s.vx*=damp; s.vy*=damp; s.x+=s.vx; s.y+=s.vy;
    if (selected.has(n.id)) s.pulse = Math.min(1, s.pulse + 0.07); else s.pulse = Math.max(0, s.pulse - 0.05);
  }
}

// particles (visual bursts)
function burstParticles(center, n=24, color="#7cf6d8"){
  for(let i=0;i<n;i++){
    const a=(Math.PI*2)*Math.random(), sp=1+Math.random()*3.2;
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

// drawing
function draw(){
  ctx.clearRect(0,0,cvs.width,cvs.height);

  // edges (sampling for large graphs)
  const MAX_EDGES = 6000;
  ctx.lineWidth=1.05; ctx.strokeStyle="rgba(80,120,200,0.35)";
  const step = Math.max(1, Math.floor(edges.length / MAX_EDGES));
  for(let i=0;i<edges.length;i+=step){
    const e = edges[i]; const A = sim[e.src], B = sim[e.dst]; if(!A||!B) continue;
    const a = worldToScreen(A), b = worldToScreen(B);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }

  // highlight neighbors of hover/selection
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

  // nodes
  for(const n of nodes){
    const s = sim[n.id]; if(!s) continue; const p = worldToScreen(s); const base = 10+(n.weight||1)*3;
    const r = base + s.pulse*3;
    // glow
    ctx.beginPath(); ctx.arc(p.x,p.y,r+8,0,Math.PI*2); ctx.fillStyle="rgba(100,160,255,0.08)"; ctx.fill();
    // core gradient
    const grad = ctx.createRadialGradient(p.x,p.y,2,p.x,p.y,r); const col = rndColor(s.seed||0);
    grad.addColorStop(0, col); grad.addColorStop(1, "#0a1230");
    ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle = grad; ctx.fill();
    // label
    ctx.save();
    ctx.font="12px system-ui";
    ctx.lineWidth=3; ctx.strokeStyle="#0b1220"; ctx.fillStyle="#a8b8ff";
    const label = (n.summary || "agent").slice(0,22);
    ctx.strokeText(label, p.x+12, p.y-12);
    ctx.fillText(label, p.x+12, p.y-12);
    ctx.restore();
    // ring if selected/hover
    if(selected.has(n.id) || hoverId===n.id){
      ctx.strokeStyle = hoverId===n.id ? "#60a5fa" : "#7cf6d8";
      ctx.lineWidth=2;
      ctx.beginPath(); ctx.arc(p.x,p.y,r+3,0,Math.PI*2); ctx.stroke();
    }
  }
  drawParticles();
}

// picking + interaction
function nodeAt(x,y){
  for(let i=nodes.length-1;i>=0;i--){
    const n = nodes[i], s = sim[n.id]; if(!s) continue;
    const p = worldToScreen(s); const r = 10 + (n.weight||1)*3 + 6;
    const dx = x-p.x, dy = y-p.y; if(dx*dx+dy*dy <= r*r) return n.id;
  } return null;
}
let dragging = null, dragOffset = {x:0,y:0};
cvs.addEventListener('pointermove', ev=>{
  const id = nodeAt(ev.clientX, ev.clientY);
  hoverId = id;
});
cvs.addEventListener('pointerdown', ev=>{
  const id = nodeAt(ev.clientX, ev.clientY);
  if(id){
    const now = performance.now();
    if(selected.has(id) && lastTapId && lastTapId!==id && (now-lastTapTime)<600){
      // quick double-tap merge
      mergeByIds(lastTapId, id); selected.clear(); dragging = null; return;
    }
    if(selected.has(id)) selected.delete(id); else {
      if(selected.size >= 2) selected.clear();
      selected.add(id);
      btnMerge.disabled = (selected.size !== 2);
    }
    lastTapTime = now; lastTapId = id;

    dragging = id;
    const s = sim[id], w = screenToWorld({x:ev.clientX, y:ev.clientY});
    dragOffset.x = s.x - w.x; dragOffset.y = s.y - w.y;
  } else {
    dragging = "pan";
    dragOffset.startX = ev.clientX; dragOffset.startY = ev.clientY;
    dragOffset.origX = cam.x; dragOffset.origY = cam.y;
  }
  cvs.setPointerCapture(ev.pointerId);
});
cvs.addEventListener('pointermove', ev=>{
  if(dragging && dragging !== "pan"){
    const s = sim[dragging]; const w = screenToWorld({x:ev.clientX,y:ev.clientY});
    s.x = w.x + dragOffset.x; s.y = w.y + dragOffset.y; s.vx = 0; s.vy = 0;
  } else if(dragging === "pan"){
    const dx = (ev.clientX - dragOffset.startX)/cam.scale, dy = (ev.clientY - dragOffset.startY)/cam.scale;
    cam.x = dragOffset.origX - dx; cam.y = dragOffset.origY - dy;
  }
});
cvs.addEventListener('pointerup', ev=>{ dragging = null; cvs.releasePointerCapture(ev.pointerId); });
cvs.addEventListener('wheel', ev=>{
  ev.preventDefault();
  const factor = Math.exp(ev.deltaY*-0.001);
  const before = screenToWorld({x:ev.clientX,y:ev.clientY});
  cam.scale = Math.min(3, Math.max(0.33, cam.scale*factor));
  const after = screenToWorld({x:ev.clientX,y:ev.clientY});
  cam.x += before.x - after.x; cam.y += before.y - after.y;
},{passive:false});

// actions
async function addText(){
  const v = (input.value || "hello agent").trim();
  const p = randomSpawn();
  await apiFCP('T', { text: v, x: p.x, y: p.y });
  log("🌌 Created agent: " + v);
  await syncState();
  burstParticles(lastNodeCenter(), 22);
}

async function doExport(){ const r = await apiFCP('E'); log("💾 Exported → " + JSON.stringify(r)); await syncState(); }
async function doImport(){
  const raw = prompt("Paste JSON state (vr_state.json) here:");
  if(!raw) return;
  try{
    const data = JSON.parse(raw);
    const r = await apiPostJson('/api/import', data);
    log(r && r.ok ? "📥 Imported OK" : "Import error: " + JSON.stringify(r));
    await syncState(true);
  }catch(e){ alert("Bad JSON"); }
}
async function doClear(){ await apiFCP('CLR'); log("🧹 Cleared"); await syncState(true); }

function randomSpawn(){
  const pad = 120;
  const sx = Math.random()*(cvs.width - pad*2) + pad;
  const sy = Math.random()*(cvs.height - pad*2) + pad + 10;
  const w = screenToWorld({x:sx,y:sy});
  return {x:w.x, y:w.y};
}

async function demo(count){
  await doClear();
  const batch = 100; // send in small batches to avoid blocking
  for(let i=0;i<count;i+=batch){
    const ops = [];
    for(let j=0;j<batch && (i+j)<count; j++){
      const idx = i+j;
      const label = `node_${idx}`;
      const p = randomSpawn();
      // fcp uses semicolons between pairs
      await apiFCP('T', { text: label, x: p.x, y: p.y });
    }
    await syncState();
    log(`✨ Created ${Math.min(i+batch,count)}/${count}`);
    // small breathing for mobile
    await sleep(80);
  }
  log(`✅ DEMO complete: ${count} agents.`);
}

async function storyMode(){
  if(nodes.length < 8) await demo(50);
  log("🎬 Story Mode: evolving world…");
  let pool = [...nodes.map(n=>n.id)];
  function deg(id){ return (adj.get(id)?.size || 0); }
  pool.sort((a,b)=>deg(b)-deg(a));
  while(pool.length > 1){
    const a = pool.shift();
    let best = null, bestD=1e9;
    for(const cand of pool){
      const da = (adj.get(a)?.has(cand) ? 0 : 1);
      const pa = sim[a], pb = sim[cand];
      const dist = pa&&pb ? Math.hypot(pa.x-pb.x, pa.y-pb.y) : 999;
      const score = da*1000 + dist;
      if(score < bestD){ bestD = score; best = cand; }
    }
    if(!best) break;
    await mergeByIds(a,best);
    await syncState();
    await sleep(300);
    pool = [...nodes.map(n=>n.id)]; pool.sort((x,y)=>deg(y)-deg(x));
  }
  log("🏁 Story complete.");
}

function lastNodeCenter(){
  if(!nodes.length) return {x:cvs.width/2,y:cvs.height/2};
  const n = nodes[nodes.length-1], s = sim[n.id]; if(!s) return {x:cvs.width/2,y:cvs.height/2};
  return worldToScreen({x:s.x,y:s.y});
}

async function mergeByIds(idA,idB){
  const a = nodes.find(n=>n.id===idA), b = nodes.find(n=>n.id===idB);
  if(!a||!b) return;
  await apiFCP('M', { a: a.desc, b: b.desc, mix: 0.5 });
  log(`⚡ Merged: ${(a.summary||'A')} + ${(b.summary||'B')}`);
  await syncState();
  burstParticles(lastNodeCenter(), 36, "#60a5fa");
}

// CHAIN / MINE
document.getElementById('btn-chain').onclick = async ()=>{
  const r = await apiGetJson('/chain'); log("⛓ Chain: " + JSON.stringify(r));
};
document.getElementById('btn-mine').onclick = async ()=>{
  const r = await apiPostJson('/mine', { max_iters: 200000 });
  log(r.mined ? `✅ Mined block #${r.block.index} ${r.block.hash.slice(0,12)}…` : "⏳ No solution this round");
  await syncState();
};

document.getElementById('btn-auto-mine').onclick = () => {
  autoMining = !autoMining;
  if(autoMining){
    log("⚡ Auto-mining started");
    autoMineHandle = setInterval(async ()=>{
      const r = await apiPostJson('/mine', { max_iters: 200000 });
      if(r && r.mined) log(`✅ Auto-mined block #${r.block.index}`);
      await syncState();
    }, 4000);
  } else {
    log("⏹️ Auto-mining stopped");
    clearInterval(autoMineHandle);
    autoMineHandle = null;
  }
};

// UI buttons bindings (add/merge/export/import/clear/demo)
btnAdd.onclick = addText;
btnExport.onclick = doExport;
btnImport.onclick = doImport;
btnClear.onclick = doClear;
btnDemo.onclick = ()=> demo(2000);
btnDemo10k.onclick = ()=> demo(10000);
btnStory.onclick = storyMode;
document.getElementById('btn-merge').onclick = ()=>{
  if(selected.size !== 2) return;
  const [a,b] = [...selected];
  mergeByIds(a,b);
  selected.clear(); btnMerge.disabled = true;
};

// zoom controls
btnZoomIn.onclick = ()=>{ cam.scale = Math.min(3, cam.scale*1.15); };
btnZoomOut.onclick = ()=>{ cam.scale = Math.max(0.33, cam.scale/1.15); };
btnZoomReset.onclick = ()=>{ cam.scale = 1; cam.x=0; cam.y=0; };

// main loop
function loop(){
  stepPhysics(); draw();
  requestAnimationFrame(loop);
}

(async ()=>{ await syncState(true); loop(); })();
