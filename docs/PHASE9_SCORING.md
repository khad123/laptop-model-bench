# Phase 9 — Reporting and final scoring

Phase 9 consolidates the frozen Phase 1–8 data into transparent category leaderboards and a practical laptop recommendation.

The project explicitly does **not** hide the benchmark behind one unexplained composite. Category leaderboards remain first-class outputs; the overall score is an additional decision aid.

## Frozen inputs

The reporting pipeline must use these exact timestamped sources rather than `*-latest` aliases:

- Phase 1: `results/phase1-20260912T125525Z.json`
- Phase 2: `results/phase2-20260912T163441Z.json`
- Phase 3: `results/phase3-20260912T172204Z.json`
- Phase 4: `results/phase4-20260912T185826Z.json`
- Phase 5: `results/phase5-20260912T233610Z.json`
- Phase 6: `results/phase6-20260913T001137Z.json`
- Phase 7 full v0.2: `results/phase7-20260913T135829Z.json`
- Phase 7 4K validation/correction: `results/phase7-20260913T171609Z.json`

For Phase 7 only, the three SmolLM3-3B IQ4_XS 4K timeout rows in the full run are replaced by the corresponding fresh 4K validation rows. No other Phase 7 rows are replaced.

## Proposed overall laptop score

This weighting is **provisional until the generated ranking is reviewed**.

### Capability — 85%

| Category | Weight | Rationale |
|---|---:|---|
| Reasoning + knowledge (Phase 2) | 12% | General problem solving and factual competence |
| Isolated coding (Phase 3) | 15% | Ability to generate correct executable code |
| MiniSWE (Phase 4) | 20% | Most realistic repository-level software-engineering signal |
| Instruction following (Phase 5) | 10% | Reliability under exact constraints and structured output |
| Tool / agent use (Phase 6) | 20% | Important for practical automated workflows and coding agents |
| Context handling (Phase 7) | 8% | Retrieval/use at 1K–4K context lengths |

Capability subtotal is reported separately on a 0–100 scale:

```text
capability_score = weighted capability sum / 85
```

### Laptop efficiency — 15%

| Metric | Weight | Direction |
|---|---:|---|
| Prompt-processing speed | 4% | higher is better |
| Generation speed | 5% | higher is better |
| Peak benchmark RSS | 4% | lower is better |
| Model size on disk | 2% | lower is better |

Efficiency metrics use transparent ratio-to-best normalization across the 12 model+quant entries:

```text
higher-is-better score = 100 * value / best_value
lower-is-better score  = 100 * best_value / value
```

This avoids opaque z-scores or dataset-dependent min/max stretching. The resulting efficiency subtotal is also reported on a 0–100 scale.

### Composite

```text
overall_laptop_score = 0.85 * capability_score + 0.15 * efficiency_score
```

The score should be interpreted together with the category tables, not alone.

## Additional leaderboards

Phase 9 generates:

- **Smartest** — Phase 2 score
- **Isolated coding** — Phase 3 score
- **MiniSWE** — Phase 4 score
- **Instruction follower** — Phase 5 score
- **Tool / agent** — Phase 6 score
- **Context** — corrected Phase 7 score
- **Developer score** — 30% Phase 3 + 40% Phase 4 + 30% Phase 6
- **Fastest** — 40% normalized prompt speed + 60% normalized generation speed
- **Quality per GB** — capability score divided by model size in GiB
- **Overall laptop score** — proposed composite above

## Two ranking views

The report contains both:

1. **All 12 model+quant entries** — preserves every benchmarked quant and makes quant effects visible.
2. **Recommended-quant base-model view** — one practical quant per base model, using the Phase 8 decisions:
   - K2-Horizon-0.9B Q4_K_M
   - Qwen3.5-0.8B Q4_K_M
   - Qwen3.5-2B Q4_K_M
   - LFM2.5-1.2B-Instruct Q4_K_M
   - SmolLM3-3B IQ4_XS
   - Gemma 3 1B IT Q4_K_M
   - Llama 3.2 1B Instruct Q4_K_M

The original frozen primary-capability pool is not rewritten after seeing results. The recommended-quant view is a reporting/recommendation layer, not a retroactive methodology change.

## Generated artifacts

`scripts/build_phase9_report.py` writes:

```text
results/phase9-consolidated.json
results/phase9-consolidated.csv
results/phase9-report.md
```

The report also prints compact leaderboard summaries to the terminal for review before the final weighting is frozen.
