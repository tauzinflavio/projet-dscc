"""Contrat d'entrée partagé par le dispatcher et le worker."""
import hashlib
import json
import math

MAX_BYTES = 64 * 1024


def document_id(name, etag):
    return hashlib.sha256(json.dumps([name, etag], ensure_ascii=False).encode()).hexdigest()


def validate(name, size, raw):
    if not name.lower().endswith(".json"):
        raise ValueError("extension attendue : .json")
    if size > MAX_BYTES:
        raise ValueError("taille maximale : 64 Kio")
    try:
        item = json.loads(raw)
    except (ValueError, RecursionError) as error:
        raise ValueError("JSON illisible") from error
    features = item.get("features") if isinstance(item, dict) else None
    if not isinstance(features, list) or len(features) != 13 or set(item) != {"features"}:
        raise ValueError("champ unique features contenant 13 mesures attendu")
    for value in features:
        if type(value) not in (int, float) or abs(value) > 1e100 or not math.isfinite(value):
            raise ValueError("mesure non numérique ou hors plage")
    return item
