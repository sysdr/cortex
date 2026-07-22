# Build 02 Milestone — the `/classify` endpoint

Every document uploaded to Cortex gets auto-tagged by a model you
trained. Lesson 04's scikit-learn classifier and Build 01's Postgres-backed
`DocumentService` meet here for the first time.

## Honest caveat, up front

Cortex doesn't have real production traffic yet, so `train_classifier.py`
bootstraps the shipped `model.joblib` on the same synthetic corpus Lesson
04 used — not real Cortex documents. The interface this milestone exposes
(features in, category + confidence out) doesn't change once there's real
data to retrain on; only what `train_classifier.py` reads from does.

## What this proves

- **Auto-tagging actually works end to end**, verified with a real running
  server and real `curl` calls, not just the test client — a short note
  classified as `note` (confidence 0.97), a long legal-shaped document
  classified as `spec` (confidence 0.90, **not** `legal`, because `legal`
  is only 1.6% of the bootstrap training data — an honest result, not a
  cherry-picked one).
- **Auto-tagging and the standalone `/classify` endpoint agree** on
  identical input, verified directly
  (`test_auto_tagging_agrees_with_standalone_classify_for_the_same_input`)
  — they're the same underlying function call, and this test would catch
  it if they ever drifted apart.
- **A dedup hit preserves the original category** instead of
  reclassifying — verified directly, not just asserted — so
  classification results don't depend on submission order.
- **Graceful degradation, verified, not assumed**: with no classifier
  loaded, document creation still succeeds (`category: null`) while the
  standalone `/classify` endpoint correctly fails loud with a `503` —
  different failure behavior for a required feature versus an optional one.

## Quick start

```bash
chmod +x setup.sh
./setup.sh

source .venv/bin/activate    # required — do not use system python/pytest
uvicorn lesson_code:app --reload
```

In another terminal:

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"title":"quick note","body":"lunch at noon","tags":[]}'
# {"category":"note","confidence":0.97...}

curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"title":"Onboarding","body":"Welcome to the team.","owner_id":"user-1","tags":["welcome"]}'
# category is populated automatically — no separate classify call needed
```

Run the tests:

```bash
./test.sh -v
# or, after activating .venv: pytest test_lesson.py -v
```

## This lesson's git tag

```bash
git checkout build-02-lesson-07
```

This is Build 02, complete. Build 03 begins: **Tokenization & NLP
preprocessing**, applied to the real Cortex corpus this milestone's
`/classify` endpoint has been tagging.
