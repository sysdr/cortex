"""
Cortex — Build 02, Lesson 03
Train/test split & overfitting — demonstrated live on Cortex's own classifier.

Two things happen today, both live, not described:
  1. A naive random split is shown producing genuinely different class
     representation from run to run on Lesson 02's imbalanced corpus —
     stratified splitting fixes it.
  2. Overfitting is shown actually happening: the exact, unmodified
     training loop from Lesson 01 gets fed increasingly high-degree
     polynomial features, and the gap between train and test accuracy
     widens in front of you as capacity increases past what 500 documents
     can support.

The classifier code below (sigmoid, cross_entropy_loss, compute_gradients,
train_logistic_regression) is copied verbatim from Lesson 01 — not
rewritten, not improved. The point of today's lesson is that the exact
same training loop can either generalize or overfit depending entirely on
what you feed it and how you evaluate it, not on anything about the loop
itself.
"""

from __future__ import annotations

from itertools import combinations_with_replacement

import numpy as np
import pandas as pd


# ── Classifier code, unchanged from Lesson 01 ──────────────────────────


def sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


def predict_proba(X: np.ndarray, weights: np.ndarray, bias: float) -> np.ndarray:
    z = X @ weights + bias
    return sigmoid(z)


def cross_entropy_loss(y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
    eps = 1e-12
    p = np.clip(y_pred_proba, eps, 1 - eps)
    return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))


def compute_gradients(
    X: np.ndarray, y_true: np.ndarray, y_pred_proba: np.ndarray
) -> tuple[np.ndarray, float]:
    n = X.shape[0]
    error = y_pred_proba - y_true
    dw = X.T @ error / n
    db = float(np.mean(error))
    return dw, db


def train_logistic_regression(
    X: np.ndarray, y: np.ndarray, learning_rate: float = 0.5, epochs: int = 300
) -> tuple[np.ndarray, float, list[float]]:
    n_features = X.shape[1]
    weights = np.zeros(n_features)
    bias = 0.0
    loss_history: list[float] = []
    for _ in range(epochs):
        y_pred = predict_proba(X, weights, bias)
        loss_history.append(cross_entropy_loss(y, y_pred))
        dw, db = compute_gradients(X, y, y_pred)
        weights -= learning_rate * dw
        bias -= learning_rate * db
    return weights, bias, loss_history


def accuracy(y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
    y_pred_labels = (y_pred_proba >= 0.5).astype(int)
    return float(np.mean(y_pred_labels == y_true))


# ── Dataset, adapted from Lesson 02's messy corpus ─────────────────────


def generate_labeled_corpus(n: int = 500, seed: int = 7) -> pd.DataFrame:
    """Official documents (report/spec/legal, collapsed to is_official=1)
    really do tend to be longer and wordier than quick notes — that's the
    genuine, if noisy, signal a classifier should be able to find. Three
    additional columns (noise_1..3) carry no relationship to the label at
    all; they exist so a high-capacity model has something spurious to
    latch onto, which is a far more realistic cause of overfitting than
    "too many degrees on otherwise-meaningful features" alone."""
    rng = np.random.default_rng(seed)

    is_official = rng.choice([0, 1], size=n, p=[0.686, 0.314])

    body_length = np.where(
        is_official == 1,
        rng.lognormal(mean=6.2, sigma=0.8, size=n),
        rng.lognormal(mean=4.8, sigma=0.9, size=n),
    ).astype(int)
    word_count = np.clip((body_length / 5 + rng.normal(0, 3, size=n)), 1, None).astype(int)

    noise_1 = rng.normal(0, 1, size=n)
    noise_2 = rng.normal(0, 1, size=n)
    noise_3 = rng.normal(0, 1, size=n)

    return pd.DataFrame(
        {
            "id": [f"doc-{i:04d}" for i in range(n)],
            "is_official": is_official,
            "body_length": body_length,
            "word_count": word_count,
            "noise_1": noise_1,
            "noise_2": noise_2,
            "noise_3": noise_3,
        }
    )


def normalize(X: np.ndarray) -> np.ndarray:
    mean, std = X.mean(axis=0), X.std(axis=0)
    return (X - mean) / std


# ── Splitting: naive vs stratified ─────────────────────────────────────


def naive_random_split(
    n: int, test_size: float = 0.3, seed: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Shuffles every row together and slices — no awareness that some
    classes are rarer than others. Simple, and exactly why it's risky on
    imbalanced data: a rare class can end up over- or under-represented
    in the test set purely by chance, and that chance changes every time
    the seed changes."""
    rng = np.random.default_rng(seed)
    indices = rng.permutation(n)
    n_test = int(n * test_size)
    return indices[n_test:], indices[:n_test]


def stratified_split(
    y: np.ndarray, test_size: float = 0.3, seed: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Splits within each class separately, then combines — so the test
    set's class proportions match the full dataset's proportions by
    construction, not by luck. This is the direct fix for what Lesson 02
    found: a 68.6/31.4 split that a naive shuffle isn't guaranteed to
    preserve, especially as the minority class gets smaller."""
    rng = np.random.default_rng(seed)
    train_indices = []
    test_indices = []
    for cls in np.unique(y):
        cls_indices = np.where(y == cls)[0]
        cls_indices = rng.permutation(cls_indices)
        n_test = int(len(cls_indices) * test_size)
        test_indices.extend(cls_indices[:n_test])
        train_indices.extend(cls_indices[n_test:])
    return np.array(train_indices), np.array(test_indices)


# ── Polynomial feature expansion — the knob that controls overfitting ──


def polynomial_features(X: np.ndarray, degree: int) -> np.ndarray:
    """Expands [body_length, word_count] into every polynomial
    combination up to the given degree — degree 2 adds x1^2, x1*x2, x2^2;
    degree 3 adds every cubic term; and so on. More degree means more
    capacity to fit the training data exactly, whether or not that fit
    reflects anything real about the underlying pattern."""
    n_features = X.shape[1]
    columns = []
    for d in range(1, degree + 1):
        for combo in combinations_with_replacement(range(n_features), d):
            col = np.ones(X.shape[0])
            for idx in combo:
                col = col * X[:, idx]
            columns.append(col)
    return np.column_stack(columns)


def _demo() -> None:
    df = generate_labeled_corpus(n=500)
    X_raw = df[["body_length", "word_count", "noise_1", "noise_2", "noise_3"]].to_numpy(dtype=float)
    y = df["is_official"].to_numpy()

    print(f"Corpus: {len(df)} documents, {y.mean():.1%} official\n")

    # --- Part 1: naive split variance vs stratified consistency ---
    print("--- Naive random split: test-set positive rate across 5 seeds ---")
    naive_rates = []
    for seed in range(5):
        _, test_idx = naive_random_split(len(df), test_size=0.3, seed=seed)
        rate = y[test_idx].mean()
        naive_rates.append(rate)
        print(f"  seed={seed}: {rate:.1%}")
    print(f"  std across seeds: {np.std(naive_rates):.4f}")

    print("\n--- Stratified split: test-set positive rate across 5 seeds ---")
    strat_rates = []
    for seed in range(5):
        _, test_idx = stratified_split(y, test_size=0.3, seed=seed)
        rate = y[test_idx].mean()
        strat_rates.append(rate)
        print(f"  seed={seed}: {rate:.1%}")
    print(f"  std across seeds: {np.std(strat_rates):.4f}")

    # --- Part 2: overfitting, live, using Lesson 01's unmodified loop ---
    print("\n--- Overfitting curve: same training loop, increasing polynomial degree ---")
    print("(body_length + word_count carry real signal; noise_1..3 carry none)\n")
    train_idx, test_idx = stratified_split(y, test_size=0.3, seed=0)

    for degree in [1, 2, 3, 4, 5]:
        X_poly = polynomial_features(X_raw, degree)
        X_norm = normalize(X_poly)

        X_train, X_test = X_norm[train_idx], X_norm[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        weights, bias, _ = train_logistic_regression(X_train, y_train, learning_rate=0.3, epochs=500)

        train_acc = accuracy(y_train, predict_proba(X_train, weights, bias))
        test_acc = accuracy(y_test, predict_proba(X_test, weights, bias))
        gap = train_acc - test_acc

        print(f"  degree={degree}  features={X_poly.shape[1]:>4}  "
              f"train_acc={train_acc:.3f}  test_acc={test_acc:.3f}  gap={gap:+.3f}")


if __name__ == "__main__":
    _demo()
