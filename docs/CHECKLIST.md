# Checklist

Status legend:

- [ ] Planned / not started
- [x] Done
- [~] In progress

## Phase 0 — Methodology

- [x] Create GitHub repository
- [x] Add project README
- [x] Add project plan
- [x] Add living checklist
- [x] Add benchmark protocol
- [x] Freeze v1 model list
- [x] Freeze primary quantization for every base model
- [x] Freeze v1 task set category by category
- [x] Freeze final scoring weights / leaderboard rules

## Phase 1 — Inventory + speed

- [x] Create model registry
- [x] Add K2-Horizon-0.9B Q4_K_M
- [x] Add Qwen3.5-0.8B Q4_K_M
- [x] Add Qwen3.5-2B Q4_K_M
- [x] Add Qwen3.5-2B IQ4_XS as quant comparison
- [x] Add LFM2.5-1.2B-Instruct Q4_K_M
- [x] Add SmolLM3-3B IQ4_XS primary + Q4_K_M comparison
- [x] Add Gemma 3 1B IQ4_XS primary + Q4_K_M comparison
- [x] Add Llama 3.2 1B Instruct IQ4_XS primary + Q4_K_M comparison
- [x] Record K2 Q6_K as quant comparison
- [x] Identify/exclude old LFM2-1.2B HIP-optimized file from primary leaderboard
- [x] Identify/exclude Ollama Llama 3.2 duplicate from primary leaderboard
- [x] Identify/exclude Qwen mmproj files as non-standalone models
- [x] Build automated llama-bench runner
- [x] Save raw benchmark output from the real laptop run
- [x] Measure prompt processing speed
- [x] Measure generation speed
- [x] Measure load time
- [x] Measure on-disk size in the real run summary
- [x] Investigate reliable peak-RAM measurement
- [x] Record peak RAM from the real laptop run
- [x] Re-run K2 baseline under final protocol

Runner implementation notes:

- Entry point: `./bench.sh`
- Local HF cache only; missing models fail without redownloading.
- Peak RSS: exact child `wait4().ru_maxrss` on Linux.
- CPU usage: child `wait4()` user/system time, reported as process CPU % and normalized four-thread utilization.
- Raw per-model output: `results/raw/<run-id>/`.
- Summary: timestamped CSV/JSON plus `results/phase1-latest.*`.
- Phase 1 is frozen.

## Phase 2 — Reasoning + knowledge

- [x] Choose compact project-authored reasoning task source
- [x] Add arithmetic / multi-step reasoning set
- [x] Add ARC-style reasoning set
- [x] Add compact MMLU-style knowledge set
- [x] Add deterministic scorer
- [x] Validate answer extraction and model/template compatibility
- [x] Balance A/B/C/D answer positions
- [x] Review task difficulty after pilot/full runs
- [x] Freeze final Phase 2 v0.3 task set
- [x] Run all 12 model/quant entries

Phase 2 implementation notes:

- Entry point: `./capability.sh`
- Frozen task file: `tasks/phase2_v0.3.json`
- 32 objective multiple-choice tasks: 20 reasoning + 12 knowledge.
- Direct-choice grammar constrains output to A/B/C/D.
- Runtime: local `llama-server`, 4 threads, CPU-only, context 4096, temperature 0, seed 42, prompt cache disabled, `reasoning_effort=none`.
- `phase2_score`: equal-weight mean of reasoning accuracy and knowledge accuracy.
- Final 12-model v0.3 run completed with 100% parse rate.

## Phase 3 — Coding

- [x] Define compact HumanEval+/MBPP+-style project-authored task set
- [x] Build safe local execution harness
- [x] Add deterministic pass/fail scorer
- [x] Save generated code and test output
- [x] Define timeout/resource limits
- [x] Validate Bubblewrap network isolation and failure detection
- [x] Run single-model pilot
- [x] Audit pilot failures against generated code
- [x] Run all 12 model/quant entries
- [x] Freeze Phase 3 v0.1 behavior for v1 benchmark

Phase 3 implementation notes:

- Entry point: `./coding.sh`
- Task file: `tasks/phase3_v0.1.json`
- 12 Python function-generation tasks with hidden deterministic tests.
- Model-generated Python executes inside Bubblewrap with network disabled and CPU/RAM/time limits.
- Full run completed: 12 models × 12 tasks = 144 evaluations with no infrastructure errors.

## Phase 4 — MiniSWE

- [x] Define MiniSWE task format
- [x] Create task 01
- [x] Create task 02
- [x] Create task 03
- [x] Create task 04
- [x] Create task 05
- [x] Decide five tasks are sufficient for compact v1 MiniSWE coverage
- [x] Build patch/apply/test harness
- [x] Score solved / partially solved / failed
- [x] Add partial hidden-check score
- [x] Validate patch parsing and task difficulty with pilot model
- [x] Correct final-file closing-tag tolerance for repository-fixing focus
- [x] Correct swe-05 rounding expectation
- [x] Run all 12 model/quant entries
- [x] Audit parse/syntax/import failures against raw model output
- [x] Freeze Phase 4 v0.2 task set and behavior

Phase 4 implementation notes:

- Entry point: `./miniswe.sh`
- Frozen task file: `tasks/phase4_v0.2.json`
- Five tiny multi-file Python repositories with issue descriptions and hidden tests.
- Models return complete replacements for changed files; the parser requires valid file-path openings but tolerates a missing final closing tag because strict formatting is measured separately in Phase 5.
- Hidden tests run in Bubblewrap with network disabled and resource limits.
- `task_score` is hidden checks passed; `phase4_score` is the mean task score.
- Final run completed: 12 models × 5 tasks = 60 evaluations. Remaining parse/syntax/import failures were audited and confirmed to be genuine unusable model outputs or destructive patches rather than infrastructure faults.

## Phase 5 — Instruction following

- [x] Define task schema
- [x] Create strict formatting tests
- [x] Create forbidden/required token tests
- [x] Create ordering tests
- [x] Create JSON/schema tests
- [x] Implement deterministic checker
- [x] Add partial per-constraint scoring and category summaries
- [x] Validate task behavior with a pilot model
- [x] Review task difficulty / ambiguity
- [x] Run all 12 model/quant entries
- [x] Freeze Phase 5 v0.1 task set

Phase 5 implementation notes:

- Entry point: `./instruction.sh`
- Frozen task file: `tasks/phase5_v0.1.json`
- 16 project-authored deterministic tasks: four each for strict formatting, required/forbidden content, ordering, and JSON/schema compliance.
- Exact-output tasks intentionally penalize extra prose and Markdown. One final newline is ignored as transport tolerance.
- `task_score` is constraints passed; `phase5_score` is the mean task score. Full-task solved counts and per-category means are retained.
- Final run completed: 12 models × 16 tasks = 192 evaluations with no infrastructure errors.
- Phase 5 winner: K2-Horizon-0.9B Q6_K at 87.50%, followed by Qwen3.5-2B Q4_K_M and IQ4_XS at 83.33%.

## Phase 6 — Tool / agent benchmark

- [x] Define local mock tools
- [x] Create simple single-tool tasks
- [x] Create similar-tool disambiguation tasks
- [x] Create missing-argument tasks
- [x] Create multi-step tasks
- [x] Score tool choice
- [x] Score arguments
- [x] Score structured-output validity
- [x] Run Qwen3.5-2B Q4_K_M pilot
- [x] Run all 12 model/quant entries
- [x] Freeze Phase 6 v0.1 task set and behavior

Phase 6 implementation notes:

- Entry point: `./agent.sh`
- Frozen task file: `tasks/phase6_v0.1.json`
- Ten deterministic BFCL-style local-tool tasks: 3 single-tool, 3 disambiguation, 2 missing-information, and 2 multi-step agent tasks.
- The model emits strict JSON actions; the runner executes deterministic mock tools locally and feeds tool results back for the next action.
- Scoring separately records structured-action validity, tool choice, arguments, sequence, and final outcome; the phase score is the mean per-task score.
- Final run completed: 12 models × 10 tasks = 120 evaluations with no infrastructure errors.
- Phase 6 winner: Qwen3.5-2B Q4_K_M at 100.00%, followed by Qwen3.5-2B IQ4_XS at 94.00%. K2-Horizon-0.9B Q4_K_M placed third at 54.00%.

## Phase 7 — Context

- [x] Create ~1K context tests
- [x] Create ~2K context tests
- [x] Create ~4K context tests
- [x] Measure retrieval accuracy
- [x] Measure answer quality degradation
- [x] Pair the same task families across 1K / 2K / 4K to remove question-difficulty confounding
- [x] Validate measured prompt-token bands
- [x] Run all 12 model/quant entries
- [x] Audit and correct infrastructure-only 4K timeouts
- [x] Freeze Phase 7 v0.2 task set and corrected results

Phase 7 implementation notes:

- Entry point: `./context.sh`
- Frozen task file: `tasks/phase7_v0.2.json`
- Nine paired deterministic tasks: the same direct-retrieval, two-fact composition, and relational-retrieval problems are repeated at ~1K, ~2K, and ~4K prompt lengths; only irrelevant filler grows.
- Runtime: CPU-only, 4 threads, context 8192, temperature 0, seed 42, prompt cache disabled, `reasoning_effort=none`, max output 64.
- Full v0.2 run `20260913T135829Z` completed 108 evaluations, but SmolLM3 IQ4_XS encountered three 4K infrastructure timeouts after completing 1K/2K.
- Fresh all-model 4K validation `20260913T171609Z` reproduced every other model's 4K pass/fail pattern exactly; SmolLM3 IQ4_XS changed from timeout to 3/3 PASS. Only those invalid timeout rows are replaced in the frozen result.
- Corrected Phase 7 winner: SmolLM3-3B IQ4_XS at 100.00% (9/9), followed by Qwen3.5-0.8B Q4_K_M and SmolLM3-3B Q4_K_M at 88.89%.

## Phase 8 — Quantization

- [x] K2 Q4_K_M vs Q6_K combined comparison
- [x] Qwen3.5-2B Q4_K_M vs IQ4_XS combined comparison
- [x] SmolLM3 Q4_K_M vs IQ4_XS combined comparison
- [x] Gemma 3 1B Q4_K_M vs IQ4_XS combined comparison
- [x] Llama 3.2 1B Q4_K_M vs IQ4_XS combined comparison
- [x] Decide whether additional same-base quant comparisons are useful

Phase 8 implementation notes:

- Analysis document: `docs/PHASE8_QUANTIZATION.md`.
- No new model inference was required; Phase 8 combines the frozen Phase 1–7 measurements.
- Recommended v1 quants: K2 Q4_K_M, Qwen3.5-2B Q4_K_M, SmolLM3 IQ4_XS, Gemma 3 1B Q4_K_M, and Llama 3.2 1B Q4_K_M.
- Additional quant sweeps are deferred to a possible v1.1 because they are not needed to change the v1 decisions.

## Phase 9 — Results

- [x] Define final JSON result schema
- [x] Export consolidated CSV summary
- [x] Generate per-model report
- [x] Generate category leaderboards
- [x] Generate overall laptop recommendation
- [x] Generate quality-per-GB ranking
- [x] Generate quantization trade-off ranking
- [x] Freeze final scoring weights after sensitivity review

Phase 9 implementation notes:

- Builder: `scripts/build_phase9_report.py`.
- Frozen outputs: `results/phase9-consolidated.json`, `results/phase9-consolidated.csv`, and `results/phase9-report.md`.
- Frozen overall weighting: 85% capability / 15% laptop efficiency, with transparent category and efficiency subweights documented in `docs/PHASE9_SCORING.md`.
- Qwen3.5-2B Q4_K_M is the robust overall winner across all tested sensitivity profiles.

## Phase 10 — Polish

- [x] Single-command speed runner
- [x] System metadata capture
- [x] Documentation for adding models
- [x] Documentation for adding tasks
- [x] Charts / plots
- [~] Commit frozen release summaries and charts
- [ ] Tag and publish v1.0.0

## Current immediate next steps

1. Commit only the frozen Phase 1–7 source summaries, final Phase 9 artifacts, and generated SVG charts.
2. Verify the repository is clean and the report can be regenerated from the committed summaries.
3. Tag the release as `v1.0.0` and publish the final v1 release notes.

See [`MODEL_REGISTRY.md`](MODEL_REGISTRY.md), [`PHASE8_QUANTIZATION.md`](PHASE8_QUANTIZATION.md), [`PHASE9_SCORING.md`](PHASE9_SCORING.md), and [`RELEASE_V1.md`](RELEASE_V1.md).
