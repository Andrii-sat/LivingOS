from flask import request, jsonify, Response
import os, json
from src.kernel.fcp_protocol import fcp_pack, fcp_parse

def init_routes(app, kernel):
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
                d = kernel.ingest_text(args.get("text",""))
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
