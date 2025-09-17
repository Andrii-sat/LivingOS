import time
import hashlib
from .blockchain import Block

class Miner:
    def __init__(self, chain):
        self.chain = chain

    def mine_once(self, max_iters=200000, difficulty=2):
        #
        if not self.chain.pending:
            return None

        parent = self.chain.blocks[-1]
        txs = list(self.chain.pending)  # 

        prefix = "0" * int(difficulty)
        base = f"{parent.hash}|{len(txs)}|{difficulty}|"

        for nonce in range(int(max_iters)):
            h = hashlib.sha256(f"{base}{nonce}".encode()).hexdigest()
            if h.startswith(prefix):
                blk = Block(
                    index=parent.index + 1,
                    ts=time.time(),
                    parent_hash=parent.hash,
                    txs=txs,
                    difficulty=int(difficulty),
                    nonce=nonce,
                    hash_=h
                )
                self.chain.add_block(blk)
                return blk
        return None
