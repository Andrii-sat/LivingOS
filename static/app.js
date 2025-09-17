const btnAdd = document.getElementById("btnAdd");
const btnMerge = document.getElementById("btnMerge");
const btnClear = document.getElementById("btnClear");
const btnExport = document.getElementById("btnExport");
const btnChain = document.getElementById("btnChain");
const btnMine = document.getElementById("btnMine");
const btnAutoMine = document.getElementById("btnAutoMine");

const inputText = document.getElementById("inputText");
const inputA = document.getElementById("inputA");
const inputB = document.getElementById("inputB");
const outputBox = document.getElementById("output");

let autoMineInterval = null;

async function apiCall(url, method = "GET", body = null) {
  let opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  try { return await res.json(); }
  catch { return { error: "No JSON from server", status: res.status }; }
}

btnAdd.onclick = async () => {
  let text = (inputText.value || "").trim();
  if (!text) return;
  const msg = { msg: `fcp://T|text=${encodeURIComponent(text)}` };
  const r = await apiCall("/api/fcp", "POST", msg);
  outputBox.innerText = JSON.stringify(r, null, 2);
};

btnMerge.onclick = async () => {
  let a = (inputA.value || "").trim();
  let b = (inputB.value || "").trim();
  if (!a || !b) return;
  const msg = { msg: `fcp://M|a=${encodeURIComponent(a)};b=${encodeURIComponent(b)};mix=0.5` };
  const r = await apiCall("/api/fcp", "POST", msg);
  outputBox.innerText = JSON.stringify(r, null, 2);
};

btnClear.onclick = async () => {
  const msg = { msg: "fcp://CLR|" };
  const r = await apiCall("/api/fcp", "POST", msg);
  outputBox.innerText = JSON.stringify(r, null, 2);
};

btnExport.onclick = () => {
  const link = document.createElement("a");
  link.href = "/api/export";
  link.download = "vr_state.json";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

btnChain.onclick = async () => {
  const r = await apiCall("/chain");
  outputBox.innerText = "CHAIN INFO:\n" + JSON.stringify(r, null, 2);
};

btnMine.onclick = async () => {
  const r = await apiCall("/mine", "POST", { max_iters: 50000, difficulty: 2 });
  outputBox.innerText = "MINED BLOCK:\n" + JSON.stringify(r, null, 2);
};

btnAutoMine.onclick = () => {
  if (autoMineInterval) {
    clearInterval(autoMineInterval);
    autoMineInterval = null;
    outputBox.innerText = "⛔ Auto Mining stopped.";
    btnAutoMine.innerText = "Start Auto Mining";
  } else {
    autoMineInterval = setInterval(async () => {
      const r = await apiCall("/mine", "POST", { max_iters: 20000, difficulty: 2 });
      if (r && r.mined) {
        outputBox.innerText = "✅ Auto-mined block:\n" + JSON.stringify(r, null, 2);
      }
    }, 5000);
    btnAutoMine.innerText = "Stop Auto Mining";
    outputBox.innerText = "⚡ Auto Mining started...";
  }
};
