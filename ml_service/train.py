"""Trains the risk model on synthetic data and saves it to model.joblib."""
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

FEATURES = ["temperature", "pressure", "vibration"]
VIBRATION_MAP = {"low": 0, "medium": 1, "high": 2}
LABELS = ["Low", "Medium", "High"]


def generate_data(n=3000):
    rng = np.random.default_rng(42)
    temperature = rng.uniform(20, 120, n)
    pressure = rng.uniform(50, 200, n)
    vibration = rng.integers(0, 3, n)

    # made-up risk score: higher values of each feature means more risk
    score = (temperature - 20) / 100 * 40 + (pressure - 50) / 150 * 30 + vibration * 15
    score = score + rng.normal(0, 4, n)
    risk = np.digitize(score, [35, 60])  # 0 = Low, 1 = Medium, 2 = High

    return pd.DataFrame(
        {"temperature": temperature, "pressure": pressure, "vibration": vibration, "risk": risk}
    )


def train_and_save(path="model.joblib"):
    data = generate_data()
    X_train, X_test, y_train, y_test = train_test_split(
        data[FEATURES], data["risk"], test_size=0.2, random_state=1
    )
    model = RandomForestClassifier(n_estimators=100, random_state=1)
    model.fit(X_train, y_train)
    print("Test accuracy:", round(model.score(X_test, y_test), 2))

    joblib.dump({"model": model, "features": FEATURES, "labels": LABELS}, path)


if __name__ == "__main__":
    train_and_save()
