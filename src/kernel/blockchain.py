import time

class Block:
    def __init__(self, index, ts, parent, txs, difficulty, nonce, hash_):
        self.index = index
        self.ts = ts
        self.parent = parent
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
    def __init__(self):
        self.blocks = []
        self.pending = []
        self.genesis()

    def genesis(self):
        genesis_block = Block(
            index=0,
            ts=time.time(),
            parent="0"*64,
            txs=["GENESIS"],
            difficulty=1,
            nonce=0,
            hash_="GENESIS_HASH"
        )
        self.blocks.append(genesis_block)

    def add_tx(self, tx: dict):
        self.pending.append(tx)
        return True

    def add_block(self, block: Block):
        self.blocks.append(block)
        self.pending.clear()

    def info(self):
        return {
            "height": len(self.blocks),
            "tip": self.blocks[-1].hash if self.blocks else None,
            "pending": len(self.pending),
        }
