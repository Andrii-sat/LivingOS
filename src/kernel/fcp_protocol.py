import json, time, urllib.parse as _url

def fcp_pack(op: str, **kwargs) -> str:
    kv = []
    for k,v in kwargs.items():
        if isinstance(v,(dict,list)):
            v = json.dumps(v, ensure_ascii=False)
        kv.append(f"{k}={_url.quote(str(v))}")
    kv.append(f"t={int(time.time())}")
    return f"fcp://{op}|" + ";".join(kv)

def fcp_parse(msg: str):
    head, payload = msg[6:].split("|",1)
    op = head.strip(); args={}
    for part in payload.split(";"):
        if part and "=" in part:
            k,v = part.split("=",1); args[k] = _url.unquote(v)
    return op,args
