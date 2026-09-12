# Phase 5 — Instruction Following

Phase 5 measures whether each local model follows explicit output constraints exactly. It intentionally penalizes extra prose, Markdown fences, missing or forbidden tokens, wrong ordering, and invalid JSON. Unlike Phase 4 MiniSWE, format compliance is part of the benchmark target here.

## Entry point

```bash
./instruction.sh
```

Default task file:

```text
tasks/phase5_v0.1.json
```

## Task set

The development suite contains 16 project-authored tasks across four categories:

- `strict_format` — exact strings, exact line structure, CSV output
- `required_forbidden` — required tokens, forbidden tokens, casing, word/line constraints
- `ordering` — exact or constrained ordering of tokens/steps
- `json_schema` — valid JSON, exact keys, nested keys, values, arrays, and primitive types

Each task has one or more deterministic checks. `task_score` is the percentage of checks passed. `phase5_score` is the mean task score across selected tasks. A task is marked solved only when every check passes.

## Runtime profile

- CPU only
- 4 threads
- context 4096
- temperature 0
- seed 42
- `reasoning_effort=none`
- prompt cache disabled
- max output 256 tokens
- native model chat template through `/v1/chat/completions`

One final newline is ignored for transport tolerance. Other whitespace, preambles, Markdown fences, or extra content remain scoreable failures where the task requires exact output.

## Commands

Preflight all registered quants:

```bash
./instruction.sh --dry-run --include-comparisons
```

Single smoke task:

```bash
./instruction.sh --only qwen35-2b-q4km --task if-13
```

Full pilot on one model:

```bash
./instruction.sh --only qwen35-2b-q4km
```

All 12 model/quant entries:

```bash
./instruction.sh --include-comparisons
```

## Artifacts

Timestamped JSON/CSV summaries are written under `results/`. Per-task raw API responses, raw model text, and deterministic check details are written under:

```text
results/raw/phase5/<run-id>/<model-id>/<task-id>/
```

The task set remains development status until a pilot confirms that the checks are unambiguous and discriminative.
