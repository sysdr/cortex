# Build 02, Lesson 04 — Classical ML with scikit-learn

Cortex's actual category classifier, v1 — the model Lesson 07's
`/classify` endpoint will eventually serve — plus a direct, honest test of
last lesson's teaser: does scikit-learn's regularization actually fix the
overfitting measured by hand in Lesson 03?

## What this proves

- `class_weight="balanced"` measurably changes the precision/recall
  trade-off: without it, this model **never** correctly predicts the rare
  "legal" class (recall 0.00); with it, legal recall rises to 0.50, at the
  cost of a few points of raw accuracy
  (`test_class_weight_balanced_improves_minority_class_recall`).
- Saving and reloading a model via `joblib` produces bit-identical
  predictions (`test_save_and_load_model_produce_identical_predictions`)
  — the actual mechanism Lesson 07's endpoint depends on.
- **The corrected regularization story** (see below) — a real finding
  that contradicts what Lesson 03's "next time" teaser predicted.

## The teaser didn't hold — here's what actually happened

Lesson 03 predicted: "expect `LogisticRegression`'s default regularization
to visibly narrow the gap." Running the actual comparison shows the
opposite at the default setting:

```
Lesson 03 (hand-rolled gradient descent, 500 epochs):
  degree=5  train=0.846  test=0.772  gap=+0.074

scikit-learn at default C=1.0, same degree:
  degree=5  train=0.877  test=0.767  gap=+0.110   <- LARGER, not smaller
```

The reason isn't that regularization doesn't work — it's that this
comparison is confounded. scikit-learn's L-BFGS solver converges much
more precisely than 500 epochs of plain gradient descent did, so the
"regularized" model actually fits the training data *more* tightly
(0.877 vs 0.846) than the hand-rolled "unregularized" one — because the
hand-rolled version never finished converging in the first place. That's
not a fair test of regularization; it's an accidental test of "which
implementation trained longer."

The clean version of the same test — hold the solver fixed, vary only
`C` — shows regularization's real effect clearly:

```
  C=   1000000  train_acc=1.000  test_acc=0.647  gap=+0.353
  C=      1000  train_acc=0.960  test_acc=0.733  gap=+0.227
  C=       1.0  train_acc=0.877  test_acc=0.767  gap=+0.110
  C=       0.1  train_acc=0.809  test_acc=0.740  gap=+0.069
  C=      0.01  train_acc=0.769  test_acc=0.707  gap=+0.062
  C=     0.001  train_acc=0.711  test_acc=0.713  gap=-0.002
```

Monotonic, and unambiguous, once the comparison is actually fair.

## Quick start

No database needed — pure scikit-learn/pandas on synthetic data.

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
python lesson_code.py
pytest test_lesson.py -v
```

## This lesson's git tag

```bash
git checkout build-02-lesson-04
```

Builds on `build-02-lesson-03`. Lesson 05 rebuilds this same classifier as
a neural network from scratch — the "why" lesson — before Lesson 06 makes
it PyTorch-production-shaped.
