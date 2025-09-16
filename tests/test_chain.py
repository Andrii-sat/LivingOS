import pytest
from src.kernel.blockchain import Chain
from src.kernel.mining import Miner

def test_chain_init_and_tx():
    chain = Chain()
    # Genesis block
    info = chain.info()
    assert info["height"] == 1
    assert "tip" in info

    # Add tx
    chain.add_tx("TEST", {"msg": "hello"})
    mempool = chain.pending
    assert len(mempool) == 1
    assert mempool[0]["op"] == "TEST"

def test_mining_and_block_addition():
    chain = Chain()
    miner = Miner(chain)

    chain.add_tx("TX1", {"v": 1})
    chain.add_tx("TX2", {"v": 2})

    blk = miner.mine_once(max_iters=100000, difficulty=2)
    assert blk is not None
    assert blk.index == 1  # after genesis
    assert isinstance(blk.hash, str)

    # Chain should now have 2 blocks (genesis + mined)
    info = chain.info()
    assert info["height"] == 2

def test_chain_validity():
    chain = Chain()
    miner = Miner(chain)

    # Mine 2 blocks
    for i in range(2):
        chain.add_tx("TX", {"i": i})
        blk = miner.mine_once(max_iters=200000, difficulty=2)
        assert blk is not None

    # Check validity
    for i in range(1, len(chain.blocks)):
        prev = chain.blocks[i-1]
        curr = chain.blocks[i]
        assert curr.parent == prev.hash
