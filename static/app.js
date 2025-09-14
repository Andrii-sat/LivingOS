const cvs = document.getElementById('canvas'), ctx = cvs.getContext('2d');
const logEl = document.getElementById('log'), statusEl = document.getElementById('status');
const log = (...a)=>{ const out=a.join(" "); logEl.textContent=out; console.log(out); };

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

// world/camera
let cam = {x:0,y:0,scale:1};
let nodes=[], edges=[], positions={};
let sim = {}; // id -> {x,y,vx,vy,m,seed,pulse}
let particles=[];
let selected=new Set(), lastTapTime=0, lastTapId=null, hoverId=null;

// adjacency
let adj = new Map();
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

async function doExport(){ await apiFCP('E'); log("💾 Exported → vr_state.json"); await syncState(); }
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
async function doClear(){ await apiFCP('CLR'); log("🧹 Cleared"); await syncState(true); }

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
  if (nodes.length < 3) { await demo(); }
  log("🎬 Story Mode: evolving world…");
  let pool = [...nodes.map(n=>n.id)];
  function byDegree(id){ return (adj.get(id)?.size || 0); }
  pool.sort((a,b)=>byDegree(b)-byDegree(a));
  while (pool.length > 1){
    const a = pool.shift();
    let best=null, bestD=1e9;
    for(const cand of pool){
      const da = (adj.get(a)?.has(cand) ? 0 : 1);
      const pa = sim[a], pb = sim[cand];
      const dist = pa&&pb ? Math.hypot(pa.x-pb.x, pa.y-pb.y) : 999;
      const score = da*1000 + dist;
      if (score < bestD) { bestD = score; best = cand; }
    }
    if (!best) break;
    await mergeByIds(a, best);
    await new Promise(r=>setTimeout(r, 700));
    await syncState();
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

// physics
function stepPhysics(){
  const kSpring=0.002, kRepel=2000, damp=0.86, kCluster=0.006, rest=110;

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
    const ext=dist-rest; const ux=dx/dist, uy=dy/dist;
    const F = kSpring*ext + kCluster;
    A.vx += F*ux/A.m; A.vy += F*uy/A.m; B.vx -= F*ux/B.m; B.vy -= F*uy/B.m;
  }
  for(const n of nodes){
    const s=sim[n.id]; if(!s) continue;
    s.vx += (-s.x)*0.0005; s.vy += (-s.y)*0.0005;
  }
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

  // edges (background)
  ctx.lineWidth=1.1; ctx.strokeStyle="rgba(80,120,200,0.35)"; ctx.shadowColor="rgba(100,140,255,0.15)"; ctx.shadowBlur=3;
  for(const e of edges){
    const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    const a=worldToScreen(A), b=worldToScreen(B);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }
  ctx.shadowBlur=0;

  // highlighted links
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
    const s=sim[n.id]; if(!s) continue; const p=worldToScreen(s); const base=10+(n.weight||1)*3;
    const r = base + s.pulse*3;

    // glow
    ctx.beginPath(); ctx.arc(p.x,p.y,r+8,0,Math.PI*2); ctx.fillStyle="rgba(100,160,255,0.08)"; ctx.fill();

    // core
    const grad=ctx.createRadialGradient(p.x,p.y,2,p.x,p.y,r); const col=rndColor(s.seed||0);
    grad.addColorStop(0,col); grad.addColorStop(1,"#0a1230");
    ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle=grad; ctx.fill();

    // label with halo
    ctx.save();
    ctx.font="12px system-ui";
    ctx.lineWidth=3; ctx.strokeStyle="#0b1220"; ctx.fillStyle="#a8b8ff";
    const label=(n.summary||"agent").slice(0,22);
    ctx.strokeText(label, p.x+12, p.y-12);
    ctx.fillText(label, p.x+12, p.y-12);
    ctx.restore();

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
      mergeByIds(lastTapId, id); selected.clear(); dragging=null; btnMerge.disabled = true; return;
    }
    if(selected.has(id)) selected.delete(id);
    else {
      if (selected.size >= 2) selected.clear();
      selected.add(id);
    }
    lastTapTime=now; lastTapId=id;
    btnMerge.disabled = (selected.size !== 2);

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

cvs.addEventListener('pointerup', ev=>{
  dragging=null; cvs.releasePointerCapture(ev.pointerId);
});

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
