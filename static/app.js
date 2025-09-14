const cvs = document.getElementById("canvas"), ctx = cvs.getContext("2d");
cvs.width = window.innerWidth; cvs.height = window.innerHeight*0.7;

let nodes = [], edges = [], selected = [];

async function syncState(){
  const r = await fetch("/state"); const s = await r.json();
  nodes = s.nodes; edges = s.edges; draw();
}
async function addAgent(){
  const text = document.getElementById("txt").value || "agent";
  await fetch("/api/add",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})});
  await syncState();
}
async function mergeAgents(){
  if (selected.length < 2) return alert("Виберіть 2 агенти");
  await fetch("/api/merge",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({a:selected[0],b:selected[1]})});
  selected = []; await syncState();
}
function draw(){
  ctx.clearRect(0,0,cvs.width,cvs.height);
  ctx.strokeStyle="#5aa2ff"; ctx.lineWidth=1.5;
  for (const e of edges){
    const a=nodes.find(n=>n.id===e.src), b=nodes.find(n=>n.id===e.dst);
    if(a&&b){ ctx.beginPath(); ctx.moveTo(a.x||50,a.y||50); ctx.lineTo(b.x||150,b.y||150); ctx.stroke(); }
  }
  for (const n of nodes){
    ctx.beginPath(); ctx.arc(n.x||Math.random()*cvs.width, n.y||Math.random()*cvs.height, 12,0,Math.PI*2);
    ctx.fillStyle=selected.includes(n.desc)?"#7cf6d8":"#e6ecff"; ctx.fill();
    ctx.fillStyle="white"; ctx.fillText(n.summary||"agent", (n.x||0)+14,(n.y||0)-14);
  }
}
syncState();
