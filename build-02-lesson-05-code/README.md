# Build 02, Lesson 05 — Neural networks from scratch (the "why" lesson)

Lesson 01's single logistic unit, and a two-layer neural network built by
hand right alongside it, both trained on the exact same problem — so the
difference between them isn't a claim, it's a number you can watch happen.

## The problem, on purpose

`needs_review = is_urgent XOR is_long` — a document gets flagged when its
urgency and length signals *disagree*, not when both are true or both are
false. This is XOR, and XOR is the textbook example of a pattern no
straight line can separate, no matter how it's trained.

## What this proves

- **The single logistic unit is mathematically stuck**, not just
  under-trained: accuracy tops out at 58.8%, barely above the 50% chance
  baseline, and the loss barely moves off `ln(2) ≈ 0.693` — the loss of
  predicting "50/50" for everything (`test_single_logistic_unit_cannot_solve_xor`).
- **A two-layer network with 4 hidden units solves it cleanly**: 98.5%
  accuracy, loss down to 0.03 (`test_two_layer_network_solves_xor`).
- **Zero-initialization completely prevents learning** — not slow
  learning, *zero* learning: with every weight starting at exactly 0,
  `W1` never moves from all-zeros through 500 epochs of training, because
  the zero `W2` blocks all gradient flow back to it
  (`test_zero_initialization_completely_prevents_learning`) — verified
  directly, not just asserted in a comment.
- Gradient checking, extended from Lesson 01's single layer to all four
  parameter groups of a two-layer network, matches the numerical
  approximation to within `1e-4` for every one of them.

## Quick start

No database needed — pure NumPy on synthetic XOR-shaped data.

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
python lesson_code.py
pytest test_lesson.py -v
```

Actual verified output from this build:

```
Dataset: 400 documents, 50.2% flagged for review

--- Single logistic unit (Lesson 01's exact approach) ---
Final loss: 0.6909
Accuracy: 58.8%  <- a single straight-line boundary cannot solve XOR

--- Two-layer neural network (4 hidden units, ReLU) ---
Final loss: 0.0297
Accuracy: 98.5%

--- Gradient check on the trained network ---
  W1: max diff = 3.18e-12
  b1: max diff = 4.59e-12
  W2: max diff = 3.71e-13
  b2: max diff = 1.04e-13
```

## This lesson's git tag

```bash
git checkout build-02-lesson-05
```

Builds on `build-02-lesson-04`. Lesson 06 takes this exact architecture —
same forward pass, same backprop logic — and rebuilds it in PyTorch,
production-shaped, so the manual chain-rule bookkeeping done by hand today
becomes `loss.backward()` with full understanding of what that call is
actually doing underneath.
