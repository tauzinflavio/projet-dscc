import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from time import perf_counter

import joblib
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

DEFAULT_MODEL = Path(__file__).resolve().parents[1] / "model/model-1.0.0.joblib"


@asynccontextmanager
async def lifespan(app):
    start = perf_counter()
    app.state.bundle = joblib.load(os.getenv("MODEL_PATH", str(DEFAULT_MODEL)))
    app.state.load_ms = (perf_counter() - start) * 1000
    app.state.calls = 0
    app.state.total_ms = 0.0
    app.state.lock = Lock()
    yield


app = FastAPI(title="Pipeline ML événementiel", lifespan=lifespan)


class Measurements(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: list[FiniteFloat] = Field(min_length=13, max_length=13)


@app.get("/health")
def health():
    return {"status": "ready", "load_ms": app.state.load_ms}


@app.get("/version")
def version():
    return {"api": os.getenv("API_VERSION", "1.0.0"), "model": app.state.bundle["version"],
            "commit": os.getenv("GIT_SHA", "local")}


@app.post("/predict")
def predict(data: Measurements):
    model = app.state.bundle["estimator"]
    start = perf_counter()
    probabilities = model.predict_proba([data.features])[0]
    best = probabilities.argmax()
    elapsed = (perf_counter() - start) * 1000
    with app.state.lock:
        app.state.calls += 1
        app.state.total_ms += elapsed
    return {"prediction": int(model.classes_[best]) + 1, "confidence": float(probabilities[best]),
            "modelVersion": app.state.bundle["version"], "durationMs": elapsed}


@app.get("/metrics")
def metrics():
    with app.state.lock:
        calls = app.state.calls
        return {"calls": calls, "meanLatencyMs": app.state.total_ms / calls if calls else 0.0}
