"""
Flask routes for LivingOS (state, FCP API, import)
"""

import os
from flask import request, jsonify, Response, current_app, send_from_directory
from src.kernel.mini_os import MiniOS
from src.kernel.fcp_protocol import fcp_pack, fcp_parse

kernel = MiniOS()

def init_routes(app):
    @app.route("/state")
    def state():
        # ліниво формуємо файл стану
        if not os.path.isfile("vr_state.json"):
            kernel.export_state("vr_state.json")
        with open("vr_state.json", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="application/json")

    @app.route("/api/fcp", methods=["POST"])
    def api_fcp():
        data = request.get_json(force=True, silent=True) or {}
        msg = data.get("msg", "")
        try:
            op, args = fcp_parse(msg)
            if op == "T":
                x = float(args["x"]) if "x" in args else None
                y = float(args["y"]) if "y" in args else None
                d = kernel.ingest_text(args.get("text", ""), x=x, y=y)
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
                kernel.clear()
                kernel.export_state("vr_state.json")
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

    # коренева сторінка вже в app (index route) — але лишаємо запасний:
    @app.route("/index.html")
    def index_html():
        return send_from_directory(current_app.static_folder, "index.html")
