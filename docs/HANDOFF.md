# Session Handoff

## Current state

The v1 laptop benchmark model inventory is downloaded and recorded in `docs/MODEL_REGISTRY.md`, including exact local GGUF sizes.

The benchmark protocol is defined in `docs/BENCHMARK_PROTOCOL.md` and the living work tracker is in `docs/CHECKLIST.md`.

Phase 1 speed/efficiency automation is now implemented:

- `bench.sh` — single-command entry point containing registry parsing, local HF-cache resolution, sequential `llama-bench` execution, metric extraction, peak-RAM capture, load probe, and CSV/JSON output logic.
- `docs/PHASE1_RUNNER.md` — runner behavior, output format, RAM method, load-probe caveat, and usage.

The runner has been syntax-checked and smoke-tested with fake local GGUF cache entries and a fake `llama-bench`, including continue-on-failure behavior. It has **not** yet been run against the real laptop model pool, so no official Phase 1 measurements exist yet.

## Important runtime facts

- Target laptop: Intel Core i5 8th gen, 8 GB RAM, CPU-only.
- llama.cpp fork: `~/Models/llama.cpp-k2`
- llama.cpp binary directory: `~/Models/llama.cpp-k2/build/bin/`
- Standard threads: `4`
- Standard context: `4096`
- K2-Horizon support requires the current special llama.cpp fork/branch used on this laptop.

## Phase 1 runner defaults

The official default speed run uses:

- 4 CPU threads
- `-ngl 0`
- prompt processing: 512 tokens
- token generation: 128 tokens
- 5 repetitions
- local GGUF paths only; no Hugging Face download path

Raw evidence is saved under `results/raw/<run-id>/`. Machine-readable summaries are written to timestamped CSV/JSON files plus `results/phase1-latest.csv` and `results/phase1-latest.json`.

Peak RAM is measured from the exact `llama-bench` child process using Linux `wait4().ru_maxrss`.

Load timing is a separate tiny process probe and is intentionally recorded as `load_probe_wall_seconds`, not claimed to be a guaranteed cold-load measurement.

## Existing unofficial K2 speed references

K2-Horizon-0.9B Q4_K_M:

- prompt processing: ~96.96 tok/s
- generation: ~22.93 tok/s

K2-Horizon-0.9B Q6_K:

- prompt processing: ~60.42 tok/s
- generation: ~18.45 tok/s

These must still be re-run by the automated runner before becoming official benchmark results.

## Next task

On the target laptop, from the repository root:

```bash
./bench.sh --dry-run
```

Confirm all frozen registry entries resolve from the existing Hugging Face cache. Then run:

```bash
./bench.sh
```

After the run:

1. Inspect `results/phase1-latest.csv` / `.json`.
2. Check any failed row's matching files under `results/raw/<run-id>/`.
3. Sanity-check K2 Q4_K_M and Q6_K against the old unofficial references.
4. Only mark the Phase 1 measurement tasks complete after the real run is stable.

Do not begin capability/intelligence scoring until the Phase 1 runner and real output format/results have been validated on the laptop.
