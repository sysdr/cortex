"""
Tests for Build 02, Lesson 03.
Run with: pytest test_lesson.py -v
"""

import numpy as np
import pytest

from lesson_code import (
    accuracy,
    generate_labeled_corpus,
    naive_random_split,
    normalize,
    polynomial_features,
    predict_proba,
    stratified_split,
    train_logistic_regression,
)


# ── Splitting ───────────────────────────────────────────────────────────


def test_naive_split_produces_variable_positive_rate_across_seeds():
    df = generate_labeled_corpus(n=500)
    y = df["is_official"].to_numpy()

    rates = []
    for seed in range(10):
        _, test_idx = naive_random_split(len(df), test_size=0.3, seed=seed)
        rates.append(y[test_idx].mean())

    # this is the actual point of the lesson: a naive split's test-set
    # class balance genuinely moves around from run to run
    assert np.std(rates) > 0.01


def test_stratified_split_produces_consistent_positive_rate_across_seeds():
    df = generate_labeled_corpus(n=500)
    y = df["is_official"].to_numpy()

    rates = []
    for seed in range(10):
        _, test_idx = stratified_split(y, test_size=0.3, seed=seed)
        rates.append(y[test_idx].mean())

    assert np.std(rates) < 1e-9  # effectively zero, by construction


def test_stratified_split_test_rate_matches_overall_rate():
    df = generate_labeled_corpus(n=500)
    y = df["is_official"].to_numpy()

    _, test_idx = stratified_split(y, test_size=0.3, seed=0)

    assert y[test_idx].mean() == pytest.approx(y.mean(), abs=0.01)


def test_stratified_split_has_no_overlap_between_train_and_test():
    df = generate_labeled_corpus(n=500)
    y = df["is_official"].to_numpy()

    train_idx, test_idx = stratified_split(y, test_size=0.3, seed=0)

    assert set(train_idx).isdisjoint(set(test_idx))
    assert len(train_idx) + len(test_idx) == len(y)


def test_naive_split_has_no_overlap_between_train_and_test():
    train_idx, test_idx = naive_random_split(500, test_size=0.3, seed=0)

    assert set(train_idx).isdisjoint(set(test_idx))
    assert len(train_idx) + len(test_idx) == 500


# ── Polynomial features ─────────────────────────────────────────────────


def test_polynomial_features_produces_expected_column_count():
    X = np.array([[1.0, 2.0], [3.0, 4.0]])

    # degree 2 on 2 base features: [x0, x1, x0^2, x0*x1, x1^2] = 5 columns
    result = polynomial_features(X, degree=2)

    assert result.shape == (2, 5)


def test_polynomial_features_degree_1_is_the_original_features():
    X = np.array([[1.0, 2.0], [3.0, 4.0]])

    result = polynomial_features(X, degree=1)

    assert np.allclose(result, X)


def test_polynomial_features_includes_correct_squared_term():
    X = np.array([[3.0, 5.0]])

    result = polynomial_features(X, degree=2)

    # columns are [x0, x1, x0^2, x0*x1, x1^2] in generation order
    assert result[0, 2] == pytest.approx(9.0)   # 3^2
    assert result[0, 3] == pytest.approx(15.0)  # 3*5
    assert result[0, 4] == pytest.approx(25.0)  # 5^2


# ── Overfitting, demonstrated against real generated data ──────────────


def test_overfitting_gap_widens_from_low_to_high_polynomial_degree():
    """The actual claim of this lesson, checked directly: train the exact
    same loop at low and high polynomial degree, and the train-minus-test
    accuracy gap should be meaningfully larger at high degree."""
    df = generate_labeled_corpus(n=500, seed=7)
    X_raw = df[["body_length", "word_count", "noise_1", "noise_2", "noise_3"]].to_numpy(dtype=float)
    y = df["is_official"].to_numpy()
    train_idx, test_idx = stratified_split(y, test_size=0.3, seed=0)

    def gap_at_degree(degree: int) -> float:
        X_norm = normalize(polynomial_features(X_raw, degree))
        X_train, X_test = X_norm[train_idx], X_norm[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        weights, bias, _ = train_logistic_regression(X_train, y_train, learning_rate=0.3, epochs=500)
        train_acc = accuracy(y_train, predict_proba(X_train, weights, bias))
        test_acc = accuracy(y_test, predict_proba(X_test, weights, bias))
        return train_acc - test_acc

    low_degree_gap = gap_at_degree(1)
    high_degree_gap = gap_at_degree(5)

    assert high_degree_gap > low_degree_gap
    assert high_degree_gap > 0.03  # a real, visible gap, not noise


def test_low_degree_model_generalizes_reasonably():
    df = generate_labeled_corpus(n=500, seed=7)
    X_raw = df[["body_length", "word_count", "noise_1", "noise_2", "noise_3"]].to_numpy(dtype=float)
    y = df["is_official"].to_numpy()
    train_idx, test_idx = stratified_split(y, test_size=0.3, seed=0)

    X_norm = normalize(polynomial_features(X_raw, degree=1))
    weights, bias, _ = train_logistic_regression(
        X_norm[train_idx], y[train_idx], learning_rate=0.3, epochs=500
    )

    train_acc = accuracy(y[train_idx], predict_proba(X_norm[train_idx], weights, bias))
    test_acc = accuracy(y[test_idx], predict_proba(X_norm[test_idx], weights, bias))

    assert abs(train_acc - test_acc) < 0.05
