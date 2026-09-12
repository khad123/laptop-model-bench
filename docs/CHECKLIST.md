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
- [ ] Freeze v1 model list
- [ ] Freeze quantization for every model
- [ ] Freeze v1 task set
- [ ] Freeze scoring weights / leaderboard rules

## Phase 1 — Inventory + speed

- [ ] Create model registry
- [ ] Add K2-Horizon-0.9B Q4_K_M
- [ ] Add Qwen3.5-0.8B Q4_K_M
- [ ] Add Qwen3.5-2B Q4_K_M
- [ ] Add Qwen3.5-2B IQ4_XS
- [ ] Add LFM2.5-1.2B-Instruct Q4_K_M
- [ ] Add SmolLM3-3B
- [ ] Add Gemma 3 1B
- [ ] Add Llama 3.2 1B Instruct
- [ ] Build automated llama-bench runner
- [ ] Save raw benchmark output
- [ ] Measure prompt processing speed
- [ ] Measure generation speed
- [ ] Measure load time
- [ ] Measure on-disk size
- [ ] Investigate reliable peak-RAM measurement
- [ ] Re-run K2 baseline under final protocol

Known pre-project K2 result (not yet official):

- Prompt processing: ~96.96 tok/s
- Generation: ~22.93 tok/s
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

- [ ] Qwen3.5-2B Q4_K_M vs IQ4_XS speed
- [ ] Qwen3.5-2B Q4_K_M vs IQ4_XS RAM
- [ ] Qwen3.5-2B Q4_K_M vs IQ4_XS quality
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

- [ ] Single-command runner
- [ ] System metadata capture
- [ ] Documentation for adding models
- [ ] Documentation for adding tasks
- [ ] Charts / plots
- [ ] Release v1.0

## Current immediate next steps

1. Finish downloading the initial model pool.
2. Record exact quant/file/repository for each model.
3. Build Phase 1 model registry and automated speed harness.
4. Run every model through the identical speed test.
5. Only then begin capability benchmarks.
