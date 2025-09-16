import time, hashlib, json


class Block:
    def __init__(self, index, parent_hash, txs, difficulty=1, nonce=0, ts=None, block_hash=None):
        self.index = index
        self.ts = ts or time.time()
        self.parent = parent_hash  # alias for parent hash
        self.txs = txs or []
        self.difficulty = difficulty
        self.nonce = nonce
        self.hash = block_hash or self.compute_hash()

    def compute_hash(self):
        data = {
            "index": self.index,
            "ts": self.ts,
            "parent": self.parent,
            "txs": self.txs,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
        }
        s = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(s).hexdigest()

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
    def __init__(self):
        self.blocks = []
        self.pending = []  # mempool
        self.create_genesis()

    def create_genesis(self):
        if not self.blocks:
            genesis = Block(index=0, parent_hash="0" * 64, txs=[], difficulty=1, nonce=0)
            self.blocks.append(genesis)

    def add_tx(self, tx_type, payload):
        tx = {"type": tx_type, "payload": payload, "t": time.time()}
        self.pending.append(tx)
        return tx

    def add_block(self, block: Block):
        self.blocks.append(block)

    def tip(self):
        return self.blocks[-1]

    def info(self):
        return {
            "height": len(self.blocks),
            "tip": self.blocks[-1].hash if self.blocks else None,
            "pending": len(self.pending),
        }
