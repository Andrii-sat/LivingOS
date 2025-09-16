import os, json, time, hashlib
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHAIN_PATH = os.path.join(ROOT_DIR, "chain_state.json")
VR_STATE_PATH = os.path.join(ROOT_DIR, "vr_state.json")

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def merkle_like_root(items: List[str]) -> str:
    if not items:
        return sha256_hex("empty")
    layer = sorted(items)
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i+1] if i+1 < len(layer) else layer[i]
            nxt.append(sha256_hex(a + b))
        layer = nxt
    return layer[0]

@dataclass
class Tx:
    txid: str
    kind: str
    payload: Dict[str, Any]
    ts: float

@dataclass
class Block:
    index: int
    ts: float
    parent_hash: str
    frsig_root: str
    txids: List[str]
    difficulty: int
    nonce: int
    hash: str

class Chain:
    def __init__(self, path: str = CHAIN_PATH, vr_state_path: str = VR_STATE_PATH):
        self.path = path
        self.vr_state_path = vr_state_path
        self.mempool: List[Tx] = []
        self.blocks: List[Block] = []
        self.difficulty = 14
        self._load()

    def _load(self):
        if not os.path.isfile(self.path):
            self._genesis()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.difficulty = int(data.get("difficulty", self.difficulty))
            self.blocks = [Block(**b) for b in data.get("blocks",[])]
            self.mempool = []
        except Exception:
            self._genesis()

    def _save(self):
        data = {
            "difficulty": self.difficulty,
            "blocks": [asdict(b) for b in self.blocks],
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _genesis(self):
        g = Block(
            index=0,
            ts=time.time(),
            parent_hash="0"*64,
            frsig_root=sha256_hex("genesis"),
            txids=[],
            difficulty=self.difficulty,
            nonce=0,
            hash=sha256_hex("genesis"),
        )
        self.blocks = [g]
        self.mempool = []
        self._save()

    def add_tx(self, kind: str, payload: Dict[str, Any]) -> Tx:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        txid = sha256_hex(f"{kind}|{body}|{time.time()}")
        tx = Tx(txid=txid, kind=kind, payload=payload, ts=time.time())
        self.mempool.append(tx)
        return tx

    def _collect_fr_inputs(self) -> List[str]:
        if not os.path.isfile(self.vr_state_path):
            return [sha256_hex("novr")]
        try:
            with open(self.vr_state_path, "r", encoding="utf-8") as f:
                s = json.load(f)
            items = []
            for n in s.get("nodes", []):
                desc = n.get("desc","")
                nid  = n.get("id","")
                items.append(sha256_hex(f"{desc}|{nid}"))
            for e in s.get("edges", []):
                items.append(sha256_hex(f"{e.get('src')}->{e.get('dst')}"))
            pos = s.get("positions", {})
            items.append(sha256_hex(json.dumps(pos, sort_keys=True)))
            return items
        except Exception:
            return [sha256_hex("badvr")]

    def compute_frsig_root(self) -> str:
        return merkle_like_root(self._collect_fr_inputs())

    def tip(self) -> Block:
        return self.blocks[-1]

    @staticmethod
    def _target_from_bits(bits: int) -> int:
        return (1 << (256 - bits)) - 1

    def try_mine(self, max_iters: int = 200000, difficulty: Optional[int] = None) -> Optional[Block]:
        if difficulty is None:
            difficulty = self.difficulty
        parent = self.tip()
        root = self.compute_frsig_root()
        txids = [t.txid for t in self.mempool]
        target = Chain._target_from_bits(difficulty)
        base = f"{parent.hash}|{root}|{difficulty}|{len(txids)}|"
        nonce = 0
        best = None
        for _ in range(max_iters):
            s = f"{base}{nonce}"
            h = hashlib.sha256(s.encode("utf-8")).hexdigest()
            if int(h, 16) <= target:
                best = (nonce, h)
                break
            nonce += 1
        if not best:
            return None
        block = Block(
            index=parent.index + 1,
            ts=time.time(),
            parent_hash=parent.hash,
            frsig_root=root,
            txids=txids,
            difficulty=difficulty,
            nonce=best[0],
            hash=best[1],
        )
        self.blocks.append(block)
        self.mempool = []
        self._save()
        return block

    def info(self) -> Dict[str, Any]:
        t = self.tip()
        return {
            "height": t.index,
            "difficulty": self.difficulty,
            "tip": {
                "hash": t.hash,
                "ts": t.ts,
                "frsig_root": t.frsig_root,
                "parent": t.parent_hash,
                "nonce": t.nonce,
                "tx_count": len(t.txids),
            }
        }
