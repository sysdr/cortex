"""
Tests for Build 02, Lesson 02.
Run with: pytest test_lesson.py -v

The pattern throughout: inject a known issue into a small, controlled
DataFrame, then check the EDA function actually finds exactly that issue —
not just that it runs without error.
"""

import numpy as np
import pandas as pd
import pytest

from lesson_code import (
    class_balance,
    clean_corpus,
    detect_outliers_iqr,
    find_duplicate_titles,
    generate_messy_corpus,
    summarize_missingness,
)


def test_generate_messy_corpus_has_expected_columns():
    df = generate_messy_corpus(n=50)

    expected = {"id", "title", "body", "category", "tags", "body_length", "word_count"}
    assert expected.issubset(set(df.columns))
    assert len(df) == 50


def test_generate_messy_corpus_actually_contains_missing_bodies():
    # if the generator's missingness logic silently broke, every other
    # test in this file that assumes messy data would be testing nothing
    df = generate_messy_corpus(n=500)

    assert df["body"].isna().sum() > 0


def test_summarize_missingness_matches_a_known_injected_pattern():
    df = pd.DataFrame(
        {
            "a": [1, 2, None, 4],       # 25% missing
            "b": [1, None, None, None],  # 75% missing
            "c": [1, 2, 3, 4],           # 0% missing
        }
    )

    result = summarize_missingness(df)

    assert result["a"] == pytest.approx(25.0)
    assert result["b"] == pytest.approx(75.0)
    assert result["c"] == pytest.approx(0.0)


def test_find_duplicate_titles_finds_an_injected_duplicate():
    df = pd.DataFrame(
        {
            "title": ["Alpha", "Beta", "Alpha", "Gamma"],
            "body": ["a", "b", "different body", "g"],
        }
    )

    dupes = find_duplicate_titles(df)

    assert len(dupes) == 2  # both rows titled "Alpha"
    assert set(dupes["title"]) == {"Alpha"}


def test_find_duplicate_titles_returns_empty_when_all_titles_unique():
    df = pd.DataFrame({"title": ["A", "B", "C"], "body": ["1", "2", "3"]})

    dupes = find_duplicate_titles(df)

    assert len(dupes) == 0


def test_class_balance_sums_to_one():
    df = generate_messy_corpus(n=300)

    balance = class_balance(df)

    assert balance.sum() == pytest.approx(1.0, abs=1e-9)


def test_class_balance_reflects_known_imbalance():
    # "note" is generated with p=0.70 — at n=2000 the sample proportion
    # should land close to that, not just "some value or other"
    df = generate_messy_corpus(n=2000)

    balance = class_balance(df)

    assert balance["note"] > 0.60  # comfortably the majority class


def test_detect_outliers_iqr_finds_a_known_extreme_value():
    # a tight cluster around 100, plus one obvious outlier at 10,000
    values = [98, 100, 102, 99, 101, 100, 97, 103, 10_000]
    df = pd.DataFrame({"value": values})

    outliers = detect_outliers_iqr(df, "value")

    assert len(outliers) == 1
    assert outliers.iloc[0]["value"] == 10_000


def test_detect_outliers_iqr_finds_nothing_in_uniform_data():
    df = pd.DataFrame({"value": [10, 11, 12, 13, 14, 15, 16]})

    outliers = detect_outliers_iqr(df, "value")

    assert len(outliers) == 0


def test_clean_corpus_removes_true_exact_duplicates():
    df = pd.DataFrame(
        {
            "title": ["A", "A", "B"],
            "body": ["same body", "same body", "different"],
            "tags": ["x", "x", None],
        }
    )

    cleaned = clean_corpus(df)

    assert len(cleaned) == 2  # the true duplicate collapses to one row


def test_clean_corpus_keeps_same_title_different_body():
    # same title, different body isn't a true duplicate — it's a naming
    # collision, and clean_corpus should NOT treat it as one
    df = pd.DataFrame(
        {
            "title": ["A", "A"],
            "body": ["first body", "second, different body"],
            "tags": ["x", "y"],
        }
    )

    cleaned = clean_corpus(df)

    assert len(cleaned) == 2


def test_clean_corpus_fills_missing_tags_without_dropping_rows():
    df = pd.DataFrame(
        {"title": ["A", "B"], "body": ["a", "b"], "tags": ["urgent", None]}
    )

    cleaned = clean_corpus(df)

    assert len(cleaned) == 2
    assert cleaned["tags"].isna().sum() == 0
