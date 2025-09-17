import time
import hashlib

class Block:
    def __init__(self, index, ts, parent_hash, txs, difficulty, nonce, hash_):
        self.index = index
        self.ts = ts
        self.parent = parent_hash
        self.txs = txs
        self.difficulty = difficulty
        self.nonce = nonce
        self.hash = hash_

    def to_dict(self):
        return {
            "index": self.index,
            "ts": self.ts,
            "parent": self.parent,
            "txs": self.txs,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "hash": self.hash,
        }

class Chain:
    """
    Простий блокчейн з мемпулом:
    - pending: список незамінених транзакцій
    - add_tx: додає транзакцію (dict або (op,payload))
    - add_block: додає блок і чистить мемпул
    - info: повертає статистику ланцюга
    """
    def __init__(self):
        self.blocks = []
        self.pending = []
        self.genesis()

    def genesis(self):
        ghash = hashlib.sha256(b"genesis").hexdigest()
        genesis_block = Block(
            index=0,
            ts=time.time(),
            parent_hash="0"*64,
            txs=["GENESIS"],
            difficulty=1,
            nonce=0,
            hash_=ghash
        )
        self.blocks.append(genesis_block)

    def add_tx(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], dict):
            tx = args[0]
        elif len(args) == 2:
            kind, payload = args
            tx = {"op": kind, "payload": payload}
        else:
            raise ValueError("add_tx expects (dict) or (kind, payload)")
        tx["ts"] = time.time()
        self.pending.append(tx)
        return True

    def add_block(self, block: Block):
        self.blocks.append(block)
        self.pending.clear()

    def info(self):
        tip_hash = self.blocks[-1].hash if self.blocks else None
        return {
            "height": len(self.blocks),
            "tip": tip_hash,
            "pending": len(self.pending),
        }
