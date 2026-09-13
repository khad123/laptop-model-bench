# Phase 8 — Quantization analysis

Phase 8 compares the five same-base quantization pairs already present in the frozen v1 model registry. No new model inference is required: this analysis uses the frozen Phase 1–7 results.

## Frozen result sources

Use explicit timestamped runs rather than `*-latest.json` aliases because some latest aliases point to validation subsets rather than the complete frozen run.

- Phase 1 speed/resource full run: `results/phase1-20260912T125525Z.json`
- Phase 2 reasoning/knowledge: `results/phase2-20260912T163441Z.json`
- Phase 3 coding: `results/phase3-20260912T172204Z.json`
- Phase 4 MiniSWE: `results/phase4-20260912T185826Z.json`
- Phase 5 instruction following: `results/phase5-20260912T233610Z.json`
- Phase 6 tool/agent: `results/phase6-20260913T001137Z.json`
- Phase 7 context v0.2 full run: `results/phase7-20260913T135829Z.json`
- Phase 7 infrastructure correction: `results/phase7-20260913T171609Z.json`

For Phase 7, only the three invalid SmolLM3 IQ4_XS 4K timeout rows from the full run are replaced by the fresh all-model 4K validation. Every other model reproduced its earlier 4K pass/fail pattern exactly.

## Interpretation rule

The `capability mean` below is a diagnostic equal-weight arithmetic mean of Phase 2, 3, 4, 5, 6, and corrected Phase 7 percentage scores. It is useful for same-base quant comparisons, but it is **not** the final v1 overall leaderboard score. Final category weights are frozen later in Phase 9.

## Summary

| Base model | Quant | Size | PP tok/s | TG tok/s | Peak RAM | P2 | P3 | P4 | P5 | P6 | P7 | Capability mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| K2-Horizon-0.9B | Q4_K_M | 636M | 94.83 | 21.69 | 1.11 GiB | 65.00 | 83.33 | 8.57 | 77.08 | 54.00 | 44.44 | 55.40 |
| K2-Horizon-0.9B | Q6_K | 847M | 51.21 | 14.25 | 0.93 GiB | 61.66 | 75.00 | 31.07 | 87.50 | 50.00 | 55.56 | 60.13 |
| Qwen3.5-2B | Q4_K_M | 1.4G | 51.03 | 10.55 | 1.88 GiB | 77.50 | 75.00 | 86.29 | 83.33 | 100.00 | 77.78 | 83.32 |
| Qwen3.5-2B | IQ4_XS | 1.2G | 26.80 | 8.61 | 1.27 GiB | 75.00 | 75.00 | 83.43 | 83.33 | 94.00 | 77.78 | 81.42 |
| SmolLM3-3B | IQ4_XS | 1.7G | 13.44 | 7.56 | 1.78 GiB | 82.50 | 66.67 | 76.00 | 44.06 | 23.00 | 100.00 | 65.37 |
| SmolLM3-3B | Q4_K_M | 1.8G | 25.04 | 6.99 | 3.16 GiB | 75.84 | 83.33 | 78.00 | 44.06 | 8.00 | 88.89 | 63.02 |
| Gemma 3 1B IT | IQ4_XS | 682M | 72.10 | 14.05 | 1.02 GiB | 55.84 | 75.00 | 0.00 | 39.79 | 14.67 | 55.56 | 40.14 |
| Gemma 3 1B IT | Q4_K_M | 769M | 59.21 | 18.35 | 0.94 GiB | 37.50 | 66.67 | 56.57 | 42.19 | 12.33 | 66.67 | 46.99 |
| Llama 3.2 1B Instruct | IQ4_XS | 709M | 38.16 | 14.28 | 0.83 GiB | 65.00 | 58.33 | 0.00 | 57.29 | 13.67 | 77.78 | 45.34 |
| Llama 3.2 1B Instruct | Q4_K_M | 771M | 90.67 | 19.15 | 1.28 GiB | 61.66 | 75.00 | 0.00 | 55.73 | 14.00 | 66.67 | 45.51 |

## Pair decisions

### K2-Horizon-0.9B — prefer Q4_K_M for the laptop default

Q6_K gains +4.73 points in the diagnostic capability mean, driven mainly by MiniSWE (+22.50), instruction following (+10.42), and context (+11.12). However, it is about 33% larger on disk while prompt processing is about 46% slower and token generation about 34% slower. It also loses isolated coding, reasoning/knowledge, and agent score.

The measured Phase 1 peak-RAM result is lower for Q6_K than Q4_K (0.93 vs 1.11 GiB), which is counterintuitive given the larger quant and should not be interpreted as a general memory advantage without a dedicated memory rerun. For the actual 8 GB CPU-only laptop, Q4_K_M is the better practical default; Q6_K is an optional quality experiment when instruction/MiniSWE behavior matters more than latency.

### Qwen3.5-2B — prefer Q4_K_M

Q4_K_M is the clearest same-base winner in the project. It equals or beats IQ4_XS in every frozen capability phase: +2.50 P2, equal P3, +2.86 P4, equal P5, +6.00 P6, and equal P7. Its diagnostic capability mean is +1.90 points.

The speed difference is much larger than the quality difference: Q4_K_M prompt processing is about 90% faster and generation about 23% faster. IQ4_XS saves roughly 200 MB on disk and about 0.61 GiB in the measured Phase 1 peak RAM. Because Q4 still fits the target laptop and is the strongest realistic SWE/agent quant, Q4_K_M is the recommended Qwen3.5-2B quant.

### SmolLM3-3B — prefer IQ4_XS overall; Q4_K_M only for isolated coding/PP throughput

IQ4_XS has the higher diagnostic capability mean (+2.35), is slightly smaller, and used far less measured peak RAM (1.78 vs 3.16 GiB). It also wins reasoning/knowledge (+6.66), agents (+15.00), and corrected context (+11.11). Generation speed is slightly higher as well.

Q4_K_M is much faster at prompt processing (+86% relative to IQ4_XS) and performs substantially better on isolated coding (+16.66), with a small MiniSWE edge (+2.00). For an 8 GB laptop where memory headroom and broad capability matter, IQ4_XS is the better default. Q4_K_M is the specialization choice when prompt ingestion and isolated coding are prioritized and the extra RAM is acceptable.

### Gemma 3 1B IT — prefer Q4_K_M

Q4_K_M has the higher diagnostic capability mean by +6.85 points. The largest reason is MiniSWE: 56.57% versus 0% for IQ4_XS. Q4 also wins instruction following, context, and generation speed (+31%). IQ4_XS is better in reasoning/knowledge, isolated coding, prompt-processing speed, and disk size.

Because the Q4 variant turns Gemma from a zero-score MiniSWE model into a partially useful repo-level coding model while remaining small, Q4_K_M is the better practical quant for this laptop.

### Llama 3.2 1B Instruct — prefer Q4_K_M unless RAM is the limiting constraint

The two quants are effectively tied in the diagnostic capability mean (45.51 Q4 vs 45.34 IQ4). Q4 wins isolated coding by +16.67 and is dramatically faster in this Phase 1 run: prompt processing is about 138% faster and generation about 34% faster. IQ4_XS wins reasoning/knowledge, instruction following, context, disk size, and measured peak RAM.

Both score 0% on MiniSWE and both are weak agents, so the speed difference is more useful than a negligible mean-quality difference. Q4_K_M is the better default when 1.28 GiB measured peak RAM is acceptable; IQ4_XS remains useful when memory headroom is the priority.

## Recommended quant per base model

| Base model | Recommended v1 quant | Why |
|---|---|---|
| K2-Horizon-0.9B | **Q4_K_M** | Much faster and smaller; Q6 quality gains are too task-specific to justify the latency for the default |
| Qwen3.5-2B | **Q4_K_M** | Better/equal capability everywhere and substantially faster; strongest agent/SWE choice |
| SmolLM3-3B | **IQ4_XS** | Better broad capability and much lower measured RAM; corrected 100% context score |
| Gemma 3 1B IT | **Q4_K_M** | Strong MiniSWE recovery and faster generation with better overall capability mean |
| Llama 3.2 1B Instruct | **Q4_K_M** | Similar quality but much faster; choose IQ4 only when RAM headroom matters more |

## Do we need more same-base quant runs?

No for v1. The five existing pairs cover the main trade-off patterns we needed to observe: larger quant with task-specific quality gains, smaller quant with memory savings, Q4 dominance, IQ4 dominance, and near-tie behavior. Adding more Q5/Q6/IQ variants now would increase benchmark cost without changing the v1 model-selection conclusions. Additional quant sweeps can be a v1.1 extension after the final scoring/reporting pipeline is frozen.

## Phase 8 conclusion

Phase 8 is an analysis phase, not another inference phase. The frozen data already supports practical per-model quant recommendations for this 8 GB CPU-only laptop. Phase 9 should now define the final leaderboard weighting, consolidate the timestamped frozen runs into one schema, and produce per-model/category/efficiency reports.
