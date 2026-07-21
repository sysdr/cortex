"""
Tests for Build 02, Lesson 01.
Run with: pytest test_lesson.py -v
"""

import numpy as np
import pytest

from lesson_code import (
    accuracy,
    compute_gradients,
    cross_entropy_loss,
    generate_synthetic_documents,
    normalize,
    numerical_gradient,
    predict_proba,
    sigmoid,
    train_logistic_regression,
)


def test_sigmoid_of_zero_is_one_half():
    assert sigmoid(np.array([0.0]))[0] == pytest.approx(0.5)


def test_sigmoid_saturates_toward_bounds():
    assert sigmoid(np.array([50.0]))[0] == pytest.approx(1.0, abs=1e-6)
    assert sigmoid(np.array([-50.0]))[0] == pytest.approx(0.0, abs=1e-6)


def test_sigmoid_stays_strictly_inside_unit_interval_for_moderate_inputs():
    # Mathematically, sigmoid never reaches 0 or 1 — but float64 can only
    # represent so much precision near those bounds. At |z| this size,
    # exp(-z) is still well above machine epsilon relative to 1.0, so the
    # strict inequality holds in floating point too, not just in theory.
    z = np.array([-30.0, -1.0, 0.0, 1.0, 30.0])
    p = sigmoid(z)
    assert np.all(p > 0.0)
    assert np.all(p < 1.0)


def test_sigmoid_saturation_is_asymmetric_at_extreme_inputs():
    # The two bounds saturate for genuinely different floating-point
    # reasons, not the same one:
    #   - At z=+1000 (clipped to 500), exp(-500) ~ 7e-218. Added to 1.0,
    #     that's so far below machine epsilon that 1.0 + 7e-218 rounds to
    #     exactly 1.0 in float64 — so sigmoid saturates to exact 1.0.
    #   - At z=-1000 (clipped to -500), exp(500) is a huge but perfectly
    #     representable float64 (~1.4e217), and 1 divided by it is a tiny
    #     but still nonzero, representable number (~7e-218) — float64
    #     represents numbers down to ~1e-324, far below this. It does NOT
    #     underflow to exact 0.0 at this clip range.
    # Two different floating-point mechanisms, two different outcomes —
    # worth knowing before trusting "close enough to 0 or 1" as symmetric.
    z = np.array([-1000.0, 1000.0])
    p = sigmoid(z)
    assert p[1] == 1.0          # saturates exactly, via addition rounding
    assert 0.0 < p[0] < 1e-200  # tiny but real — no underflow at this range


def test_cross_entropy_loss_is_near_zero_for_confident_correct_predictions():
    y_true = np.array([1.0, 0.0, 1.0])
    y_pred = np.array([0.999, 0.001, 0.999])

    loss = cross_entropy_loss(y_true, y_pred)

    assert loss < 0.01


def test_cross_entropy_loss_is_large_for_confident_wrong_predictions():
    y_true = np.array([1.0, 0.0])
    y_pred = np.array([0.001, 0.999])  # confidently wrong both times

    loss = cross_entropy_loss(y_true, y_pred)

    assert loss > 5.0


def test_gradients_have_correct_shape():
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    y_true = np.array([0.0, 1.0, 1.0])
    y_pred = np.array([0.3, 0.6, 0.8])

    dw, db = compute_gradients(X, y_true, y_pred)

    assert dw.shape == (2,)
    assert isinstance(db, float)


def test_analytical_gradient_matches_numerical_gradient():
    """The test that actually catches a hand-derivation mistake: if the
    calculus in compute_gradients is wrong, this fails, even though every
    other test might still accidentally pass."""
    X_raw, y = generate_synthetic_documents(n=40, seed=1)
    X, _, _ = normalize(X_raw)
    weights = np.array([0.3, -0.2])
    bias = 0.1

    y_pred = predict_proba(X, weights, bias)
    analytical, _ = compute_gradients(X, y, y_pred)
    numerical = numerical_gradient(X, y, weights, bias)

    assert np.allclose(analytical, numerical, atol=1e-4)


def test_training_reduces_loss():
    X_raw, y = generate_synthetic_documents(n=200, seed=2)
    X, _, _ = normalize(X_raw)

    _, _, loss_history = train_logistic_regression(X, y, learning_rate=0.5, epochs=100)

    assert loss_history[-1] < loss_history[0]


def test_training_converges_to_reasonable_accuracy_on_separable_data():
    X_raw, y = generate_synthetic_documents(n=300, seed=3)
    X, _, _ = normalize(X_raw)

    weights, bias, _ = train_logistic_regression(X, y, learning_rate=0.5, epochs=300)
    preds = predict_proba(X, weights, bias)

    # the synthetic classes are well-separated by design — a correctly
    # trained classifier should comfortably clear 90%
    assert accuracy(y, preds) > 0.9


def test_normalize_produces_zero_mean_unit_std():
    X = np.array([[10.0, 100.0], [20.0, 200.0], [30.0, 300.0]])

    X_norm, mean, std = normalize(X)

    assert np.allclose(X_norm.mean(axis=0), 0.0, atol=1e-10)
    assert np.allclose(X_norm.std(axis=0), 1.0, atol=1e-10)
