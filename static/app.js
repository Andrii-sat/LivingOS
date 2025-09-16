// ===== UI scaffolding =====
const cvs = document.getElementById('canvas'), ctx = cvs.getContext('2d');
const log = (...a)=>{ const out=a.join(" "); document.getElementById('log').textContent = out; console.log(out); };
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
const autoMineEl = document.getElementById('auto-mine');
const btnHealth = document.getElementById('btn-health');
const btnVersion = document.getElementById('btn-version');
const btnZoomIn = document.getElementById('zoom-in');
const btnZoomOut = document.getElementById('zoom-out');
const btnZoomReset = document.getElementById('zoom-reset');
const input = document.getElementById('txt');

function resize(){ cvs.width = innerWidth; cvs.height = innerHeight - 172; }
resize(); addEventListener('resize', resize);

// ===== World state =====
let cam = {x:0,y:0,scale:1};
let nodes=[], edges=[], positions={};
let sim = {}; // id -> {x,y,vx,vy,m,seed,pulse}
let particles=[];
let selected=new Set(), lastTapTime=0, lastTapId=null, hoverId=null;
let adj = new Map(); // id -> Set(nei)

// ===== Helpers =====
function rndColor(seed){ return '#'+((seed&0xFFFFFF).toString(16)).padStart(6,'0'); }
function worldToScreen(p){ return {x:(p.x - cam.x)*cam.scale + cvs.width/2, y:(p.y - cam.y)*cam.scale + cvs.height/2}; }
function screenToWorld(p){ return {x:(p.x - cvs.width/2)/cam.scale + cam.x, y:(p.y - cvs.height/2)/cam.scale + cam.y}; }

async function apiFCP(op, kv={}) {
  const pairs = Object.entries(kv).map(([k,v]) => `${k}=${encodeURIComponent(v)}`).join(';');
  const msg = `fcp://${op}|${pairs}`;
  const r = await fetch('/api/fcp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg})});
  const j = await r.json(); return j.resp;
}
async function fetchState(){ const r = await fetch('/state'); return await r.json(); }
async function fetchChain(){ const r = await fetch('/chain'); return await r.json(); }
async function fetchMine(){ const r = await fetch('/mine',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})}); return await r.json(); }
async function fetchHealth(){ const r = await fetch('/health'); return await r.json(); }
async function fetchVersion(){ const r = await fetch('/version'); return await r.json(); }

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

// ===== State sync =====
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

// ===== Physics (cluster-friendly) =====
function stepPhysics(){
  const kSpring=0.0016, kRepel=1600, damp=0.86, kCluster=0.004, rest=110;

  const N = nodes.length;
  const STEP = (N>3000)? 3 : 1;
  for(let i=0;i<N;i+=STEP){
    for(let j=i+1;j<N;j+=STEP){
      const A=sim[nodes[i].id], B=sim[nodes[j].id]; if(!A||!B) continue;
      let dx=B.x-A.x, dy=B.y-A.y; let d2=dx*dx+dy*dy; if(d2<0.01) d2=0.01;
      const f=kRepel/d2; const invd=1/Math.sqrt(d2); dx*=invd; dy*=invd;
      A.vx -= f*dx/A.m; A.vy -= f*dy/A.m; B.vx += f*dx/B.m; B.vy += f*dy/B.m;
    }
  }
  const E = edges.length, E_STEP = (E>6000)? 3 : 1;
  for(let idx=0; idx<E; idx+=E_STEP){
    const e = edges[idx]; if(!e) continue;
    const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    let dx=B.x-A.x, dy=B.y-A.y; const dist=Math.sqrt(dx*dx+dy*dy)||1;
    const ext=dist-rest; const ux=dx/dist, uy=dy/dist;
    const F = kSpring*ext + kCluster;
    A.vx += F*ux/A.m; A.vy += F*uy/A.m; B.vx -= F*ux/B.m; B.vy -= F*uy/B.m;
  }
  for(const n of nodes){
    const s=sim[n.id]; if(!s) continue;
    s.vx += (-s.x)*0.0004; s.vy += (-s.y)*0.0004;
    s.vx*=damp; s.vy*=damp; s.x+=s.vx; s.y+=s.vy;
    if (selected.has(n.id)) s.pulse = Math.min(1, s.pulse + 0.07); else s.pulse = Math.max(0, s.pulse - 0.05);
  }
}

// ===== Particles =====
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

// ===== Rendering =====
function draw(){
  ctx.clearRect(0,0,cvs.width,cvs.height);

  const MAX_EDGES = 6000;
  ctx.lineWidth=1.05; ctx.strokeStyle="rgba(80,120,200,0.35)";
  const step = Math.max(1, Math.floor(edges.length / MAX_EDGES));
  for(let i=0;i<edges.length;i+=step){
    const e=edges[i]; const A=sim[e.src], B=sim[e.dst]; if(!A||!B) continue;
    const a=worldToScreen(A), b=worldToScreen(B);
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }

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

  for(const n of nodes){
    const s=sim[n.id]; if(!s) continue; const p=worldToScreen(s); const base=10+(n.weight||1)*3;
    const r = base + s.pulse*3;

    ctx.beginPath(); ctx.arc(p.x,p.y,r+8,0,Math.PI*2); ctx.fillStyle="rgba(100,160,255,0.08)"; ctx.fill();
    const grad=ctx.createRadialGradient(p.x,p.y,2,p.x,p.y,r); const col=rndColor(s.seed||0);
    grad.addColorStop(0,col); grad.addColorStop(1,"#0a1230");
    ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle=grad; ctx.fill();

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

// ===== Picking & interactions =====
function nodeAt(x,y){
  for(let i=nodes.length-1;i>=0;i--){
    const n=nodes[i], s=sim[n.id]; if(!s) continue;
    const p=worldToScreen(s); const r=10+(n.weight||1)*3+6;
    const dx=x-p.x, dy=y-p.y; if(dx*dx+dy*dy<=r*r) return n.id;
  } return null;
}
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
      btnMerge.disabled = (selected.size !== 2);
    }
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
  if(autoMineEl.checked) await mineOnce();
}

// ===== Actions =====
btnAdd.onclick = async ()=>{
  const v = (input.value || "hello agent").trim();
  const pad = 120, sx = Math.random()*(cvs.width - pad*2) + pad, sy = Math.random()*(cvs.height - pad*2) + pad;
  const w = screenToWorld({x:sx,y:sy});
  await apiFCP("T", { text: v, x: w.x, y: w.y });
  await syncState(); burstParticles(lastNodeCenter(), 22);
  if(autoMineEl.checked) await mineOnce();
};
btnMerge.onclick = ()=>{ if (selected.size===2){ const [a,b]=[...selected]; mergeByIds(a,b); selected.clear(); btnMerge.disabled=true; }};
btnExport.onclick = async ()=>{ await apiFCP('E'); log("💾 Exported → vr_state.json"); };
btnImport.onclick = async ()=>{
  const raw = prompt("Paste vr_state.json here:");
  if(!raw) return;
  try{
    const data = JSON.parse(raw);
    const r = await fetch('/api/import', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
    const j = await r.json(); log(j.ok ? "📥 Imported OK" : "Import error"); await syncState(true);
  }catch(e){ alert("Bad JSON"); }
};
btnClear.onclick = async ()=>{ await apiFCP('CLR'); await syncState(true); log("🧹 Cleared"); if(autoMineEl.checked) await mineOnce(); };

btnDemo.onclick = ()=> demo(2000);
btnDemo10k.onclick = ()=> demo(10000);

async function demo(count){
  await btnClear.onclick();
  const batch=200;
  for(let i=0;i<count;i++){
    const label = "agent_"+i;
    const pad = 120, sx = Math.random()*(cvs.width - pad*2) + pad, sy = Math.random()*(cvs.height - pad*2) + pad;
    const w = screenToWorld({x:sx,y:sy});
    await apiFCP("T", { text: label, x: w.x, y: w.y });
    if (i%batch===0){ await syncState(); log(`🌌 Created ${i+1}/${count}`); }
  }
  await syncState(true);
  log(`✅ DEMO complete: ${count} agents.`);
}

async function storyMode(){
  if (nodes.length < 6) await demo(50);
  log("🎬 Story Mode: evolving…");
  const degree = id => (adj.get(id)?.size || 0);
  for(let step=0; step<Math.min(20,nodes.length-1); step++){
    nodes.sort((a,b)=>degree(b.id)-degree(a.id));
    const a = nodes[0]?.id, b = nodes[1]?.id;
    if(a && b) { await mergeByIds(a,b); await new Promise(r=>setTimeout(r, 500)); await syncState(); }
  }
  log("🏁 Story complete.");
}
btnStory.onclick = storyMode;

// ===== Blockchain buttons =====
btnChain.onclick = async ()=>{
  const info = await fetchChain();
  log("⛓️ PROTOCOL CHAIN:\n" + JSON.stringify(info,null,2));
};

async function mineOnce(){
  const res = await fetchMine();
  if(res.mined){
    log(`⛏️ PROTOCOL: frsig://block/${res.block.index} • hash=${res.block.hash.slice(0,12)}… • txs=${res.block.txs.length}`);
    burstParticles(lastNodeCenter(), 40, "#00ff99");
    await syncState();
  } else {
    log("⏳ PROTOCOL: no solution this round");
  }
}
btnMine.onclick = mineOnce;

// ===== System buttons =====
btnHealth.onclick = async ()=>{
  const r = await fetchHealth();
  log("❤️ HEALTH: " + JSON.stringify(r));
};
btnVersion.onclick = async ()=>{
  const r = await fetchVersion();
  log("ℹ️ VERSION: " + JSON.stringify(r));
};

// ===== Main loop =====
function loop(){ stepPhysics(); draw(); requestAnimationFrame(loop); }
(async()=>{ await syncState(true); loop(); })();
