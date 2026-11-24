import json
from pathlib import Path

import pytest
from pipeline import MAX_BYTES, document_id, validate

EXAMPLES = Path(__file__).resolve().parents[2] / "docs/exemples"


def test_valid_sample():
    raw = (EXAMPLES / "vin-valide.json").read_bytes()
    assert validate("vin.json", len(raw), raw) == json.loads(raw)


@pytest.mark.parametrize("name,size,raw", [
    ("vin.csv", 10, b"{}"), ("vin.json", MAX_BYTES + 1, b""),
    ("vin.json", 0, b""), ("vin.json", 2, b"[]"),
    ("vin.json", 20, (EXAMPLES / "vin-invalide.json").read_bytes()),
    ("vin.json", 100, json.dumps({"features": [True] * 13})),
    ("vin.json", 100, json.dumps({"features": [float("nan")] * 13})),
])
def test_invalid_sample(name, size, raw):
    with pytest.raises(ValueError):
        validate(name, size, raw)


def test_idempotence_key():
    assert document_id("a.json", "1") == document_id("a.json", "1")
    assert document_id("a.json", "1") != document_id("a.json", "2")
