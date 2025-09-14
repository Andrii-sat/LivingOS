"""
FractalSignature — deterministic seed from text
"""

import hashlib
import random

class FractalSignature:
    def __init__(self, seed: int, size: int = 256, iters: int = 64):
        self.seed = seed & 0x7FFFFFFF
        rng = random.Random(self.seed)
        self.c_re = (rng.random() - 0.5) * 1.5
        self.c_im = (rng.random() - 0.5) * 1.5

    def descriptor(self) -> str:
        return f"frsig://{self.seed}:{self.c_re:.4f}:{self.c_im:.4f}"

def sha256_int32(s: str) -> int:
    h = hashlib.sha256((s or "").encode("utf-8")).hexdigest()
    return int(h[:16], 16) & 0x7FFFFFFF
