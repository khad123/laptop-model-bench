# Laptop Model Bench

A compact, reproducible benchmark suite for comparing small local LLMs on an **8 GB CPU-only laptop**.

The project is designed to answer practical questions rather than reproduce giant industry benchmark suites:

- Which model is actually usable on an older laptop?
- Which model is fastest?
- Which model is strongest for coding and repository-level software engineering?
- Which model is best at tool/agent workflows?
- Which model follows instructions reliably?
- Which quantization gives the best quality/resource trade-off?

## v1 result

**Best overall laptop model: `Qwen3.5-2B Q4_K_M`**

It wins the frozen v1 overall recommendation with an **overall laptop score of 79.15**, combining the strongest MiniSWE and agent results with high general capability while remaining practical on the target machine.

The winner is robust: Qwen3.5-2B Q4_K_M remains #1 under every tested sensitivity profile, including equal capability weighting, capability-only weighting, developer-heavy weighting, and a more general-purpose mix.

### Recommended-quant overall leaderboard

| Rank | Model | Overall | Capability | Efficiency | Developer |
|---:|---|---:|---:|---:|---:|
| 1 | **Qwen3.5-2B Q4_K_M** | **79.15** | **85.13** | 45.25 | **87.02** |
| 2 | Qwen3.5-0.8B Q4_K_M | 59.53 | 52.41 | **99.88** | 39.40 |
| 3 | K2-Horizon-0.9B Q4_K_M | 57.05 | 51.85 | 86.46 | 44.63 |
| 4 | SmolLM3-3B IQ4_XS | 56.81 | 61.30 | 31.37 | 57.30 |
| 5 | LFM2.5-1.2B-Instruct Q4_K_M | 52.56 | 47.63 | 80.51 | 35.93 |
| 6 | Gemma 3 1B IT Q4_K_M | 49.05 | 44.51 | 74.75 | 46.33 |
| 7 | Llama 3.2 1B Instruct Q4_K_M | 43.92 | 38.07 | 77.09 | 26.70 |

### Category winners

| Category | Winner | Score |
|---|---|---:|
| Smartest / reasoning + knowledge | SmolLM3-3B IQ4_XS | 82.50 |
| Developer | **Qwen3.5-2B Q4_K_M** | **87.02** |
| MiniSWE | **Qwen3.5-2B Q4_K_M** | **86.29** |
| Tool / agent | **Qwen3.5-2B Q4_K_M** | **100.00** |
| Instruction following | K2-Horizon-0.9B Q6_K | 87.50 |
| Context | SmolLM3-3B IQ4_XS | 100.00 |
| Fastest | Qwen3.5-0.8B Q4_K_M | 100.00 normalized speed score |
| Quality per GiB | Qwen3.5-0.8B Q4_K_M | 97.10 |

See [`docs/PHASE9_SCORING.md`](docs/PHASE9_SCORING.md) for the frozen overall scoring method and sensitivity review, and [`docs/PHASE8_QUANTIZATION.md`](docs/PHASE8_QUANTIZATION.md) for same-base quant decisions.

## Target hardware

The v1 machine profile is intentionally modest:

- CPU: Intel Core i5, 8th generation
- RAM: 8 GB
- GPU: CPU-only benchmark target
- OS: Linux
- Runtime: `llama.cpp`
- Default CPU threads: `4`
- Standard capability context: `4096`
- Dedicated Phase 7 context runtime: `8192`

The benchmark records machine/runtime metadata with results so future machine profiles can be compared without changing the frozen task set.

## What is tested

1. **Speed & efficiency** — prompt processing, generation speed, model size, load time, peak benchmark RSS.
2. **Reasoning + knowledge** — 32 compact deterministic multiple-choice tasks.
3. **Coding** — 12 executable Python function-generation tasks with hidden tests.
4. **MiniSWE** — 5 tiny repository-level bug-fixing tasks with hidden tests and partial scoring.
5. **Instruction following** — 16 strict, automatically checked constraint tasks.
6. **Tool / agent ability** — 10 deterministic local-tool tasks including disambiguation and multi-step sequences.
7. **Context handling** — paired direct, composition, and relational tasks at approximately 1K, 2K, and 4K prompt lengths.
8. **Quantization trade-offs** — five same-base quant pairs compared across speed, RAM, size, and capability.

## Final v1 scoring

The overall laptop score is transparent and secondary to the standalone category leaderboards.

### Capability — 85%

- Reasoning + knowledge: 12%
- Isolated coding: 15%
- MiniSWE: 20%
- Instruction following: 10%
- Tool / agent: 20%
- Context: 8%

### Laptop efficiency — 15%

- Prompt-processing speed: 4%
- Generation speed: 5%
- Peak benchmark RSS: 4%
- Model size: 2%

Full details are in [`docs/PHASE9_SCORING.md`](docs/PHASE9_SCORING.md).

## Recommended quant per base model

| Base model | v1 recommendation |
|---|---|
| K2-Horizon-0.9B | **Q4_K_M** |
| Qwen3.5-2B | **Q4_K_M** |
| SmolLM3-3B | **IQ4_XS** |
| Gemma 3 1B IT | **Q4_K_M** |
| Llama 3.2 1B Instruct | **Q4_K_M** |

The full reasoning is documented in [`docs/PHASE8_QUANTIZATION.md`](docs/PHASE8_QUANTIZATION.md).

## Reproducing the report

The benchmark phases save timestamped JSON/CSV summaries and raw audit artifacts. Phase 9 intentionally reads **explicit frozen run IDs**, not `*-latest.json`, because latest aliases can point to pilots or validation subsets.

Generate the consolidated final report:

```bash
python3 scripts/build_phase9_report.py
```

This writes:

```text
results/phase9-consolidated.json
results/phase9-consolidated.csv
results/phase9-report.md
```

Generate dependency-free SVG charts:

```bash
python3 scripts/generate_phase10_charts.py
```

This writes charts under:

```text
results/charts/
```

## Benchmark entry points

```text
./bench.sh          Phase 1 — speed/resources
./capability.sh     Phase 2 — reasoning/knowledge
./coding.sh         Phase 3 — executable coding
./miniswe.sh        Phase 4 — MiniSWE
./instruction.sh    Phase 5 — instruction following
./agent.sh          Phase 6 — tool/agent benchmark
./context.sh        Phase 7 — context handling
```

Each phase has a dedicated runner document under `docs/`.

## Fair-test rules

Unless a phase explicitly requires something different:

- same laptop
- same runtime
- 4 CPU threads
- deterministic decoding / temperature 0 where supported
- fixed seed where supported
- identical prompts across models
- same output limit within a phase
- native chat template
- no internet during evaluation
- raw outputs saved before scoring
- no model-specific prompt fixes after seeing results

See [`docs/BENCHMARK_PROTOCOL.md`](docs/BENCHMARK_PROTOCOL.md) for the full protocol.

## Adding models or tasks

- [Adding a model](docs/ADDING_MODELS.md)
- [Adding benchmark tasks](docs/ADDING_TASKS.md)
- [Model registry](docs/MODEL_REGISTRY.md)

The v1 benchmark is frozen. New models or task-set changes should normally be published as a new benchmark/report version instead of rewriting historical v1 results.

## Project documents

- [Project plan](docs/PLAN.md)
- [Checklist](docs/CHECKLIST.md)
- [Benchmark protocol](docs/BENCHMARK_PROTOCOL.md)
- [Phase 8 quantization analysis](docs/PHASE8_QUANTIZATION.md)
- [Phase 9 final scoring](docs/PHASE9_SCORING.md)

## Philosophy

A local model should not be judged only by benchmark accuracy or only by tokens per second. On an 8 GB laptop, responsiveness, memory use, software-engineering reliability, structured behavior, and model size all matter.

Laptop Model Bench therefore keeps **capability**, **developer usefulness**, **speed**, and **resource efficiency** visible as separate measurements, then combines them only through documented practical leaderboards.
