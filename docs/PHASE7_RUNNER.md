# Phase 7 — Context runner

Phase 7 measures retrieval and use of information as prompt length grows. It is intentionally separate from instruction-following and coding so formatting mistakes do not dominate the score.

## Entry point

```bash
./context.sh
```

Frozen task file:

```text
tasks/phase7_v0.2.json
```

## v0.2 paired task set

Nine deterministic tasks are split evenly across approximate prompt-length bands:

- 3 near 1K tokens
- 3 near 2K tokens
- 3 near 4K tokens

Each band contains the same three task families with the same hidden facts, questions, answer targets, and relative evidence positions:

- direct retrieval
- two-fact numeric composition
- relational retrieval

Only the amount of irrelevant filler grows between 1K, 2K, and 4K. This makes the bucket comparison paired: a 1K-to-4K change is not confounded by using a different question at each length.

The task file stores character targets only as a generation target. The runner records the actual `prompt_tokens` returned by `llama-server`; those measured counts are the authoritative prompt-size values for analysis. In the real laptop runs the nominal bands landed close to the intended ranges, with model-template-dependent token counts.

## Runtime

- CPU only
- 4 threads
- context window: 8192
- temperature: 0
- seed: 42
- `reasoning_effort=none`
- max output: 64 tokens
- prompt cache disabled
- request timeout: 600 seconds by default

An 8192 runtime context is used so the ~4K input band plus chat-template/system overhead fits without truncation.

## Scoring

Each task is pass/fail based on whether the expected short answer is present in the response. The scorer tolerates short prose or an `Answer:` prefix because Phase 7 measures context retrieval/use rather than strict output formatting.

Reported summaries include:

- overall Phase 7 accuracy
- 1K / 2K / 4K bucket accuracy
- direct / composition / relational accuracy
- paired 1K-to-4K accuracy difference
- average measured prompt tokens per bucket

## Validation and infrastructure correction

The first v0.2 all-model run was `20260913T135829Z` (12 models × 9 tasks = 108 evaluations). Eleven models completed normally. SmolLM3-3B IQ4_XS completed all 1K and 2K tasks but its three 4K requests timed out after the earlier sequential requests.

A clean all-model 4K validation run, `20260913T171609Z`, reran the three 4K tasks from a fresh server for every model. Eleven of twelve models reproduced their previous 4K pass/fail pattern exactly. SmolLM3-3B IQ4_XS changed from three infrastructure timeouts to three passes. A separate fresh-server SmolLM3 IQ4_XS 4K run had also passed 3/3.

Therefore the frozen Phase 7 result uses the original full-run results for valid evaluations and replaces only the three invalid SmolLM3 IQ4_XS timeout rows with the clean 4K rerun. This is an infrastructure correction, not a model-score rescue: no ordinary model failures were rerun or replaced.

Corrected Phase 7 v0.2 ranking:

| Rank | Model entry | Score | Solved |
|---:|---|---:|---:|
| 1 | `smollm3-3b-iq4xs` | 100.00% | 9/9 |
| 2= | `qwen35-0.8b-q4km` | 88.89% | 8/9 |
| 2= | `smollm3-3b-q4km` | 88.89% | 8/9 |
| 4= | `qwen35-2b-q4km` | 77.78% | 7/9 |
| 4= | `lfm25-1.2b-q4km` | 77.78% | 7/9 |
| 4= | `llama32-1b-iq4xs` | 77.78% | 7/9 |
| 4= | `qwen35-2b-iq4xs` | 77.78% | 7/9 |
| 8= | `gemma3-1b-q4km` | 66.67% | 6/9 |
| 8= | `llama32-1b-q4km` | 66.67% | 6/9 |
| 10= | `gemma3-1b-iq4xs` | 55.56% | 5/9 |
| 10= | `k2-0.9b-q6k` | 55.56% | 5/9 |
| 12 | `k2-0.9b-q4km` | 44.44% | 4/9 |

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

All-model run:

```bash
./context.sh --include-comparisons
```

For diagnostic reproduction of one length bucket, select its three task IDs explicitly so the model starts that bucket on a fresh server.

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

Phase 7 v0.2 is frozen for the v1 benchmark.
