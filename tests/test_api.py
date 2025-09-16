import pytest
import json
from src.living_os_showtime import app

@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client

def test_health_and_version(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["ok"]

    r = client.get("/version")
    assert r.status_code == 200
    assert r.json["name"] == "LivingOS"

def test_state_endpoint(client):
    r = client.get("/state")
    assert r.status_code == 200
    data = json.loads(r.data.decode("utf-8"))
    assert "nodes" in data
    assert "edges" in data

def test_add_and_merge(client):
    # Add "sun"
    msg1 = {"msg": "fcp://T|text=sun"}
    r1 = client.post("/api/fcp", json=msg1)
    assert r1.status_code == 200
    assert "OK" in r1.json["resp"]

    # Add "moon"
    msg2 = {"msg": "fcp://T|text=moon"}
    r2 = client.post("/api/fcp", json=msg2)
    assert r2.status_code == 200
    assert "OK" in r2.json["resp"]

    # Merge last two
    d1 = r1.json["resp"]
    d2 = r2.json["resp"]
    # Format: fcp://OK|d=frsig://...
    desc_a = d1.split("d=")[1]
    desc_b = d2.split("d=")[1]
    msg3 = {"msg": f"fcp://M|a={desc_a};b={desc_b};mix=0.5"}
    r3 = client.post("/api/fcp", json=msg3)
    assert r3.status_code == 200
    assert "OK" in r3.json["resp"]

def test_chain_and_mine(client):
    r = client.get("/chain")
    assert r.status_code == 200
    assert "height" in r.json

    r = client.post("/mine", json={"max_iters": 50000, "difficulty": 2})
    assert r.status_code == 200
    assert r.json["mined"] in [True, False]
