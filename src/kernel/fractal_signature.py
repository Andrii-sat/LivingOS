"""
FractalSignature — deterministic fractal descriptor (seeded per text)
"""

import hashlib
import random
from dataclasses import dataclass

def sha256_int32(s: str) -> int:
    h = hashlib.sha256((s or "").encode("utf-8")).hexdigest()
    return int(h[:16], 16) & 0x7FFFFFFF

@dataclass
class FractalSignature:
    seed: int
    size: int = 256
    iters: int = 64
    c_re: float = 0.0
    c_im: float = 0.0
    zoom: float = 1.0
    ox: float = 0.0
    oy: float = 0.0

    def __post_init__(self):
        self.seed = int(self.seed) & 0x7FFFFFFF
        rng = random.Random(self.seed)
        # Параметри для візуальної варіативності (стабільні від seed)
        self.c_re = (rng.random() - 0.5) * 1.5
        self.c_im = (rng.random() - 0.5) * 1.5
        self.zoom = 1.0 + rng.random() * 2.0
        self.ox = (rng.random() - 0.5) * 1.2
        self.oy = (rng.random() - 0.5) * 1.2

    def descriptor(self) -> str:
        # Компактний дескриптор, який можна зберігати/ділити
        return (
            f"frsig://{self.seed}:{self.size}:{self.iters}:"
            f"{self.c_re:.6f}:{self.c_im:.6f}:{self.zoom:.6f}:{self.ox:.6f}:{self.oy:.6f}"
        )

    @staticmethod
    def from_descriptor(desc: str) -> "FractalSignature":
        # очікуємо формат frsig://<seed>:<size>:<iters>:<c_re>:<c_im>:<zoom>:<ox>:<oy>
        if not desc.startswith("frsig://"):
            raise ValueError("Bad frsig descriptor")
        parts = desc[8:].split(":")
        seed, size, iters = int(parts[0]), int(parts[1]), int(parts[2])
        fs = FractalSignature(seed, size, iters)
        fs.c_re, fs.c_im, fs.zoom, fs.ox, fs.oy = map(float, parts[3:8])
        return fs

class FractalCodec:
    """ Простий енкодер тексту → сигнатура """
    @staticmethod
    def encode_text(text: str) -> dict:
        seed = sha256_int32(text or "")
        fs = FractalSignature(seed)
        return {
            "seed": seed,
            "descriptor": fs.descriptor(),
            "summary": (text or "")[:120]
        }
