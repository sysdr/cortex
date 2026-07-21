"""
Cortex — Build 02, Lesson 02
EDA with NumPy/Pandas on a real document dataset feeding Cortex's tagger.

Lesson 01's data was synthetic and clean on purpose, so the math was the
only variable. Today's corpus is synthetic too — Cortex doesn't have
enough real production traffic yet to matter — but it's deliberately messy
in the specific ways real document corpora are messy: missing bodies,
near-duplicate titles, wildly imbalanced categories, and length outliers.
This is the diagnostic pass that has to happen before Lesson 04 trains
anything on this data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ── A deliberately messy corpus, with known issues baked in ────────────
# AI relevance: every issue generated here is injected on purpose, with a
# known ground truth, so this lesson's tests can check "did EDA actually
# find what's really there" — not just "does the code run."


def generate_messy_corpus(n: int = 500, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Imbalanced categories — this is realistic, not a contrived example.
    # Most documents in a real system are quick notes; formal reports and
    # legal documents are rare by nature, not by data collection accident.
    categories = rng.choice(
        ["note", "report", "spec", "legal"],
        size=n,
        p=[0.70, 0.20, 0.08, 0.02],
    )

    titles = [f"Document {i}" for i in range(n)]
    # Inject exact duplicate titles — simulating a user who re-saved the
    # same note twice, or an import script that ran without dedup logic
    # (the kind of thing Lesson 06's content-hash dedup exists to prevent
    # going forward — this corpus predates that discipline, on purpose).
    duplicate_indices = rng.choice(n, size=max(1, n // 25), replace=False)
    for idx in duplicate_indices:
        titles[idx] = titles[max(0, idx - 1)]

    body_lengths = rng.lognormal(mean=5.0, sigma=1.0, size=n).astype(int)
    # A handful of genuine outliers — someone pasted an entire transcript
    # into one document. Real, not a data-generation artifact; this
    # happens.
    outlier_indices = rng.choice(n, size=max(1, n // 100), replace=False)
    body_lengths[outlier_indices] = rng.integers(15000, 30000, size=len(outlier_indices))

    bodies = ["x" * length for length in body_lengths]
    # Missing bodies aren't random — "note" category documents are more
    # likely to be title-only captures. Modeling that pattern, not just
    # sprinkling NaN uniformly, is the honest version of this problem.
    missing_mask = (rng.random(n) < 0.15) & (categories == "note")
    bodies = [None if missing else b for b, missing in zip(bodies, missing_mask)]

    tag_pool = ["urgent", "draft", "reviewed", "archived", "external", ""]
    tags = [
        ",".join(rng.choice(tag_pool, size=rng.integers(0, 3), replace=False))
        for _ in range(n)
    ]

    word_counts = np.where(
        [b is None for b in bodies], 0, [len(b or "") // 5 for b in bodies]
    )

    return pd.DataFrame(
        {
            "id": [f"doc-{i:04d}" for i in range(n)],
            "title": titles,
            "body": bodies,
            "category": categories,
            "tags": tags,
            "body_length": [len(b) if b else 0 for b in bodies],
            "word_count": word_counts,
        }
    )


# ── Missingness ─────────────────────────────────────────────────────────


def summarize_missingness(df: pd.DataFrame) -> pd.Series:
    """Percent missing per column. Missingness this uneven across columns
    — body missing far more than title or category — is itself a finding,
    not noise: it usually means the missingness has a cause, not that data
    collection is simply unreliable."""
    return (df.isna().sum() / len(df) * 100).round(2)


# ── Duplicates ──────────────────────────────────────────────────────────


def find_duplicate_titles(df: pd.DataFrame) -> pd.DataFrame:
    """Rows sharing a title with at least one other row. This matters for
    a reason beyond tidiness: if near-duplicate documents end up split
    across train and test sets later (Lesson 03), the model effectively
    gets to see the test set during training, and accuracy numbers stop
    meaning what they claim to mean."""
    dup_mask = df.duplicated(subset="title", keep=False)
    return df.loc[dup_mask].sort_values("title")


# ── Class balance ───────────────────────────────────────────────────────


def class_balance(df: pd.DataFrame, column: str = "category") -> pd.Series:
    """Normalized value counts. A model that always predicts the majority
    class here would score ~70% accuracy while being useless — this
    number is why Lesson 04 won't be able to trust raw accuracy alone."""
    return df[column].value_counts(normalize=True).round(4)


# ── Outliers ────────────────────────────────────────────────────────────


def detect_outliers_iqr(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """The interquartile-range method: flag anything more than 1.5x the
    IQR beyond the 25th/75th percentile. Chosen over "more than N standard
    deviations from the mean" deliberately — extreme outliers inflate the
    mean and standard deviation themselves, which can hide the very
    outliers you're looking for. Percentile-based bounds don't have that
    blind spot."""
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return df[(df[column] < lower) | (df[column] > upper)]


# ── A first-pass cleaning decision ─────────────────────────────────────


def clean_corpus(df: pd.DataFrame) -> pd.DataFrame:
    """Deliberately conservative: drops exact duplicate rows (same title
    AND same body — a true copy, not just a naming collision), fills
    missing tags with an empty string rather than dropping the row, and
    leaves outliers in rather than silently deleting them. Outlier
    handling is a modeling decision, not a cleaning one — Lesson 04
    decides what to do with them, this function just makes them visible."""
    cleaned = df.drop_duplicates(subset=["title", "body"], keep="first").copy()
    cleaned["tags"] = cleaned["tags"].fillna("")
    return cleaned.reset_index(drop=True)


def _demo() -> None:
    df = generate_messy_corpus(n=500)

    print(f"Corpus: {len(df)} documents\n")

    print("--- Missingness ---")
    print(summarize_missingness(df))

    print("\n--- Class balance ---")
    print(class_balance(df))

    print("\n--- Duplicate titles ---")
    dupes = find_duplicate_titles(df)
    print(f"{len(dupes)} rows involved in a duplicate title group")

    print("\n--- Body length outliers (IQR method) ---")
    outliers = detect_outliers_iqr(df, "body_length")
    print(f"{len(outliers)} outliers found")
    if len(outliers):
        print(outliers[["id", "category", "body_length"]].head())

    print("\n--- body_length describe() ---")
    print(df["body_length"].describe())

    cleaned = clean_corpus(df)
    print(f"\nAfter conservative cleaning: {len(df)} -> {len(cleaned)} rows")


if __name__ == "__main__":
    _demo()
