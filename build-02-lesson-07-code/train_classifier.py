"""
Cortex — Build 02, Lesson 07 (Build Milestone)
Trains and saves the classifier this milestone's /classify endpoint
serves. Run once, at build time — not something the API triggers itself.

Honest caveat, stated once here instead of buried: Cortex doesn't have
enough real production traffic yet to train on, so this model is
bootstrapped on the same synthetic corpus Lesson 04 used. The interface
this milestone exposes — features in, category + confidence out — doesn't
change at all once there's real data to retrain on; only what
train_classifier.py reads from changes.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_PATH = Path(__file__).parent / "model.joblib"


def generate_corpus(n: int = 500, seed: int = 7) -> pd.DataFrame:
    """Identical generator to Build 02, Lesson 04 — same imbalance
    ratios, same per-category length/tag distributions."""
    rng = np.random.default_rng(seed)
    categories = rng.choice(
        ["note", "report", "spec", "legal"], size=n, p=[0.70, 0.20, 0.08, 0.02]
    )
    length_params = {
        "note": (4.6, 0.8), "report": (5.8, 0.7), "spec": (6.3, 0.6), "legal": (6.8, 0.5),
    }
    tag_params = {"note": 0.6, "report": 1.8, "spec": 2.3, "legal": 2.8}

    body_length = np.array([rng.lognormal(*length_params[c]) for c in categories]).astype(int)
    word_count = np.clip(body_length / 5 + rng.normal(0, 3, size=n), 1, None).astype(int)
    num_tags = np.array([rng.poisson(tag_params[c]) for c in categories]).clip(0, 5)

    return pd.DataFrame(
        {"category": categories, "body_length": body_length, "word_count": word_count, "num_tags": num_tags}
    )


def build_classifier() -> Pipeline:
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)),
        ]
    )


def train_and_save(path: Path = MODEL_PATH) -> Pipeline:
    df = generate_corpus(n=500)
    X = df[["body_length", "word_count", "num_tags"]]
    y = df["category"]

    pipeline = build_classifier()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Unknown solver options: iprint")
        pipeline.fit(X, y)

    joblib.dump(pipeline, path)
    return pipeline


if __name__ == "__main__":
    train_and_save()
    print(f"Model trained and saved to {MODEL_PATH}")
