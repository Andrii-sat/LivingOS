# 🌌 LivingOS — Fractal Internet of Living Agents

> **License:** MIT — © 2025 Andrii (Andrii-sat). See [LICENSE](./LICENSE).  
> You may use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies under the MIT terms.

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8%2B-informational)
![Flask](https://img.shields.io/badge/Flask-3.x-black)
![Status](https://img.shields.io/badge/Status-Prototype%20%2F%20Showtime-success)
![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen)

**Not another chatbot.** LivingOS is a new paradigm — a *living internet* where data becomes **agents**.  
Create agents from text, merge them into hybrids, and watch multidimensional worlds emerge in real time.

---

## Table of Contents
- [Why LivingOS](#-why-livingos)
- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Quick Start (Desktop)](#-quick-start-desktop)
- [Quick Start (Android / Termux)](#-quick-start-android--termux)
- [Usage Guide](#-usage-guide)
- [HTTP API](#-http-api)
- [Data Model](#-data-model)
- [Roadmap](#-roadmap)
- [Troubleshooting](#-troubleshooting)
- [Ethics & Safety](#-ethics--safety)
- [Author](#-author)
- [License](#-license)

---

## 🚀 Why LivingOS
- **Lightweight & accessible** — runs on a laptop, or even on an Android tablet via Termux.
- **Fractal-native** — agents use deterministic *fractal signatures* for compact identity & linking.
- **Composable worlds** — MERGE agents to spawn hybrids and emergent structures.
- **Hackathon-ready** — simple setup, wow-visuals, and a clear demo flow.

---

## ✨ Features

### Core (ships in this repo)
- 🌀 **Fractal agents** — each agent has a deterministic signature `frsig://…` derived from text.
- 🔗 **MERGE** — combine two agents; a hybrid child is created with lineage edges.
- 🧹 **CLEAR** — reset the world to start fresh.
- 🖥️ **Canvas UI** — interactive node/edge visualization in a clean dark theme.
- ⚙️ **Simple REST API** — `POST /api/add`, `POST /api/merge`, `POST /api/clear`, `GET /state`.

### Showtime layer (enhanced demo UX)
- 💡 Selection **glow & pulse**; link highlighting on hover/selection.
- 🌍 Force-based **physics layout** (repulsion, springs, soft clustering, gravity).
- ✨ **Particle bursts** on create/merge for cinematic feedback.
- 🎬 **Story Mode** — scripted, cinematic auto-merging sequence.
- 📦 **Export / Import** world state (`vr_state.json`).
- 🌐 **On-chain anchoring (stubs)** — Solana/Coral-style integration points.

> The repo structure is ready for the Showtime layer; visuals/UX can be toggled purely in frontend without breaking the API.

---

## 🧠 Architecture

- **FractalSignature** — per-text deterministic seed → compact descriptor `frsig://{seed}:{…}`.
- **GraphFractal** — in-memory graph (nodes/edges) with lineage; snapshot served via `/state`.
- **MiniOS kernel** — `ingest_text`, `merge`, and exports; extendable with NLP/LLM bridges.
- **Flask backend** — REST endpoints + static UI serving.
- **Canvas frontend** — draws nodes/edges, handles interactions, demo/story flows.

---

## 📁 Project Structure

> Folder names are intentionally **Ukrainian**. If you prefer English (`src/`, `static/`), rename and adjust paths.

LivingOS/ ├─ джерело/ │  └─ living_os_showtime.py      # Flask backend + kernel (entrypoint) ├─ статичний/ │  ├─ index.html                 # UI shell │  ├─ style.css                  # styles (Showtime-ready) │  └─ app.js                     # client logic & demo/story flows ├─ tests/ │  └─ test_basic.py              # minimal test stub ├─ requirements.txt              # Flask dependency ├─ .gitignore ├─ README.md └─ LICENSE

---

## ⚡ Quick Start (Desktop)

```bash
git clone https://github.com/Andrii-sat/LivingOS.git
cd LivingOS
pip install -r requirements.txt
python джерело/living_os_showtime.py

Open in browser: http://127.0.0.1:5000


---

📱 Quick Start (Android / Termux)

pkg update && pkg upgrade -y
pkg install python git -y
pip install --upgrade pip

git clone https://github.com/Andrii-sat/LivingOS.git
cd LivingOS
pip install -r requirements.txt
python джерело/living_os_showtime.py

Open your mobile browser at http://127.0.0.1:5000 (or the Termux IP printed in console).


---

🕹️ Usage Guide

Create an agent

Type text → press ADD. A node with that text’s signature appears.


Merge two agents

Select two agents (UI) → press MERGE.
A hybrid child node is created; edges connect parents → child.


Reset

Press CLEAR to wipe the world.


Demo / Story

Press DEMO to auto-spawn a world (e.g., sun, moon, river, forest, code, dream).

Press Story Mode to watch a cinematic evolution (if enabled in UI).



---

🔌 HTTP API

GET  /state            → returns current graph snapshot (nodes, edges)
POST /api/add          → body: { "text": "..." }          → { "desc": "frsig://..." }
POST /api/merge        → body: { "a": "<desc>", "b": "<desc>" } → { "desc": "frsig://..." }
POST /api/clear        → clears graph → { "ok": true }

desc is a descriptor string (e.g., frsig://12345678:...).

You can store desc and re-use it later to wire custom workflows.



---

🗃️ Data Model

Node

{
  "id": "uuid",
  "desc": "frsig://<seed>:…",
  "summary": "user text (truncated)",
  "seed": 123456789,
  "t": 1736940000
}

Edge

{
  "src": "<node-id>",
  "dst": "<node-id>"
}

Fractal signature

frsig://{seed}:{...}

Deterministic per text via a SHA-256-based 32-bit seed → stable identity/visual.


---

🔮 Roadmap

[x] Minimal kernel (ingest/merge), REST API, Canvas UI

[x] DEMO world

[x] Showtime hooks in UI (glow, pulse, particles, physics)

[ ] Story Mode polish & presets

[ ] Export / Import world state

[ ] Multiuser rooms (ROOM/JOIN)

[ ] AI Bridge (LLMs as agents)

[ ] Solana anchoring & NFT agents; Coral-style registry



---

🛠️ Troubleshooting

Server runs, but browser shows nothing

Use http://127.0.0.1:5000 (or the IP Termux printed).

Some Android browsers block localhost; try Chrome/Firefox mobile.


pip or dependencies fail on Termux

pip install --upgrade pip

Then pip install -r requirements.txt


Port conflict

Change port in джерело/living_os_showtime.py:

app.run(host="0.0.0.0", port=8080, debug=False)


Stuck state

Press CLEAR in the UI, or restart the server.



---

🧭 Ethics & Safety

LivingOS embraces ethical freedom of choice and transparent behavior.
It is intended for beneficial, creative and research use.
Avoid harmful, deceptive or privacy-violating deployments.


---

👤 Author

Andrii (Andrii-sat)

Mechanical Engineer & AI Experimenter

Focus: AI systems, fractal computing, blockchain integrations (Solana), educational tooling

GitHub: Andrii-sat



---

📜 License

MIT License — © 2025 Andrii (Andrii-sat). See LICENSE for full text.

> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction…
