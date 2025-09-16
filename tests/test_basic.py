from src.kernel.mini_os import MiniOS
from src.kernel.fractal_signature import FractalSignature

def test_ingest_and_merge():
    kernel = MiniOS()
    a = kernel.ingest_text("sun")
    b = kernel.ingest_text("moon")
    assert a != b
    m = kernel.merge(a, b, 0.5)
    assert m not in (a, b)

def test_frsig_descriptor_roundtrip():
    seed = 123456
    fs = FractalSignature(seed)
    desc = fs.descriptor()
    fs2 = FractalSignature.from_descriptor(desc)
    assert fs.seed == fs2.seed
    assert abs(fs.c_re - fs2.c_re) < 1e-6
