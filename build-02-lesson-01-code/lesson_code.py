"""
Cortex — Build 02, Lesson 01
Math for ML, taught by deriving the classifier we're about to build.

No scikit-learn, no PyTorch — just NumPy, because the point of this lesson
is to see every piece of a classifier come directly from linear algebra and
probability, not from a library call. This exact classifier — a single
logistic unit — is the seed Lesson 05 grows into a neural network by
stacking more of them, and the seed Build 09's model-routing classifier
grows into a production cost-control decision.

The data here is synthetic on purpose. Lesson 02 does real EDA on Cortex's
actual document corpus; putting messy real data in front of the math before
the math is understood would teach two hard things at once.
"""

from __future__ import annotations

import numpy as np


# ── Synthetic data: a document is two numbers, on purpose ──────────────
# AI relevance: this is a drastically simplified stand-in for what Lesson 02
# will do for real — turn a document into a feature vector. Two features
# instead of two thousand keeps the linear algebra visible instead of
# buried in dimensionality.


def generate_synthetic_documents(
    n: int = 200, seed: int = 42
) -> tuple[np.ndarray, np.ndarray]:
    """Each document becomes a feature vector [body_length, word_count].
    The true rule: documents are "long-form" (label 1) if they're long AND
    wordy; "quick-note" (label 0) otherwise — with noise added so the data
    isn't trivially, perfectly separable. Real documents won't be this
    clean, which is exactly why Lesson 02 exists."""
    rng = np.random.default_rng(seed)

    quick_notes = rng.normal(loc=[80, 15], scale=[30, 5], size=(n // 2, 2))
    long_form = rng.normal(loc=[600, 120], scale=[150, 25], size=(n // 2, 2))

    X = np.vstack([quick_notes, long_form])
    X = np.clip(X, 1, None)  # a document can't have negative length
    y = np.array([0] * (n // 2) + [1] * (n // 2))

    # Shuffle so the two classes aren't sitting in two obvious blocks —
    # a classifier that "works" on sorted data can hide a real bug.
    shuffle_idx = rng.permutation(n)
    return X[shuffle_idx], y[shuffle_idx]


def normalize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Features on wildly different scales (word count: tens, body length:
    hundreds) make gradient descent zigzag instead of heading straight for
    the minimum — the gradient in the large-scale direction dominates.
    Normalizing puts both features on comparable footing."""
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    return (X - mean) / std, mean, std


# ── The math, in order: linear combination -> probability -> loss ──────


def sigmoid(z: np.ndarray) -> np.ndarray:
    """Squashes any real number into (0, 1) — the function that turns a
    raw weighted score into something that can legitimately be called a
    probability. Clipped to avoid overflow on very negative z; the
    mathematical sigmoid doesn't need this, floating point does."""
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


def predict_proba(X: np.ndarray, weights: np.ndarray, bias: float) -> np.ndarray:
    """A prediction is a dot product plus a bias, then squashed. The dot
    product X @ weights is a weighted vote: each feature contributes
    weight[i] * X[i] to a running score, and the sign and magnitude of
    that sum is what sigmoid converts into a probability."""
    z = X @ weights + bias
    return sigmoid(z)


def cross_entropy_loss(y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
    """Derived from maximum likelihood estimation on a Bernoulli label,
    not chosen arbitrarily: if you write down "the probability of seeing
    these exact labels, given these predicted probabilities" and take the
    negative log (to turn a product into a sum, and maximization into
    minimization), this formula is what falls out. Clipped away from
    exactly 0 and 1 — log(0) is undefined, and floating point can produce
    a probability that rounds to exactly 0.0 or 1.0."""
    eps = 1e-12
    p = np.clip(y_pred_proba, eps, 1 - eps)
    return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))


def compute_gradients(
    X: np.ndarray, y_true: np.ndarray, y_pred_proba: np.ndarray
) -> tuple[np.ndarray, float]:
    """The gradient of cross-entropy loss with respect to the weights,
    worked out by hand, simplifies to X^T @ (y_pred - y_true) / n — the
    same elegant form every time, regardless of how many features there
    are. That simplicity isn't a coincidence: it's a direct consequence of
    pairing sigmoid with cross-entropy specifically, not an accident of
    this particular problem. Swap in a different loss function and the
    gradient gets meaningfully uglier."""
    n = X.shape[0]
    error = y_pred_proba - y_true  # how wrong, and in which direction
    dw = X.T @ error / n
    db = float(np.mean(error))
    return dw, db


def train_logistic_regression(
    X: np.ndarray,
    y: np.ndarray,
    learning_rate: float = 0.5,
    epochs: int = 200,
) -> tuple[np.ndarray, float, list[float]]:
    """Gradient descent: repeatedly nudge the weights in the direction
    that most reduces the loss, by an amount controlled by learning_rate.
    Nothing here is specific to classification — this is the exact same
    update rule every neural network in this series trains with,
    regardless of how many layers get added on top of it later."""
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


# ── Gradient checking: verifying the calculus by hand, numerically ─────
# A real ML engineering practice, not a teaching contrivance — this is how
# you catch a sign error or a dropped term in a hand-derived gradient
# before it silently trains a broken model for an hour.


def numerical_gradient(
    X: np.ndarray, y: np.ndarray, weights: np.ndarray, bias: float, eps: float = 1e-5
) -> np.ndarray:
    """Approximates dL/dw by nudging each weight up and down slightly and
    measuring the change in loss — the definition of a derivative, made
    literal instead of derived symbolically. Slow (one loss computation
    per weight, per direction) and never used in real training; used
    exactly once, here, to confirm the fast analytical version is correct."""
    grad = np.zeros_like(weights)
    for i in range(len(weights)):
        w_plus = weights.copy()
        w_plus[i] += eps
        w_minus = weights.copy()
        w_minus[i] -= eps

        loss_plus = cross_entropy_loss(y, predict_proba(X, w_plus, bias))
        loss_minus = cross_entropy_loss(y, predict_proba(X, w_minus, bias))
        grad[i] = (loss_plus - loss_minus) / (2 * eps)

    return grad


def _demo() -> None:
    X_raw, y = generate_synthetic_documents(n=200)
    X, mean, std = normalize(X_raw)

    weights, bias, loss_history = train_logistic_regression(X, y, learning_rate=0.5, epochs=200)

    print(f"Loss:  epoch 0 = {loss_history[0]:.4f}  ->  epoch {len(loss_history)-1} = {loss_history[-1]:.4f}")
    print(f"Learned weights: {weights}  bias: {bias:.4f}")

    final_proba = predict_proba(X, weights, bias)
    print(f"Training accuracy: {accuracy(y, final_proba):.2%}")

    print("\n--- Gradient check ---")
    y_pred = predict_proba(X, weights, bias)
    analytical, _ = compute_gradients(X, y, y_pred)
    numerical = numerical_gradient(X, y, weights, bias)
    max_diff = np.max(np.abs(analytical - numerical))
    print(f"Analytical gradient: {analytical}")
    print(f"Numerical gradient:  {numerical}")
    print(f"Max difference: {max_diff:.2e}  (should be tiny)")

    print("\n--- A few real predictions ---")
    for i in range(3):
        raw_features = X_raw[i]
        prob = predict_proba(X[i:i+1], weights, bias)[0]
        label = "long-form" if prob >= 0.5 else "quick-note"
        print(f"  body_length={raw_features[0]:.0f}, word_count={raw_features[1]:.0f}"
              f"  -> P(long-form)={prob:.3f}  -> {label}  (actual: {'long-form' if y[i] else 'quick-note'})")


if __name__ == "__main__":
    _demo()
