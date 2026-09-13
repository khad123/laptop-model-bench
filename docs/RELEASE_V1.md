# v1.0 release checklist

This checklist packages the frozen benchmark without committing large raw model artifacts.

## 1. Regenerate final reports

From the repository root:

```bash
python3 scripts/build_phase9_report.py
python3 scripts/generate_phase10_charts.py
```

The report builder must print `Phase 9 final v1 consolidation complete.` and identify `qwen35-2b-q4km` as the robust winner across sensitivity profiles.

## 2. Commit the frozen source summaries

Phase 9 intentionally reads exact timestamped JSON files. Commit these files so a fresh clone can rebuild the final report:

```text
results/phase1-20260912T125525Z.json
results/phase2-20260912T163441Z.json
results/phase3-20260912T172204Z.json
results/phase4-20260912T185826Z.json
results/phase5-20260912T233610Z.json
results/phase6-20260913T001137Z.json
results/phase7-20260913T135829Z.json
results/phase7-20260913T171609Z.json
```

The second Phase 7 file is the all-model 4K validation used only to replace the three invalid SmolLM3 IQ4_XS timeout rows.

Do not commit `results/raw/`; it is intentionally ignored because raw per-task artifacts can be large.

## 3. Commit final generated artifacts

Commit:

```text
results/phase9-consolidated.json
results/phase9-consolidated.csv
results/phase9-report.md
results/charts/
```

These are the human- and machine-readable v1 outputs.

## 4. Verify repository state

Run:

```bash
git status --short
python3 scripts/build_phase9_report.py
python3 scripts/generate_phase10_charts.py
```

After regeneration, `git diff --exit-code` should succeed if the generated artifacts are deterministic and already committed.

## 5. Review the public-facing files

Check:

- `README.md`
- `docs/BENCHMARK_PROTOCOL.md`
- `docs/PHASE8_QUANTIZATION.md`
- `docs/PHASE9_SCORING.md`
- `docs/ADDING_MODELS.md`
- `docs/ADDING_TASKS.md`
- `results/phase9-report.md`

Confirm the README and final report agree on the overall winner and category leaders.

## 6. Tag v1.0.0

Once the repository is clean and the final generated files are committed:

```bash
git tag -a v1.0.0 -m "Laptop Model Bench v1.0.0"
git push origin v1.0.0
```

The tag should point to the commit containing the frozen source summaries, final report, charts, and release documentation.

## 7. Suggested release notes

### Laptop Model Bench v1.0.0

First frozen release of the 8 GB CPU-only laptop benchmark.

Highlights:

- 12 model+quant entries benchmarked
- speed/resource, reasoning/knowledge, coding, MiniSWE, instruction-following, tool/agent, and context phases
- five same-base quantization comparisons
- transparent frozen overall scoring plus standalone category leaderboards
- sensitivity analysis for the overall recommendation
- **Best overall: Qwen3.5-2B Q4_K_M**
- **Fastest / best quality per GiB: Qwen3.5-0.8B Q4_K_M**
- **Smartest and best context: SmolLM3-3B IQ4_XS**
- **Best instruction follower: K2-Horizon-0.9B Q6_K**

See `results/phase9-report.md` for the complete results.

## After v1

Do not rewrite v1 task files or historical scores. New models, broader quant sweeps, additional task families, or a second hardware profile should be released as a later benchmark version (for example v1.1 or v2).
