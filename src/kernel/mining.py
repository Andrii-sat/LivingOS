import time
import hashlib
from .blockchain import Block

class Miner:
    def __init__(self, chain):
        self.chain = chain

    def mine_once(self, max_iters=200000, difficulty=2):
        parent = self.chain.blocks[-1]
        txs = list(self.chain.pending)
        if not txs:
            return None

        for nonce in range(max_iters):
            h = hashlib.sha256(f"{parent.hash}{nonce}".encode()).hexdigest()
            if h.startswith("0" * difficulty):
                blk = Block(
                    index=parent.index + 1,
                    ts=time.time(),
                    parent_hash=parent.hash,
                    txs=txs,
                    difficulty=difficulty,
                    nonce=nonce,
                    hash_=h
                )
                self.chain.add_block(blk)
                return blk
        return None
