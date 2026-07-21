# Build 02, Lesson 01 — Math for ML

A logistic regression classifier, derived and implemented from scratch in
NumPy — no scikit-learn, no PyTorch. This exact classifier is a single
logistic unit; Lesson 05 later stacks more of these into a neural network.

## What this proves

- The analytical gradient (worked out by hand in `compute_gradients`)
  matches a numerical gradient approximation to within `1e-4`
  (`test_analytical_gradient_matches_numerical_gradient`) — the actual
  engineering practice for catching a hand-derivation mistake before it
  silently trains a broken model.
- Gradient descent measurably reduces the loss over training
  (`test_training_reduces_loss`) and reaches >90% accuracy on the
  synthetic, well-separated dataset (`test_training_converges_to_reasonable_accuracy`).
- `sigmoid` saturates to its bounds **asymmetrically** in float64: at
  extreme positive input it rounds to exactly `1.0` (addition rounding —
  `1.0 + tiny` collapses to `1.0`), but at extreme negative input it does
  *not* underflow to exact `0.0` at this implementation's clip range —
  it returns a genuinely tiny but nonzero float
  (`test_sigmoid_saturation_is_asymmetric_at_extreme_inputs`). This wasn't
  planned — an earlier, wrong version of this test assumed symmetric
  saturation and failed against the real implementation; the corrected
  test states what float64 actually does, not what seemed intuitive.

## Quick start

No database needed — this lesson is pure math, no FastAPI, no Postgres.

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
python lesson_code.py        # trains, gradient-checks, shows real predictions
pytest test_lesson.py -v
```

Actual verified output from this build:

```
Loss:  epoch 0 = 0.6931  ->  epoch 199 = 0.0110
Learned weights: [2.65786585 3.11930054]  bias: 0.4921
Training accuracy: 100.00%

--- Gradient check ---
Analytical gradient: [-0.00538714 -0.00759073]
Numerical gradient:  [-0.00538714 -0.00759073]
Max difference: 2.56e-13  (should be tiny)

--- A few real predictions ---
  body_length=69, word_count=22  -> P(long-form)=0.010  -> quick-note  (actual: quick-note)
  body_length=106, word_count=16  -> P(long-form)=0.010  -> quick-note  (actual: quick-note)
  body_length=729, word_count=141  -> P(long-form)=1.000  -> long-form  (actual: long-form)
```

## This lesson's git tag

```bash
git checkout build-02-lesson-01
```

Builds on `build-01-lesson-08` (the Build 01 milestone). Nothing here reads
from or writes to Cortex's actual document store yet — that connection
starts in Lesson 02, once this math is understood on clean synthetic data.
