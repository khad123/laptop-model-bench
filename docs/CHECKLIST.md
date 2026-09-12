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
- [ ] Freeze v1 task set
- [ ] Freeze scoring weights / leaderboard rules

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
- Load timing is a best-effort separate load probe, not a guaranteed cold-cache load measurement.
- Real 12-model Phase 1 run completed successfully; noisy entries were validation-rerun before moving on.

## Phase 2 — Reasoning + knowledge

- [x] Choose compact reasoning task source (original project-authored v0.1 set)
- [x] Add arithmetic / multi-step reasoning set
- [x] Add ARC-style reasoning set
- [x] Add compact MMLU-style knowledge set
- [x] Add deterministic scorer
- [~] Validate answer extraction and model/template compatibility
- [ ] Review task difficulty / balance after pilot model
- [ ] Freeze Phase 2 v1 task set

Phase 2 implementation notes:

- Entry point: `./capability.sh`
- Development task file: `tasks/phase2_v0.1.json`
- 32 objective multiple-choice tasks: 20 reasoning + 12 knowledge.
- Default pool: seven primary model quants only.
- Runtime: local `llama-server` with native chat template via `/v1/chat/completions`.
- Deterministic profile: 4 threads, CPU-only, context 4096, temperature 0, seed 42, prompt cache disabled.
- `phase2_score`: equal-weight mean of reasoning accuracy and knowledge accuracy.
- Raw per-task responses are retained for audit before the task set is frozen.

## Phase 3 — Coding

- [ ] Select small HumanEval+/MBPP+ subset
- [ ] Build safe local execution harness
- [ ] Add pass/fail scorer
- [ ] Save generated code and test output
- [ ] Define timeout/resource limits

## Phase 4 — MiniSWE

- [ ] Define MiniSWE task format
- [ ] Create task 01
- [ ] Create task 02
- [ ] Create task 03
- [ ] Create task 04
- [ ] Create task 05
- [ ] Expand toward 10 tasks if runtime remains practical
- [ ] Build patch/apply/test harness
- [ ] Score solved / partially solved / failed

## Phase 5 — Instruction following

- [ ] Define task schema
- [ ] Create strict formatting tests
- [ ] Create forbidden/required token tests
- [ ] Create ordering tests
- [ ] Create JSON/schema tests
- [ ] Implement deterministic checker

## Phase 6 — Tool / agent benchmark

- [ ] Define local mock tools
- [ ] Create simple single-tool tasks
- [ ] Create similar-tool disambiguation tasks
- [ ] Create missing-argument tasks
- [ ] Create multi-step tasks
- [ ] Score tool choice
- [ ] Score arguments
- [ ] Score structured-output validity

## Phase 7 — Context

- [ ] Create ~1K context tests
- [ ] Create ~2K context tests
- [ ] Create ~4K context tests
- [ ] Measure retrieval accuracy
- [ ] Measure answer quality degradation

## Phase 8 — Quantization

- [ ] K2 Q4_K_M vs Q6_K speed/resource/quality comparison
- [ ] Qwen3.5-2B Q4_K_M vs IQ4_XS speed
- [ ] Qwen3.5-2B Q4_K_M vs IQ4_XS RAM
- [ ] Qwen3.5-2B Q4_K_M vs IQ4_XS quality
- [ ] SmolLM3 Q4_K_M vs IQ4_XS
- [ ] Gemma 3 1B Q4_K_M vs IQ4_XS
- [ ] Llama 3.2 1B Q4_K_M vs IQ4_XS
- [ ] Decide whether additional same-base quant comparisons are useful

## Phase 9 — Results

- [ ] Define JSON result schema
- [ ] Export CSV summary
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

1. Pull the new Phase 2 files on the target laptop.
2. Run `./capability.sh --dry-run` and confirm all seven primary model entries plus all 32 tasks resolve.
3. Smoke-test one task with `./capability.sh --only qwen35-0.8b-q4km --task arith-01`.
4. Run the full 32-task suite on Qwen3.5-0.8B and inspect parse rate/raw outputs.
5. If parsing and task behavior are sound, run the seven-model primary capability pool.
6. Review difficulty/balance, then freeze a Phase 2 v1 task set before treating capability scores as final.

See [`MODEL_REGISTRY.md`](MODEL_REGISTRY.md), [`PHASE1_RUNNER.md`](PHASE1_RUNNER.md), and [`PHASE2_RUNNER.md`](PHASE2_RUNNER.md).
