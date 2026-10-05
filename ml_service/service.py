"""ML service. Start with: uvicorn service:app --port 8001"""
import os

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    from .train import VIBRATION_MAP, train_and_save
except ImportError:  # pragma: no cover
    from train import VIBRATION_MAP, train_and_save

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")

# train a model automatically if train.py was not run yet
if not os.path.exists(MODEL_PATH):
    train_and_save(MODEL_PATH)

saved = joblib.load(MODEL_PATH)
model = saved["model"]
features = saved["features"]
labels = saved["labels"]

app = FastAPI(title="Machine Risk ML Service")


class PredictRequest(BaseModel):
    data: dict  # machine values keyed by field name


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(request: PredictRequest):
    # make field names lowercase so "Temperature" matches "temperature"
    data = {name.strip().lower(): value for name, value in request.data.items()}

    missing = [f for f in features if data.get(f) in (None, "")]
    if missing:
        raise HTTPException(status_code=422, detail="Missing inputs: " + ", ".join(missing))

    try:
        row = {
            "temperature": float(data["temperature"]),
            "pressure": float(data["pressure"]),
            "vibration": VIBRATION_MAP[str(data["vibration"]).strip().lower()],
        }
    except (ValueError, KeyError):
        raise HTTPException(status_code=422, detail="Invalid temperature, pressure or vibration value")

    probabilities = model.predict_proba(pd.DataFrame([row])[features])[0]
    best = int(probabilities.argmax())

    return {
        "risk_level": labels[best],
        "confidence": round(float(probabilities[best]), 2),
        "features_used": features,
        # fields the model was not trained on (e.g. humidity)
        "features_ignored": [name for name in data if name not in features],
    }
