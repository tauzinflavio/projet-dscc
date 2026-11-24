"""Entraînement local. Exécuter depuis la racine du projet."""
import json
from pathlib import Path
from statistics import median
from time import perf_counter

import joblib
from sklearn.datasets import load_wine
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
VERSION = "1.0.0"


def train():
    wine = load_wine()
    x_train, x_test, y_train, y_test = train_test_split(
        wine.data, wine.target, test_size=0.25, stratify=wine.target, random_state=42
    )
    model = make_pipeline(StandardScaler(), LogisticRegression(random_state=42))
    baseline = DummyClassifier(strategy="most_frequent")
    scores = {}
    for name, classifier in [("logistique", model), ("majoritaire", baseline)]:
        classifier.fit(x_train, y_train)
        pred = classifier.predict(x_test)
        scores[name] = {"accuracy": accuracy_score(y_test, pred),
                        "f1_macro": f1_score(y_test, pred, average="macro")}
    path = ROOT / f"model-{VERSION}.joblib"
    joblib.dump({"estimator": model, "features": wine.feature_names, "version": VERSION}, path)
    timings = []
    for row in x_test:
        start = perf_counter()
        model.predict_proba([row])
        timings.append((perf_counter() - start) * 1000)
    result = dict(train=len(y_train), test=len(y_test), scores=scores, bytes=path.stat().st_size,
                  median_cpu_ms=median(timings), max_cpu_ms=max(timings))
    (ROOT / "evaluation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    train()
