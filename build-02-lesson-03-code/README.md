# Build 02, Lesson 03 — Train/test split & overfitting

Two things demonstrated live, not just described: a naive random split's
class balance genuinely wobbles from run to run on imbalanced data, and
the exact, unmodified training loop from Lesson 01 visibly overfits once
it's given more polynomial capacity than 500 documents can support.

## What this proves

- **Split variance is real, not theoretical.** Across 10 random seeds, a
  naive split's test-set positive rate has real spread (`std > 0.01`);
  a stratified split's spread is effectively zero, by construction
  (`test_stratified_split_produces_consistent_positive_rate_across_seeds`).
- **Overfitting actually happens**, using Lesson 01's training loop
  completely unmodified: the train/test accuracy gap is measurably
  larger at polynomial degree 5 than at degree 1
  (`test_overfitting_gap_widens_from_low_to_high_polynomial_degree`).
- The corpus was redesigned mid-build after an early version had **zero
  real signal** between features and label — every model scored at the
  majority-class baseline regardless of complexity, which taught nothing.
  Documented, not hidden — see the note below.

## A design mistake worth knowing about

An earlier version of this lesson's data generator assigned `is_official`
completely independently of `body_length`/`word_count`. Every model,
regardless of polynomial degree, scored right around 68.6% — the
majority-class baseline — because there was no real relationship to find.
That's not overfitting, that's a broken demo. The fix: `body_length` now
genuinely (if noisily) differs by class, and three explicit noise columns
were added specifically to give a high-capacity model something spurious
to latch onto — which is a more realistic cause of real-world overfitting
than raw polynomial degree on already-meaningful features alone.

## Quick start

No database needed — pure NumPy/pandas on synthetic data.

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
python lesson_code.py
pytest test_lesson.py -v
```

Actual verified output from this build:

```
Corpus: 500 documents, 31.8% official

--- Naive random split: test-set positive rate across 5 seeds ---
  seed=0: 29.3%
  seed=1: 33.3%
  seed=2: 28.0%
  seed=3: 35.3%
  seed=4: 34.0%
  std across seeds: 0.0283

--- Stratified split: test-set positive rate across 5 seeds ---
  seed=0: 31.5%
  seed=1: 31.5%
  seed=2: 31.5%
  seed=3: 31.5%
  seed=4: 31.5%
  std across seeds: 0.0000

--- Overfitting curve: same training loop, increasing polynomial degree ---
(body_length + word_count carry real signal; noise_1..3 carry none)

  degree=1  features=   5  train_acc=0.769  test_acc=0.785  gap=-0.016
  degree=2  features=  20  train_acc=0.783  test_acc=0.805  gap=-0.022
  degree=3  features=  55  train_acc=0.815  test_acc=0.779  gap=+0.036
  degree=4  features= 125  train_acc=0.840  test_acc=0.779  gap=+0.062
  degree=5  features= 251  train_acc=0.846  test_acc=0.772  gap=+0.074
```

Notice degree 1–2: test accuracy is actually *higher* than train (normal
noise at low complexity, nothing to worry about). By degree 5, train
accuracy has climbed nearly 8 points past where test accuracy started —
the model is fitting something in the training set that doesn't
generalize, using 251 features to describe patterns in noise, on top of
only 350 training rows.

## This lesson's git tag

```bash
git checkout build-02-lesson-03
```

Builds on `build-02-lesson-02`. Lesson 04 trains a real classifier with
scikit-learn, whose default `LogisticRegression` includes L2
regularization out of the box — the direct fix for exactly the overfitting
watched happening here by hand.
