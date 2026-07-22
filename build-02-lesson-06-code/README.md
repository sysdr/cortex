# Build 02, Lesson 06 — PyTorch fundamentals

Lesson 05's exact two-layer network — `Linear(2,4) -> ReLU -> Linear(4,1)`
— reimplemented in PyTorch. The point isn't a new model; it's proving
`loss.backward()` computes the identical gradients derived by hand last
lesson, then wrapping the same math in real production conventions:
`nn.Module`, `DataLoader`, an optimizer, device handling, checkpointing.

## What this proves

- **Autograd matches hand-derived backprop directly**, not just
  approximately: with identical starting weights, PyTorch's computed
  gradients differ from Lesson 05's manually-derived ones by no more than
  `~7e-9` — essentially float32 precision noise
  (`test_autograd_matches_manual_gradients`).
- **Forgetting `optimizer.zero_grad()` is a real, dangerous bug** —
  verified by actually omitting it: loss looks healthy for the first few
  epochs (0.677 → 0.049), then explodes to 23+ as gradients accumulate
  across every batch forever, ending back at chance accuracy
  (`test_forgetting_zero_grad_causes_training_to_diverge`). It fails
  *after* looking like it's working, which is what makes it dangerous.
- Saving and reloading via `state_dict()` produces bit-identical logits
  (`test_checkpoint_save_and_load_produces_identical_predictions`).

## Quick start

No database needed. **Note:** installing `torch` is a genuinely large
download (700MB+) — this is normal, not a sign something's wrong.

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # if not already active
python lesson_code.py
pytest test_lesson.py -v
```

Actual verified output from this build:

```
Device: cpu

Final loss: 0.0211
Accuracy: 100.0%
Reloaded model accuracy: 100.0%  (should match exactly)

--- Does autograd match Lesson 05's hand-derived gradients? ---
  dW1_max_diff: 7.45e-09
  db1_max_diff: 3.73e-09
  dW2_max_diff: 2.79e-09
  db2_max_diff: 3.73e-09
```

And, separately, the zero_grad() failure mode actually triggered:

```
Without zero_grad(): final loss=23.3793  accuracy=50.2%
Loss history sample: [0.677, 0.600, 0.351, 0.110, 0.049] ... [23.72, 14.34, 3.94, 13.44, 23.38]
```

Notice the first five epochs look completely healthy — that's what makes
this bug worth knowing about specifically, not a generic "remember to
call this method" reminder.

## This lesson's git tag

```bash
git checkout build-02-lesson-06
```

Builds on `build-02-lesson-05`. Build 02's remaining lessons (fine-tuning
prep, the actual `/classify` endpoint) build on this exact checkpointing
pattern — `state_dict()` saved here is the same mechanism that will load
Cortex's real trained classifier into the FastAPI app at the Build 02
milestone.
