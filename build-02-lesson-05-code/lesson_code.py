"""
Cortex — Build 02, Lesson 05
Neural networks from scratch: rebuilding the same classifier by hand
(the "why" lesson).

The question this lesson actually answers: why stack logistic units into
layers at all, instead of just using one (Lesson 01) or a library-tuned
one (Lesson 04)? The honest answer isn't "more layers are always better"
— it's that a single logistic unit has a hard mathematical ceiling: it can
only ever draw a straight decision boundary, and some real problems
aren't solvable by any straight line, no matter how well-trained. Today's
task — flagging a document for review when its urgency and length signals
disagree, but not when they agree — is exactly that kind of problem: XOR,
wearing a Cortex-shaped costume. It's not solvable by one logistic unit
by construction, and a network with even one small hidden layer solves it
cleanly. That contrast is the entire "why."
"""

from __future__ import annotations

import numpy as np


# ── The XOR-shaped problem: needs_review = urgent XOR long ─────────────
# A document flagged "urgent" that's also long might be fine (an urgent,
# thorough incident report). A document that's neither urgent nor long
# might also be fine (a routine short note). But urgent-and-short, or
# long-and-not-urgent, is the actual pattern worth flagging — agreement
# is fine, disagreement is the signal. That's XOR, not "more of both is
# worse" or "more of both is better," which is exactly why a single
# straight-line boundary can't capture it.


def generate_xor_documents(n: int = 400, noise: float = 0.15, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    is_urgent = rng.integers(0, 2, size=n).astype(float)
    is_long = rng.integers(0, 2, size=n).astype(float)
    needs_review = (is_urgent.astype(int) ^ is_long.astype(int)).astype(float)

    X = np.column_stack([is_urgent, is_long])
    X += rng.normal(0, noise, size=X.shape)  # a touch of real-world noise
    return X, needs_review


# ── Lesson 01's single logistic unit, unchanged ────────────────────────


def sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


def cross_entropy_loss(y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
    eps = 1e-12
    p = np.clip(y_pred_proba, eps, 1 - eps)
    return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))


def train_single_unit(
    X: np.ndarray, y: np.ndarray, learning_rate: float = 0.5, epochs: int = 1000
) -> tuple[np.ndarray, float, list[float]]:
    n_features = X.shape[1]
    weights = np.zeros(n_features)
    bias = 0.0
    loss_history: list[float] = []
    for _ in range(epochs):
        z = X @ weights + bias
        y_pred = sigmoid(z)
        loss_history.append(cross_entropy_loss(y, y_pred))
        error = y_pred - y
        dw = X.T @ error / len(y)
        db = float(np.mean(error))
        weights -= learning_rate * dw
        bias -= learning_rate * db
    return weights, bias, loss_history


def single_unit_accuracy(X: np.ndarray, y: np.ndarray, weights: np.ndarray, bias: float) -> float:
    preds = (sigmoid(X @ weights + bias) >= 0.5).astype(int)
    return float(np.mean(preds == y))


# ── A minimal neural network: one hidden layer, from scratch ──────────
# The generalization from Lesson 01 is small and specific: instead of one
# set of weights mapping features straight to an output probability, two
# sets of weights map features to a hidden representation, then that
# hidden representation to an output probability — with a nonlinearity
# (ReLU) in between. That nonlinearity is not decoration; it's the
# entire reason stacking two *linear* layers wouldn't help at all (two
# linear transforms compose into a third linear transform — still just a
# straight line). The nonlinearity is what lets the network bend.


def relu(z: np.ndarray) -> np.ndarray:
    return np.maximum(0, z)


def relu_derivative(z: np.ndarray) -> np.ndarray:
    return (z > 0).astype(float)


def init_params(n_input: int, n_hidden: int, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    # Small random init, not zeros — with zeros, every hidden unit would
    # compute the exact same gradient and stay identical to every other
    # hidden unit forever, which defeats the entire point of having more
    # than one. This is a real failure mode, not a theoretical one.
    return {
        "W1": rng.normal(0, 0.5, size=(n_input, n_hidden)),
        "b1": np.zeros(n_hidden),
        "W2": rng.normal(0, 0.5, size=(n_hidden, 1)),
        "b2": np.zeros(1),
    }


def forward(X: np.ndarray, params: dict) -> dict:
    z1 = X @ params["W1"] + params["b1"]
    a1 = relu(z1)
    z2 = a1 @ params["W2"] + params["b2"]
    a2 = sigmoid(z2).flatten()
    return {"z1": z1, "a1": a1, "z2": z2, "a2": a2}


def backward(X: np.ndarray, y: np.ndarray, params: dict, cache: dict) -> dict:
    """The chain rule, applied twice instead of once. The output layer's
    gradient (dz2) has the exact same clean form as Lesson 01's — that's
    not a coincidence, the sigmoid+cross-entropy pairing still produces
    it. The new part is propagating that error backward through W2 and
    the ReLU derivative to reach the hidden layer's gradients — this is
    literally what "backpropagation" means: the chain rule, run in
    reverse, one layer at a time."""
    n = X.shape[0]

    dz2 = (cache["a2"] - y).reshape(-1, 1) / n
    dW2 = cache["a1"].T @ dz2
    db2 = dz2.sum(axis=0)

    da1 = dz2 @ params["W2"].T
    dz1 = da1 * relu_derivative(cache["z1"])
    dW1 = X.T @ dz1
    db1 = dz1.sum(axis=0)

    return {"dW1": dW1, "db1": db1, "dW2": dW2, "db2": db2}


def train_neural_network(
    X: np.ndarray,
    y: np.ndarray,
    n_hidden: int = 4,
    learning_rate: float = 0.5,
    epochs: int = 2000,
    seed: int = 0,
) -> tuple[dict, list[float]]:
    params = init_params(X.shape[1], n_hidden, seed=seed)
    loss_history: list[float] = []

    for _ in range(epochs):
        cache = forward(X, params)
        loss_history.append(cross_entropy_loss(y, cache["a2"]))
        grads = backward(X, y, params, cache)
        params["W1"] -= learning_rate * grads["dW1"]
        params["b1"] -= learning_rate * grads["db1"]
        params["W2"] -= learning_rate * grads["dW2"]
        params["b2"] -= learning_rate * grads["db2"]

    return params, loss_history


def nn_accuracy(X: np.ndarray, y: np.ndarray, params: dict) -> float:
    preds = (forward(X, params)["a2"] >= 0.5).astype(int)
    return float(np.mean(preds == y))


# ── Gradient checking for the more complex model ───────────────────────


def numerical_gradient_check(X: np.ndarray, y: np.ndarray, params: dict, key: str, eps: float = 1e-5) -> np.ndarray:
    """Same practice as Lesson 01, extended to a multi-layer model. Worth
    doing again specifically because backprop through two layers has more
    places to introduce a sign error or a wrong transpose than a single
    layer does — the more moving parts, the more this check earns its
    keep."""
    grad = np.zeros_like(params[key])
    it = np.nditer(params[key], flags=["multi_index"])
    for _ in it:
        idx = it.multi_index
        original = params[key][idx]

        params[key][idx] = original + eps
        loss_plus = cross_entropy_loss(y, forward(X, params)["a2"])

        params[key][idx] = original - eps
        loss_minus = cross_entropy_loss(y, forward(X, params)["a2"])

        params[key][idx] = original
        grad[idx] = (loss_plus - loss_minus) / (2 * eps)

    return grad


def _demo() -> None:
    X, y = generate_xor_documents(n=400)
    print(f"Dataset: {len(y)} documents, {y.mean():.1%} flagged for review\n")

    print("--- Single logistic unit (Lesson 01's exact approach) ---")
    weights, bias, loss_hist = train_single_unit(X, y, epochs=1000)
    acc = single_unit_accuracy(X, y, weights, bias)
    print(f"Final loss: {loss_hist[-1]:.4f}")
    print(f"Accuracy: {acc:.1%}  <- a single straight-line boundary cannot solve XOR")

    print("\n--- Two-layer neural network (4 hidden units, ReLU) ---")
    params, loss_hist_nn = train_neural_network(X, y, n_hidden=4, epochs=2000)
    acc_nn = nn_accuracy(X, y, params)
    print(f"Final loss: {loss_hist_nn[-1]:.4f}")
    print(f"Accuracy: {acc_nn:.1%}")

    print("\n--- Gradient check on the trained network ---")
    for key in ["W1", "b1", "W2", "b2"]:
        cache = forward(X, params)
        analytical = backward(X, y, params, cache)[f"d{key}"]
        numerical = numerical_gradient_check(X, y, params, key)
        max_diff = np.max(np.abs(analytical - numerical))
        print(f"  {key}: max diff = {max_diff:.2e}")


if __name__ == "__main__":
    _demo()
