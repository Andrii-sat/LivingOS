from src.kernel.fractal_signature import FractalSignature

def test_signature_descriptor():
    fs = FractalSignature(12345)
    assert "frsig://" in fs.descriptor()
