# src/kernel/fcp_protocol.py
import time, json, urllib.parse as _url

def fcp_pack(op: str, **kwargs) -> str:
    """Build an fcp:// message payload as a compact string."""
    kv = []
    for k, v in kwargs.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        kv.append(f"{k}={_url.quote(str(v))}")
    kv.append(f"t={int(time.time())}")
    return "fcp://" + op + "|" + ";".join(kv)

def fcp_parse(msg: str):
    """Parse fcp:// message back to (op, args)."""
    if not (msg.startswith("fcp://") and "|" in msg):
        raise ValueError("Bad FCP message")
    head, payload = msg[6:].split("|", 1)
    op = head.strip()
    args = {}
    for part in payload.split(";"):
        if part and "=" in part:
            k, v = part.split("=", 1)
            args[k] = _url.unquote(v)
    return op, args
