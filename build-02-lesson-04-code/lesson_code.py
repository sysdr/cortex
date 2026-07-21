"""
Cortex — Build 02, Lesson 04
Classical ML with scikit-learn: Cortex's category/quality classifier, v1.

Two things happen today. First: a real, multi-class classifier — the
actual v1 that Lesson 07's /classify endpoint will eventually serve —
built on scikit-learn instead of hand-rolled gradient descent. Second, and
more pointed: the exact overfitting scenario measured by hand in Lesson 03
(polynomial degree 5, three noise columns, 500 documents) gets rebuilt
with scikit-learn's default L2-regularized LogisticRegression, so the
"regularization fixes this" claim from last lesson's teaser is checked
against real numbers, not just asserted.
"""

from __future__ import annotations

from itertools import combinations_with_replacement
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ── Part A: the real v1 classifier — four categories, not two ──────────


def generate_corpus(n: int = 500, seed: int = 7) -> pd.DataFrame:
    """Same imbalance ratios as Lesson 02 (70/20/8/2), but now each
    category has its own real, noisy relationship to body length and tag
    count — legal documents tend to be long and heavily tagged, quick
    notes tend to be short and sparsely tagged — so a multi-class
    classifier has genuine, if imperfect, signal across all four classes,
    not just a binary split."""
    rng = np.random.default_rng(seed)
    categories = rng.choice(
        ["note", "report", "spec", "legal"], size=n, p=[0.70, 0.20, 0.08, 0.02]
    )

    length_params = {
        "note": (4.6, 0.8),
        "report": (5.8, 0.7),
        "spec": (6.3, 0.6),
        "legal": (6.8, 0.5),
    }
    tag_params = {"note": 0.6, "report": 1.8, "spec": 2.3, "legal": 2.8}

    body_length = np.array(
        [rng.lognormal(*length_params[c]) for c in categories]
    ).astype(int)
    word_count = np.clip(body_length / 5 + rng.normal(0, 3, size=n), 1, None).astype(int)
    num_tags = np.array(
        [rng.poisson(tag_params[c]) for c in categories]
    ).clip(0, 5)

    return pd.DataFrame(
        {
            "id": [f"doc-{i:04d}" for i in range(n)],
            "category": categories,
            "body_length": body_length,
            "word_count": word_count,
            "num_tags": num_tags,
        }
    )


def build_classifier_v1() -> Pipeline:
    """StandardScaler first, because LogisticRegression's regularization
    penalizes large weights — and a feature measured in the thousands
    (body_length) would get penalized completely differently than one
    measured in single digits (num_tags) if left unscaled, regardless of
    which one actually matters more. class_weight="balanced" re-weights
    each class's contribution to the loss inversely to its frequency,
    which is the direct, principled fix for the exact imbalance problem
    Lesson 02 found (68.6% note, 1.6% legal) — without it, the model has
    little incentive to ever predict "legal" at all."""
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced", max_iter=1000, random_state=42
                ),
            ),
        ]
    )


def evaluate(pipeline: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    y_pred = pipeline.predict(X_test)
    return {
        "accuracy": float((y_pred == y_test).mean()),
        "report": classification_report(y_test, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=sorted(y_test.unique())),
        "labels": sorted(y_test.unique()),
    }


def cross_validate(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, cv: int = 5) -> np.ndarray:
    """A single train/test split is one sample of "how well does this
    generalize" — cross-validation runs the same question cv times, on
    cv different held-out slices, so the reported score is an average
    over several independent tries instead of whatever one particular
    split happened to produce. StratifiedKFold, not plain KFold, for the
    same reason Lesson 03 used a stratified split: preserving class ratio
    in every fold."""
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    return cross_val_score(pipeline, X, y, cv=skf)


def save_model(pipeline: Pipeline, path: Path) -> None:
    joblib.dump(pipeline, path)


def load_model(path: Path) -> Pipeline:
    return joblib.load(path)


# ── Part B: does scikit-learn's regularization actually fix Lesson 03's
#            overfitting, or was that just an assertion? ──────────────


def generate_binary_corpus_like_lesson_03(n: int = 500, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """Reproduces Lesson 03's exact setup: is_official as a binary target,
    two real features, three pure-noise features — so the comparison
    below is apples to apples, not a different problem in disguise."""
    rng = np.random.default_rng(seed)
    is_official = rng.choice([0, 1], size=n, p=[0.686, 0.314])
    body_length = np.where(
        is_official == 1,
        rng.lognormal(mean=6.2, sigma=0.8, size=n),
        rng.lognormal(mean=4.8, sigma=0.9, size=n),
    ).astype(float)
    word_count = np.clip(body_length / 5 + rng.normal(0, 3, size=n), 1, None)
    noise = rng.normal(0, 1, size=(n, 3))
    X = np.column_stack([body_length, word_count, noise])
    return X, is_official


def polynomial_features(X: np.ndarray, degree: int) -> np.ndarray:
    n_features = X.shape[1]
    columns = []
    for d in range(1, degree + 1):
        for combo in combinations_with_replacement(range(n_features), d):
            col = np.ones(X.shape[0])
            for idx in combo:
                col = col * X[:, idx]
            columns.append(col)
    return np.column_stack(columns)


def regularized_gap_at_degree(X_raw: np.ndarray, y: np.ndarray, degree: int, C: float = 1.0) -> dict:
    """The direct comparison to Lesson 03's hand-rolled result: same
    polynomial-degree feature explosion, same data, but trained with
    scikit-learn's LogisticRegression at a given regularization strength
    C instead of unregularized gradient descent."""
    X_poly = polynomial_features(X_raw, degree)
    X_train, X_test, y_train, y_test = train_test_split(
        X_poly, y, test_size=0.3, random_state=0, stratify=y
    )
    scaler = StandardScaler().fit(X_train)
    X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)

    model = LogisticRegression(C=C, max_iter=2000, random_state=42)
    model.fit(X_train_s, y_train)

    train_acc = model.score(X_train_s, y_train)
    test_acc = model.score(X_test_s, y_test)
    return {
        "degree": degree,
        "C": C,
        "n_features": X_poly.shape[1],
        "train_acc": train_acc,
        "test_acc": test_acc,
        "gap": train_acc - test_acc,
    }


def _demo() -> None:
    print("=== Part A: Cortex category classifier v1 ===\n")
    df = generate_corpus(n=500)
    X = df[["body_length", "word_count", "num_tags"]]
    y = df["category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    pipeline = build_classifier_v1()
    pipeline.fit(X_train, y_train)

    results = evaluate(pipeline, X_test, y_test)
    print(f"Test accuracy: {results['accuracy']:.3f}\n")
    print(results["report"])

    cv_scores = cross_validate(pipeline, X, y, cv=5)
    print(f"5-fold cross-validation accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")
    print(f"  fold scores: {[round(s, 3) for s in cv_scores]}")

    model_path = Path("model.joblib")
    save_model(pipeline, model_path)
    reloaded = load_model(model_path)
    sample = X_test.iloc[:1]
    match = (pipeline.predict(sample) == reloaded.predict(sample)).all()
    print(f"\nModel saved to {model_path}, reloaded, predictions match: {match}")

    print("\n\n=== Part B: does regularization actually fix Lesson 03's overfitting? ===\n")
    X_raw, y_bin = generate_binary_corpus_like_lesson_03(n=500)

    print("Lesson 03 (hand-rolled gradient descent, 500 epochs), for reference:")
    print("  degree=5  train=0.846  test=0.772  gap=+0.074\n")

    print("Naive comparison — scikit-learn at default C=1.0, same degree:")
    r_default = regularized_gap_at_degree(X_raw, y_bin, degree=5, C=1.0)
    print(f"  degree=5  train={r_default['train_acc']:.3f}  test={r_default['test_acc']:.3f}  "
          f"gap={r_default['gap']:+.3f}   <- LARGER than Lesson 03's gap, not smaller!\n")

    print("Why: scikit-learn's L-BFGS solver converges much more precisely than our")
    print("500-epoch gradient descent did. It isn't measuring 'regularized vs not' —")
    print("it's confounded by which model actually finished training. The clean test")
    print("holds the solver fixed and varies only C:\n")

    for C in [1_000_000, 1000, 1.0, 0.1, 0.01, 0.001]:
        r = regularized_gap_at_degree(X_raw, y_bin, degree=5, C=C)
        print(f"  C={C:>10}  train_acc={r['train_acc']:.3f}  test_acc={r['test_acc']:.3f}  gap={r['gap']:+.3f}")


if __name__ == "__main__":
    _demo()
