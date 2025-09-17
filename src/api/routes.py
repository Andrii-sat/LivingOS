import os, json
from flask import Blueprint, request, jsonify, Response, send_file

from src.kernel.mini_os import MiniOS
from src.kernel.fcp_protocol import fcp_pack, fcp_parse
from src.kernel.blockchain import Chain
from src.kernel.mining import Miner

bp = Blueprint("api", __name__, url_prefix="/")

# kernel + chain
kernel = MiniOS()
chain = Chain()
miner = Miner(chain)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_PATH = os.path.join(ROOT, "vr_state.json")

# ---------- health / version ----------
@bp.route("/health")
def health():
    return jsonify({"ok": True})

@bp.route("/version")
def version():
    return jsonify({"name": "LivingOS", "protocol": "frsig://", "api": 1})

# ---------- state ----------
@bp.route("/state")
def state():
    if not os.path.isfile(STATE_PATH):
        kernel.export_state(STATE_PATH)
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="application/json")

# ---------- FCP ----------
@bp.route("/api/fcp", methods=["POST"])
def api_fcp():
    data = request.get_json(force=True, silent=True) or {}
    msg = data.get("msg", "")
    if not (isinstance(msg, str) and msg.startswith("fcp://") and "|" in msg):
        return jsonify({"resp": fcp_pack("ERR", reason="bad msg")})
    op, args = fcp_parse(msg)
    try:
        if op == "T":
            x = float(args["x"]) if "x" in args and args["x"] != "" else None
            y = float(args["y"]) if "y" in args and args["y"] != "" else None
            d = kernel.ingest_text(args.get("text", ""), x=x, y=y)
            kernel.export_state(STATE_PATH)
            chain.add_tx({"op": "ADD", "desc": d, "x": x, "y": y})
            return jsonify({"resp": fcp_pack("OK", d=d)})

        elif op == "M":
            d = kernel.merge(args["a"], args["b"], float(args.get("mix", "0.5")))
            kernel.export_state(STATE_PATH)
            chain.add_tx({"op": "MERGE", "a": args["a"], "b": args["b"], "mix": float(args.get("mix", 0.5))})
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

# ---------- Import / Export ----------
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

# ---------- Chain info ----------
@bp.route("/chain", methods=["GET"])
def chain_info():
    return jsonify(chain.info())

# ---------- Mining ----------
@bp.route("/mine", methods=["POST"])
def mine_once():
    body = request.get_json(silent=True) or {}
    max_iters = int(body.get("max_iters", 200000))
    difficulty = body.get("difficulty")
    if difficulty is not None:
        difficulty = int(difficulty)
    blk = miner.mine_once(max_iters=max_iters, difficulty=difficulty if difficulty is not None else 2)
    if not blk:
        return jsonify({"mined": False, "reason": "no_solution"}), 200
    return jsonify({
        "mined": True,
        "block": blk.to_dict(),
        "protocol": "frsig://block"
    })
