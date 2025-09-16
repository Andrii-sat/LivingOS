from typing import Optional
from .blockchain import Chain, Block

class Miner:
    def __init__(self, chain: Chain):
        self.chain = chain

    def mine_once(self, max_iters: int = 200000, difficulty: int = None) -> Optional[Block]:
        return self.chain.try_mine(max_iters=max_iters, difficulty=difficulty)
