import time
import hashlib

class Block:
    def __init__(self, index, ts, parent_hash, txs, difficulty, nonce, hash_):
        self.index = index
        self.ts = ts
        self.parent = parent_hash   # явно зберігаємо parent
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
        self.pending = []   # мемпул для транзакцій
        self.genesis()

    def genesis(self):
        genesis_block = Block(
            index=1,
            ts=time.time(),
            parent_hash="0"*64,
            txs=["GENESIS"],
            difficulty=1,
            nonce=0,
            hash_="GENESIS_HASH"
        )
        self.blocks.append(genesis_block)

    def add_tx(self, tx):
        """tx = {op, payload}"""
        self.pending.append(tx)
        return True

    def add_block(self, block):
        self.blocks.append(block)
        self.pending.clear()

    def info(self):
        return {
            "height": len(self.blocks),
            "tip": self.blocks[-1].hash if self.blocks else None,
            "pending": len(self.pending),
        }
