import hashlib, time
from .blockchain import Block


class Miner:
    def __init__(self, chain):
        self.chain = chain

    def mine_once(self, max_iters=100000, difficulty=2):
        if not self.chain.pending:
            return None  # nothing to mine

        parent = self.chain.tip()
        index = parent.index + 1
        txs = self.chain.pending[:]
        self.chain.pending.clear()

        prefix = "0" * difficulty
        nonce = 0
        ts = time.time()
        while nonce < max_iters:
            blk = Block(index=index, parent_hash=parent.hash, txs=txs, difficulty=difficulty, nonce=nonce, ts=ts)
            if blk.hash.startswith(prefix):
                self.chain.add_block(blk)
                return blk
            nonce += 1
        return None
