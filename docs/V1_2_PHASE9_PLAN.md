# Laptop Model Bench v1.2 — Phase 9

Status: **METHODOLOGY FROZEN**

Phase 9 is the final validation, runtime-optimization, and reporting phase.

## 9A — Reliability

Repeat only results where repeatability materially affects the conclusion.

Primary validation targets:

- Qwen3.5-2B Q4_K_M
- MiniCPM5-2B Q4_K_M
- SmolLM3-3B IQ4_XS where useful

The goal is not to rerun every previous benchmark.

Reliability testing focuses on:
- MiniSWE variability
- close model results
- reproducibility under deterministic settings

## 9B — llama.cpp laptop optimization

Test practical CPU-only runtime tuning at realistic context lengths.

Optimization candidates:

- generation threads (`-t`)
- prompt/batch threads (`-tb`) if supported
- batch size (`-b`)
- micro-batch size (`-ub`)
- single server slot / parallelism (`-np 1`) if supported
- KV cache formats
- prompt-processing speed
- generation speed
- TTFT
- wall time
- RSS / RAM
- swap
- model startup time

MTP/speculative decoding is tested only when:
1. the llama.cpp build supports it,
2. the model itself supports the required architecture/heads,
3. it is meaningful on CPU-only hardware.

MTP is not assumed to improve prompt prefill.

## Practical cutoff

Any single optimization trial taking more than 10 minutes without producing
a result is aborted.

After a configuration exceeds the cutoff, its remaining repetitions are
skipped.

## Context policy

Official practical context coverage for the current v1.2 run:

- 8K: scored
- 16K: extended practical coverage
- 32K: deferred
- 64K: deferred

32K and 64K are not failures and can be tested later.

For the common overall context score, use the 8K bucket because it is the
largest context bucket completed by all four finalists.

16K results are reported separately as extended-context qualification.

SmolLM3 is DISQUALIFIED from 16K, not scored as an incorrect answer.

## Final score

Capability categories use these frozen relative weights:

- Reasoning: 15
- Coding: 15
- MiniSWE: 25
- Instruction following: 10
- Agents/tools: 20
- Context: 10
- Real-world workloads: 15

The above sum to 110 and are normalized to a 0-100 capability score.

Final laptop score:

- Capability: 80%
- Baseline efficiency: 15%
- Reliability: 5%

Runtime optimization results do not retroactively replace Phase 1 baseline
efficiency numbers. They are reported as deployment recommendations.

This prevents post-result runtime tuning from changing the original
apples-to-apples benchmark.
