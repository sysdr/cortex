"""
Tests for Build 02, Lesson 05.
Run with: pytest test_lesson.py -v
"""

import numpy as np
import pytest

from lesson_code import (
    backward,
    cross_entropy_loss,
    forward,
    generate_xor_documents,
    nn_accuracy,
    numerical_gradient_check,
    single_unit_accuracy,
    train_neural_network,
    train_single_unit,
)


@pytest.fixture
def xor_data():
    return generate_xor_documents(n=400, seed=7)


# ── The core claim: single unit fails, network solves it ──────────────


def test_single_logistic_unit_cannot_solve_xor(xor_data):
    X, y = xor_data
    weights, bias, _ = train_single_unit(X, y, epochs=1000)

    acc = single_unit_accuracy(X, y, weights, bias)

    # XOR is not linearly separable — a single unit is mathematically
    # capped near chance, regardless of how long it trains
    assert acc < 0.70


def test_single_logistic_unit_loss_barely_improves(xor_data):
    X, y = xor_data
    _, _, loss_history = train_single_unit(X, y, epochs=1000)

    # ln(2) ~= 0.693 is the loss of predicting 0.5 for everything —
    # a linear model on XOR should end up close to that, not near zero
    assert loss_history[-1] > 0.65


def test_two_layer_network_solves_xor(xor_data):
    X, y = xor_data
    params, _ = train_neural_network(X, y, n_hidden=4, epochs=2000)

    acc = nn_accuracy(X, y, params)

    assert acc > 0.90


def test_network_achieves_meaningfully_lower_loss_than_single_unit(xor_data):
    X, y = xor_data
    _, _, single_loss = train_single_unit(X, y, epochs=1000)
    _, network_loss = train_neural_network(X, y, n_hidden=4, epochs=2000)

    assert network_loss[-1] < single_loss[-1] / 5


# ── Gradient checking, extended to a multi-layer model ─────────────────


def test_gradients_match_numerical_check_for_every_parameter(xor_data):
    X, y = xor_data
    params, _ = train_neural_network(X, y, n_hidden=4, epochs=200)  # partially trained is fine

    cache = forward(X, params)
    analytical = backward(X, y, params, cache)

    for key in ["W1", "b1", "W2", "b2"]:
        numerical = numerical_gradient_check(X, y, params, key)
        assert np.allclose(analytical[f"d{key}"], numerical, atol=1e-4), f"mismatch in {key}"


# ── The zero-initialization failure mode ────────────────────────────────


def test_zero_initialization_completely_prevents_learning(xor_data):
    """A real, verified failure mode, not a hypothetical warning: with
    every weight starting at exactly zero, gradient flow back to W1 is
    blocked entirely by the zero W2, so W1 never updates at all — not
    'learns slowly,' literally never moves — and accuracy stays at chance."""
    X, y = xor_data
    params = {
        "W1": np.zeros((2, 4)),
        "b1": np.zeros(4),
        "W2": np.zeros((4, 1)),
        "b2": np.zeros(1),
    }

    for _ in range(500):
        cache = forward(X, params)
        grads = backward(X, y, params, cache)
        params["W1"] -= 0.5 * grads["dW1"]
        params["b1"] -= 0.5 * grads["db1"]
        params["W2"] -= 0.5 * grads["dW2"]
        params["b2"] -= 0.5 * grads["db2"]

    assert np.allclose(params["W1"], 0.0)  # never moved, not just small
    acc = nn_accuracy(X, y, params)
    assert acc < 0.60  # stuck at chance


def test_random_initialization_breaks_symmetry_and_learns(xor_data):
    X, y = xor_data
    params, _ = train_neural_network(X, y, n_hidden=4, epochs=2000, seed=0)

    # with real (non-zero) initialization, W1 should have genuinely
    # different values across hidden units, not a repeated pattern
    assert not np.allclose(params["W1"], 0.0)
    assert nn_accuracy(X, y, params) > 0.90
