# src/api/routes.py
from flask import Blueprint, request, jsonify, Response
from src.kernel.mini_os import MiniOS
from src.kernel.fcp_protocol import fcp_pack, fcp_parse

bp = Blueprint("api", __name__)
kernel = MiniOS()

@bp.route("/state", methods=["GET"])
def state():
    """Return current world snapshot."""
    try:
        kernel.export_state("vr_state.json")
        with open("vr_state.json", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="application/json")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/api/fcp", methods=["POST"])
def api_fcp():
    """FCP message interface."""
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("msg", "")
    if not (msg.startswith("fcp://") and "|" in msg):
        return jsonify({"resp": fcp_pack("ERR", reason="bad msg")})

    op, args = fcp_parse(msg)
    try:
        if op == "T":
            d = kernel.ingest_text(args.get("text", ""), 
                                   x=float(args.get("x")) if "x" in args else None,
                                   y=float(args.get("y")) if "y" in args else None,
                                   group=args.get("group"))
            kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", d=d)})

        elif op == "M":
            d = kernel.merge(args["a"], args["b"], float(args.get("mix", "0.5")))
            kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", d=d)})

        elif op == "E":
            p = kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", path=p)})

        elif op == "I":
            kernel.import_state(json.loads(args["payload"]))
            return jsonify({"resp": fcp_pack("OK", imported=1)})

        elif op == "CLR":
            kernel.clear()
            kernel.export_state("vr_state.json")
            return jsonify({"resp": fcp_pack("OK", cleared=1)})

        elif op == "WORLD":
            kernel.set_world(args.get("name", "default"))
            return jsonify({"resp": fcp_pack("OK", active=kernel.active)})

        elif op == "MODE":
            kernel.set_mode(args.get("mode", "REAL"))
            return jsonify({"resp": fcp_pack("OK", mode=kernel.mode)})

        else:
            return jsonify({"resp": fcp_pack("ERR", reason=f"unknown op {op}")})
    except Exception as e:
        return jsonify({"resp": fcp_pack("ERR", reason=str(e))})
