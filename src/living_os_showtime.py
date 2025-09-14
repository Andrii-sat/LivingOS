# src/living_os_showtime.py
# LivingOS Showtime — lightweight edition for Termux/mobile
# Optimized: 30 FPS, physics step every 60ms, syncState only on actions.

import os, time, json
from flask import Flask, request, jsonify, Response
from src.kernel.fractal_signature import FractalSignature, sha256_int32
from src.kernel.graph_fractal import GraphFractal
from src.kernel.mini_os import MiniOS
from src.kernel.fcp_protocol import fcp_pack, fcp_parse

app = Flask(__name__)
kernel = MiniOS()

# ── UI HTML loader (serves static/index.html)
@app.route("/")
def index():
    path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")

# ── serve static files (css/js)
@app.route("/static/<path:fname>")
def static_files(fname):
    path = os.path.join(os.path.dirname(__file__), "..", "static", fname)
    if not os.path.isfile(path):
        return Response("Not found", status=404)
    with open(path, "r", encoding="utf-8") as f:
        if fname.endswith(".css"):
            return Response(f.read(), mimetype="text/css")
        if fname.endswith(".js"):
            return Response(f.read(), mimetype="application/javascript")
        return Response(f.read())

# ── state endpoint
@app.route("/state")
def state():
    if not os.path.isfile("vr_state.json"):
        kernel.export_state("vr_state.json")
    with open("vr_state.json", "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="application/json")

# ── FCP API
@app.route("/api/fcp", methods=["POST"])
def api_fcp():
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("msg", "")
    if not (msg.startswith("fcp://") and "|" in msg):
        return jsonify({"resp": fcp_pack("ERR", reason="bad msg")})
    op, args = fcp_parse(msg)
    try:
        if op == "T":
            d = kernel.ingest_text(args.get("text", ""))
            kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", d=d)})
        elif op == "M":
            d = kernel.merge(args["a"], args["b"], float(args.get("mix", "0.5")))
            kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", d=d)})
        elif op == "E":
            p = kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", path=p)})
        elif op == "CLR":
            kernel.clear(); kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", cleared=1)})
        elif op == "WORLD":
            # just tag the world name in meta
            snap = kernel.graph.snapshot()
            world = args.get("name", "default")
            state = {
                "meta": {"world": world, "t": time.time()},
                "nodes": snap["nodes"], "edges": snap["edges"],
                "positions": kernel.graph.layout_phi()
            }
            with open("vr_state.json","w",encoding="utf-8") as f: json.dump(state,f,indent=2)
            return jsonify({"resp": fcp_pack("OK", world=world)})
        else:
            return jsonify({"resp": fcp_pack("ERR", reason=f"unknown op {op}")})
    except Exception as e:
        return jsonify({"resp": fcp_pack("ERR", reason=str(e))})

if __name__ == "__main__":
    print("[LivingOS Showtime] running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
