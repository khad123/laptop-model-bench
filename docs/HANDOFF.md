# Session Handoff

## Current state

The v1 laptop benchmark model inventory is downloaded and recorded in `docs/MODEL_REGISTRY.md`, including exact local GGUF sizes.

The benchmark protocol is defined in `docs/BENCHMARK_PROTOCOL.md` and the living work tracker is in `docs/CHECKLIST.md`.

## Important runtime facts

- Target laptop: Intel Core i5 8th gen, 8 GB RAM, CPU-only.
- llama.cpp fork: `~/Models/llama.cpp-k2`
- llama.cpp binary directory: `~/Models/llama.cpp-k2/build/bin/`
- Standard threads: `4`
- Standard context: `4096`
- K2-Horizon support requires the current special llama.cpp fork/branch used on this laptop.

## Existing unofficial K2 speed references

K2-Horizon-0.9B Q4_K_M:

- prompt processing: ~96.96 tok/s
- generation: ~22.93 tok/s

K2-Horizon-0.9B Q6_K:

- prompt processing: ~60.42 tok/s
- generation: ~18.45 tok/s

These must be re-run by the automated runner before becoming official benchmark results.

## Next task

Build Phase 1 speed/efficiency automation.

Create `bench.sh` (or a small script plus config if cleaner) that:

1. Reads the frozen model registry.
2. Runs every v1 model/quant one by one through `llama-bench` using 4 CPU threads.
3. Does not redownload models unnecessarily; uses the Hugging Face cache.
4. Captures raw output per model under `results/raw/`.
5. Extracts prompt-processing and token-generation speed.
6. Records actual GGUF file size.
7. Measures load/runtime timing where practical.
8. Investigates/records peak RAM in a reproducible way.
9. Produces a machine-readable summary (CSV and/or JSON).
10. Continues cleanly if one model fails, while recording the failure.

Do not begin capability/intelligence scoring until the Phase 1 runner and output format are stable.

## Why `./bench.sh` previously failed

The user tried `./bench.sh`, but the file had not been implemented yet. Building it is the immediate next task.
