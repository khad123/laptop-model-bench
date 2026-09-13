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
- [~] Freeze v1 task set category by category
- [ ] Freeze final scoring weights / leaderboard rules

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

- [~] Create ~1K context tests
- [ ] Create ~2K context tests
- [ ] Create ~4K context tests
- [ ] Measure retrieval accuracy
- [ ] Measure answer quality degradation

## Phase 8 — Quantization

- [ ] K2 Q4_K_M vs Q6_K combined comparison
- [ ] Qwen3.5-2B Q4_K_M vs IQ4_XS combined comparison
- [ ] SmolLM3 Q4_K_M vs IQ4_XS combined comparison
- [ ] Gemma 3 1B Q4_K_M vs IQ4_XS combined comparison
- [ ] Llama 3.2 1B Q4_K_M vs IQ4_XS combined comparison
- [ ] Decide whether additional same-base quant comparisons are useful

## Phase 9 — Results

- [ ] Define final JSON result schema
- [ ] Export consolidated CSV summary
- [ ] Generate per-model report
- [ ] Generate category leaderboards
- [ ] Generate overall laptop recommendation
- [ ] Generate quality-per-GB ranking
- [ ] Generate quantization trade-off ranking

## Phase 10 — Polish

- [x] Single-command speed runner
- [x] System metadata capture
- [ ] Documentation for adding models
- [ ] Documentation for adding tasks
- [ ] Charts / plots
- [ ] Release v1.0

## Current immediate next steps

1. Build Phase 7 context-retrieval tasks at approximately 1K, 2K, and 4K prompt lengths.
2. Use deterministic hidden facts and lightweight reasoning so the benchmark measures retrieval/use rather than keyword copying alone.
3. Pilot the context runner on Qwen3.5-2B Q4_K_M, then run all 12 entries if clean.

See [`MODEL_REGISTRY.md`](MODEL_REGISTRY.md), [`PHASE1_RUNNER.md`](PHASE1_RUNNER.md), [`PHASE2_RUNNER.md`](PHASE2_RUNNER.md), [`PHASE4_RUNNER.md`](PHASE4_RUNNER.md), [`PHASE5_RUNNER.md`](PHASE5_RUNNER.md), and [`PHASE6_RUNNER.md`](PHASE6_RUNNER.md).
