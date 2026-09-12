# Phase 4 — MiniSWE runner

Phase 4 tests repository-level software-engineering behavior on tiny project-authored Python repositories. Each task presents an issue description plus multiple visible repository files. Hidden deterministic tests are never included in the model prompt.

## Entry point

```bash
./miniswe.sh
```

The development task set is `tasks/phase4_v0.1.json` and currently contains five tasks. The default model pool is the seven primary quants; add `--include-comparisons` to include all 12 registry entries.

## Protocol

- CPU-only, 4 threads
- context 4096
- temperature 0
- seed 42
- `reasoning_effort=none`
- maximum generation 1024 tokens
- one `llama-server` per model
- no network during hidden-test execution
- Bubblewrap sandbox
- 10 s wall timeout / 4 s CPU limit / 768 MiB address-space limit per test

## Patch format

The model returns only complete replacements for files it changes:

```text
<file path="package/module.py">
...complete replacement file...
</file>
```

Only existing visible repository paths are accepted. Replacement Python is syntax checked and screened for unsafe imports/calls before execution.

This full-file replacement format is deliberate: Phase 4 is intended to test repository understanding and bug fixing, not unified-diff formatting skill. Strict output-format compliance is evaluated separately in Phase 5.

## Scoring

Every task contains multiple hidden checks. A task is reported as:

- `solved` — all hidden checks pass
- `partial` — at least one but not all hidden checks pass
- `failed` — no hidden checks pass, patch parsing fails, or the patch is rejected

`task_score` is the percentage of hidden checks passed. `phase4_score` is the mean task score across selected MiniSWE tasks. Solved/partial/failed counts are also retained so the aggregate score is not opaque.

## Outputs

- `results/phase4-<run-id>.json`
- `results/phase4-<run-id>.csv`
- `results/phase4-latest.json`
- `results/phase4-latest.csv`
- raw model responses, original repositories, patched work trees, test stdout/stderr under `results/raw/phase4/<run-id>/`

## Recommended validation sequence

```bash
./miniswe.sh --dry-run --include-comparisons
./miniswe.sh --only qwen35-2b-q4km --task swe-01
./miniswe.sh --only qwen35-2b-q4km
./miniswe.sh --include-comparisons
```

Do not treat v0.1 as frozen until the single-model pilot confirms patch parsing and task difficulty behave sensibly.
