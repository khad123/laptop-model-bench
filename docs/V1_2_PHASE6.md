# Laptop Model Bench v1.2 — Phase 6 Agents & Tool Use

Status: **FROZEN**

Official run: `20260915T220947Z`

| Rank | Model | Score | Solved | Structured | Tool | Args | Outcome |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `qwen35-2b-q4km` | 92.67% | 15/20 | 100.0% | 100.0% | 100.0% | 75.0% |
| 2 | `qwen35-0.8b-q4km` | 35.50% | 1/20 | 52.5% | 25.0% | 20.0% | 5.0% |
| 3 | `minicpm5-2b-q4km` | 31.00% | 5/20 | 22.5% | 15.0% | 15.0% | 25.0% |
| 4 | `smollm3-3b-iq4xs` | 20.50% | 3/20 | 15.0% | 0.0% | 0.0% | 15.0% |

## Legacy vs harder tasks

| Model | Legacy | New hard |
|---|---:|---:|
| `qwen35-2b-q4km` | 100.00% | 85.33% |
| `qwen35-0.8b-q4km` | 38.67% | 32.33% |
| `minicpm5-2b-q4km` | 22.00% | 40.00% |
| `smollm3-3b-iq4xs` | 20.00% | 21.00% |

## Method

- 20 deterministic agent/tool-use tasks.
- 10 legacy tasks plus 10 harder v1.2 tasks.
- 5 tasks each for single-tool, disambiguation, missing-information, and multi-step behavior.
- Local deterministic mock tools only.
- Temperature 0, seed 42, reasoning disabled.
- Maximum four actions per task.

