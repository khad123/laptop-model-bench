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
- [ ] Save raw benchmark output from the real laptop run
- [ ] Measure prompt processing speed
- [ ] Measure generation speed
- [ ] Measure load time
- [ ] Measure on-disk size in the real run summary
- [x] Investigate reliable peak-RAM measurement
- [ ] Record peak RAM from the real laptop run
- [ ] Re-run K2 baseline under final protocol

Runner implementation notes:

- Entry point: `./bench.sh`
- Local HF cache only; missing models fail without redownloading.
- Peak RSS: exact child `wait4().ru_maxrss` on Linux.
- Raw per-model output: `results/raw/<run-id>/`.
- Summary: timestamped CSV/JSON plus `results/phase1-latest.*`.
- Load timing is a best-effort separate load probe, not a guaranteed cold-cache load measurement.

Known pre-project K2 results (not yet official):

### K2-Horizon-0.9B Q4_K_M

- Prompt processing: ~96.96 tok/s
- Generation: ~22.93 tok/s
- Threads: 4

### K2-Horizon-0.9B Q6_K

- Prompt processing: ~60.42 tok/s
- Generation: ~18.45 tok/s
- Threads: 4

## Phase 2 — Reasoning + knowledge

- [ ] Choose compact reasoning task source
- [ ] Add arithmetic / multi-step reasoning set
- [ ] Add ARC-style reasoning set
- [ ] Add compact MMLU-style set
- [ ] Add deterministic scorer
- [ ] Validate answer extraction

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

- [x] Single-command runner
- [x] System metadata capture
- [ ] Documentation for adding models
- [ ] Documentation for adding tasks
- [ ] Charts / plots
- [ ] Release v1.0

## Current immediate next steps

1. Run `./bench.sh --dry-run` on the target laptop and confirm all frozen registry entries resolve locally.
2. Run `./bench.sh` and inspect the generated Phase 1 CSV/JSON plus raw evidence.
3. Re-run/sanity-check K2 Q4_K_M and Q6_K under the automated protocol.
4. Mark the real Phase 1 measurement tasks complete only after the output is stable.
5. Freeze the v1 capability task set and scoring rules before capability testing begins.
6. Only then begin reasoning, knowledge, coding, MiniSWE, instruction, tool, and context evaluation.

See [`MODEL_REGISTRY.md`](MODEL_REGISTRY.md) for the frozen v1 model pool and [`PHASE1_RUNNER.md`](PHASE1_RUNNER.md) for runner usage.
