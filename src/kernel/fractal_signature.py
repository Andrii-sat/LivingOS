import hashlib, random

PHI = (1 + 5 ** 0.5) / 2.0

def sha256_int32(s: str) -> int:
    h = hashlib.sha256((s or "").encode("utf-8")).hexdigest()
    return int(h[:16], 16) & 0x7FFFFFFF

class FractalSignature:
    """
    Deterministic descriptor for agents.
    frsig://{seed}:{size}:{iters}:{c_re}:{c_im}:{zoom}:{ox}:{oy}
    """
    def __init__(self, seed: int, size: int = 256, iters: int = 64):
        self.seed = int(seed) & 0x7FFFFFFF
        self.size = size; self.iters = iters
        rng = random.Random(self.seed)
        self.c_re = (rng.random() - 0.5) * 1.5
        self.c_im = (rng.random() - 0.5) * 1.5
        self.zoom = 1.0 + rng.random() * 2.0
        self.ox   = (rng.random() - 0.5) * 1.2
        self.oy   = (rng.random() - 0.5) * 1.2

    def descriptor(self) -> str:
        return f"frsig://{self.seed}:{self.size}:{self.iters}:{self.c_re:.6f}:{self.c_im:.6f}:{self.zoom:.6f}:{self.ox:.6f}:{self.oy:.6f}"

    @staticmethod
    def from_descriptor(desc: str) -> "FractalSignature":
        parts = desc[8:].split(":")
        fs = FractalSignature(int(parts[0]), int(parts[1]), int(parts[2]))
        fs.c_re, fs.c_im, fs.zoom, fs.ox, fs.oy = map(float, parts[3:8])
        return fs

class FractalCodec:
    @staticmethod
    def encode_text(text: str) -> dict:
        seed = sha256_int32(text or "")
        d = FractalSignature(seed).descriptor()
        return {"seed": seed, "descriptor": d, "summary": (text or "")[:120]}
