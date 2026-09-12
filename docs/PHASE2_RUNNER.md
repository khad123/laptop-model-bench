# Phase 2 — Reasoning + knowledge runner

`./capability.sh` is the Phase 2 entry point. It runs the development multiple-choice capability suite against the **primary capability pool** from `docs/MODEL_REGISTRY.md` using the local K2-compatible `llama-server` build.

Phase 2 is separate from `bench.sh`: Phase 1 measures throughput/resources; Phase 2 measures answer accuracy.

## Current benchmark status

The initial task set is `tasks/phase2_v0.1.json` and is marked **development**. It contains 32 original project-authored multiple-choice tasks:

- 20 reasoning tasks
  - arithmetic
  - multi-step word problems
  - algebra/patterns
  - ARC-style logic/science
- 12 general-knowledge tasks
  - STEM
  - computing
  - humanities
  - social science

The items are not copied from ARC or MMLU. They are original compact tasks inspired by the category goals in the benchmark protocol, which avoids licensing ambiguity while the harness is validated.

Do not call this task set `v1.0` until extraction, scoring, model compatibility, and difficulty have been validated.

## Standard configuration

- Runtime: `~/Models/llama.cpp-k2/build/bin/llama-server`
- CPU threads: `4`
- GPU layers: `0`
- context: `4096`
- temperature: `0`
- seed: `42`
- maximum answer generation: `32` tokens
- prompt cache reuse: disabled
- local GGUF paths only
- Hugging Face / Transformers offline environment enabled
- native model chat template through `/v1/chat/completions`

The runner starts one local server per model, runs all selected tasks, saves the raw response, and shuts the server down before moving to the next model.

## Model selection

By default only the seven **primary** registry entries are tested. Alternate quantizations belong to the later quantization phase and are not mixed into the main capability leaderboard.

Run all primary models:

```bash
./capability.sh
```

Preflight without inference:

```bash
./capability.sh --dry-run
```

Validate one model first:

```bash
./capability.sh --only qwen35-0.8b-q4km
```

Validate one task on one model:

```bash
./capability.sh --only qwen35-0.8b-q4km --task arith-01
```

To deliberately include alternate quantizations:

```bash
./capability.sh --include-comparisons
```

`--only` can also select a comparison entry directly.

## Scoring

Every task has one answer key: `A`, `B`, `C`, or `D`.

The prompt requests a single uppercase letter. The scorer first accepts an exact letter, then a clearly labelled answer such as `Answer: B`, and finally a unique standalone A/B/C/D letter. Ambiguous outputs are marked unparsed rather than guessed.

The runner reports:

- raw accuracy across all 32 tasks
- reasoning accuracy
- knowledge accuracy
- category sub-scores
- answer parse rate
- `phase2_score`: equal-weight average of reasoning accuracy and knowledge accuracy

The equal-domain score prevents the 20 reasoning tasks from silently outweighing the 12 knowledge tasks.

No subjective judge is used in this phase.

## Raw evidence

Raw model/server evidence is saved under:

```text
results/raw/phase2/<run-id>/<model-id>/
```

Each task stores its prompt metadata, request body, HTTP result, raw model response, and timing. The server log is also retained for audit/debugging.

Summaries are written to:

```text
results/phase2-<run-id>.json
results/phase2-<run-id>.csv
results/phase2-latest.json
results/phase2-latest.csv
```

## Failure behavior

A failed request is recorded rather than silently removed from the denominator. A server-start failure marks the model's remaining tasks failed. Other models continue to run.

The process exits with code `2` if any task/model execution failed, while preserving successful results.

## Validation sequence

Before running all seven models:

1. `./capability.sh --dry-run`
2. Run one task on Qwen3.5-0.8B.
3. Run the full 32-task suite on Qwen3.5-0.8B.
4. Inspect parse rate and raw answers.
5. If extraction/scoring is sound, run the seven-model primary pool.
6. Only then decide whether the task set is difficult and balanced enough to freeze as v1.
