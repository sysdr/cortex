# Build 02, Lesson 02 — EDA with NumPy/Pandas

A deliberately messy synthetic corpus — missing bodies, duplicate-ish
titles, imbalanced categories, length outliers — and the pandas toolkit to
actually characterize each of those issues instead of guessing at them.

## What this proves

- `summarize_missingness` correctly quantifies a known, injected pattern
  of missing values (`test_summarize_missingness_matches_a_known_injected_pattern`).
- `detect_outliers_iqr` finds an obvious injected extreme value in a tight
  cluster, and correctly finds *nothing* in genuinely uniform data — an
  outlier detector that flags things in clean data is as broken as one
  that misses real outliers.
- A finding from actually running this on the generated corpus, not
  staged: **40 rows share a duplicate title, but `clean_corpus` removes
  zero rows**, because none of those 40 also share a body. That's the
  correct behavior, not a bug — a shared title is a naming collision, not
  proof of a true duplicate, and conflating the two is exactly the kind
  of mistake that silently deletes real, distinct documents.

## Quick start

No database needed — this lesson is pure pandas/NumPy analysis on
synthetic data.

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
python lesson_code.py        # runs the full EDA pass
pytest test_lesson.py -v
```

Actual verified output from this build:

```
Corpus: 500 documents

--- Missingness ---
id              0.0
title           0.0
body           11.2
category        0.0
tags            0.0
body_length     0.0
word_count      0.0

--- Class balance ---
category
note      0.686
report    0.222
spec      0.076
legal     0.016

--- Duplicate titles ---
40 rows involved in a duplicate title group

--- Body length outliers (IQR method) ---
41 outliers found
           id category  body_length
7    doc-0007   report          959
72   doc-0072   report          852
...

--- body_length describe() ---
count      500.000000
mean       378.366000
std       2008.908088     <- note how far this is from the median
min          0.000000
25%         59.000000
50%        130.500000     <- the median, much more representative
75%        254.750000
max      27766.000000
Name: body_length, dtype: float64

After conservative cleaning: 500 -> 500 rows
```

Notice the gap between `mean` (378) and `50%`/median (130) in the last
block — that gap *is* the outlier problem, visible in the summary
statistics themselves before you even run outlier detection.

## This lesson's git tag

```bash
git checkout build-02-lesson-02
```

Builds on `build-02-lesson-01`. The class imbalance found here
(`note` at 68.6%) is exactly what Lesson 03's train/test split has to
account for — a naive random split can produce a test set with almost no
`legal` documents in it at all.
