# Phase 7 — Context runner

Phase 7 measures retrieval and use of information as prompt length grows. It is intentionally separate from instruction-following and coding so formatting mistakes do not dominate the score.

## Entry point

```bash
./context.sh
```

Task file:

```text
tasks/phase7_v0.1.json
```

## v0.1 task set

Nine deterministic tasks are split evenly across approximate prompt-length bands:

- 3 near 1K tokens
- 3 near 2K tokens
- 3 near 4K tokens

Each band includes:

- direct retrieval
- two-fact composition
- relational retrieval

Needles are placed at different positions so the suite exercises early, middle, late, and split evidence.

The task file stores character targets only as a generation target. The runner records the actual `prompt_tokens` returned by `llama-server`; those measured counts are the authoritative prompt-size values for analysis.

## Runtime

- CPU only
- 4 threads
- context window: 8192
- temperature: 0
- seed: 42
- `reasoning_effort=none`
- max output: 64 tokens
- prompt cache disabled

An 8192 runtime context is used so the ~4K input band plus chat-template/system overhead fits without truncation.

## Scoring

Each task is pass/fail based on whether the expected short answer is present in the response. The scorer tolerates short prose or an `Answer:` prefix because Phase 7 is intended to measure context retrieval/use, not strict output formatting.

Reported summaries include:

- overall Phase 7 accuracy
- 1K / 2K / 4K bucket accuracy
- direct / composition / relational accuracy
- 1K-to-4K accuracy degradation
- average measured prompt tokens per bucket

## Commands

Preflight all entries:

```bash
./context.sh --dry-run --include-comparisons
```

Single smoke task:

```bash
./context.sh --only qwen35-2b-q4km --task ctx-4k-03
```

Pilot one model on all tasks:

```bash
./context.sh --only qwen35-2b-q4km
```

Official all-model run:

```bash
./context.sh --include-comparisons
```

## Output

Timestamped summaries:

```text
results/phase7-<run-id>.json
results/phase7-<run-id>.csv
```

Latest aliases:

```text
results/phase7-latest.json
results/phase7-latest.csv
```

Raw per-task artifacts:

```text
results/raw/phase7/<run-id>/<model>/<task>/
```

Each task artifact includes the generated reference text, full prompt, raw response JSON, and model output.
