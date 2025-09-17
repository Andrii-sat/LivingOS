import os, json
from flask import Blueprint, request, jsonify, Response, send_file

from src.kernel.mini_os import MiniOS
from src.kernel.fcp_protocol import fcp_pack, fcp_parse
from src.kernel.blockchain import Chain
from src.kernel.mining import Miner

bp = Blueprint("api", __name__, url_prefix="/")

kernel = MiniOS()
chain = Chain()
miner = Miner(chain)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_PATH = os.path.join(ROOT, "vr_state.json")

@bp.route("/health")
def health():
    return jsonify({"ok": True})

@bp.route("/version")
def version():
    return jsonify({"name": "LivingOS", "protocol": "frsig://", "api": 1})

@bp.route("/state")
def state():
    if not os.path.isfile(STATE_PATH):
        kernel.export_state(STATE_PATH)
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="application/json")

@bp.route("/api/fcp", methods=["POST"])
def api_fcp():
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("msg", "")
    if not (isinstance(msg, str) and msg.startswith("fcp://") and "|" in msg):
        return jsonify({"resp": fcp_pack("ERR", reason="bad msg")})
    op, args = fcp_parse(msg)
    try:
        if op == "T":
            d = kernel.ingest_text(args.get("text", ""))
            kernel.export_state(STATE_PATH)
            chain.add_tx({"op": "ADD", "desc": d})
            return jsonify({"resp": fcp_pack("OK", d=d)})

        elif op == "M":
            d = kernel.merge(args["a"], args["b"], float(args.get("mix", "0.5")))
            kernel.export_state(STATE_PATH)
            chain.add_tx({"op": "MERGE", "a": args["a"], "b": args["b"]})
            return jsonify({"resp": fcp_pack("OK", d=d)})

        elif op == "E":
            p = kernel.export_state(STATE_PATH)
            chain.add_tx({"op": "EXPORT", "path": p})
            return jsonify({"resp": fcp_pack("OK", path=p)})

        elif op == "CLR":
            kernel.clear()
            kernel.export_state(STATE_PATH)
            chain.add_tx({"op": "CLEAR"})
            return jsonify({"resp": fcp_pack("OK", cleared=1)})

        else:
            return jsonify({"resp": fcp_pack("ERR", reason=f"unknown op {op}")})
    except Exception as e:
        return jsonify({"resp": fcp_pack("ERR", reason=str(e))})

@bp.route("/api/import", methods=["POST"])
def import_state():
    data = request.get_json(force=True, silent=True) or {}
    try:
        kernel.import_state(data, STATE_PATH)
        chain.add_tx({"op": "IMPORT", "size": len(json.dumps(data, ensure_ascii=False))})
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@bp.route("/api/export", methods=["GET"])
def export_file():
    path = kernel.export_state(STATE_PATH)
    return send_file(path, as_attachment=True, download_name="vr_state.json", mimetype="application/json")

@bp.route("/chain", methods=["GET"])
def chain_info():
    return jsonify(chain.info())

@bp.route("/mine", methods=["POST"])
def mine_once():
    body = request.get_json(silent=True) or {}
    max_iters = int(body.get("max_iters", 200000))
    difficulty = int(body.get("difficulty", 2))
    blk = miner.mine_once(max_iters=max_iters, difficulty=difficulty)
    if not blk:
        return jsonify({"mined": False, "reason": "no_solution"}), 200
    return jsonify({
        "mined": True,
        "block": blk.to_dict(),
        "protocol": "frsig://block"
    })
