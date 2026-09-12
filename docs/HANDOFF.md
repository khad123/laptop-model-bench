# Session Handoff

## Current state

The v1 laptop model inventory is recorded in `docs/MODEL_REGISTRY.md`, and the benchmark protocol is defined in `docs/BENCHMARK_PROTOCOL.md`.

### Phase 1 — completed on the target laptop

The speed/efficiency runner is implemented in `bench.sh` and has now been run against the real 12-entry pool on the target Intel 8th-gen i5 / 8 GB CPU-only laptop.

Validated Phase 1 measurements now include:

- prompt-processing throughput
- token-generation throughput
- peak child-process RSS
- average CPU usage and normalized four-thread utilization
- best-effort load probe
- actual local model size / identity
- raw llama-bench evidence

All 12 registry entries completed successfully. Noisy entries were rerun, including K2 Q4 and Gemma Q4 validation passes. Phase 1 is considered sufficiently validated to proceed.

The official runner profile remains:

- llama.cpp fork: `~/Models/llama.cpp-k2`
- 4 CPU threads
- `-ngl 0`
- pp512
- tg128
- 5 repetitions

### Phase 2 — implementation started

Phase 2 measures reasoning and compact general knowledge with deterministic objective scoring.

New files:

- `capability.sh` — starts local `llama-server`, runs identical multiple-choice tasks, saves raw responses, extracts A/B/C/D, and produces JSON/CSV summaries.
- `tasks/phase2_v0.1.json` — 32 original development tasks: 20 reasoning + 12 knowledge.
- `docs/PHASE2_RUNNER.md` — runner rules and validation sequence.

Default Phase 2 configuration:

- primary capability pool only (7 models)
- 4 CPU threads
- CPU-only (`-ngl 0`)
- context 4096
- temperature 0
- seed 42
- max 32 output tokens
- native chat template via local `/v1/chat/completions`
- prompt-cache reuse disabled
- offline local model paths only

Phase 2 score is the equal-weight mean of reasoning accuracy and knowledge accuracy. Raw overall accuracy and category sub-scores remain visible.

The task set is currently `phase2-v0.1` / development, not frozen v1.0. It must be validated for parsing, model compatibility, difficulty, and balance before freezing.

## Immediate next task

On the target laptop:

```bash
git pull
./capability.sh --dry-run
```

If all seven primary models and all 32 tasks preflight correctly, run the smallest smoke test:

```bash
./capability.sh --only qwen35-0.8b-q4km --task arith-01
```

Inspect the terminal score and the raw response under `results/raw/phase2/<run-id>/qwen35-0.8b-q4km/`.

If that works, run the full 32-task suite on Qwen3.5-0.8B before launching all seven primary models:

```bash
./capability.sh --only qwen35-0.8b-q4km
```

Do not freeze Phase 2 v1 or launch later coding/MiniSWE/instruction/tool/context phases until Phase 2 extraction and scoring have been validated.
