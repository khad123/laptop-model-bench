# Laptop Model Bench v1.2 — Phase 8 Real-World Workloads

Status: **FROZEN**

Official run: `20260916T113847Z`

Note: the underlying reusable instruction runner writes `phase5-*` raw filenames. The benchmark version is `phase8-v1.2`.

| Rank | Model | Score | Solved | Troubleshooting | Code review | Data work | Workflow |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `minicpm5-2b-q4km` | 71.67% | 8/12 | 66.7% | 33.3% | 86.7% | 100.0% |
| 2 | `qwen35-2b-q4km` | 62.50% | 7/12 | 50.0% | 0.0% | 100.0% | 100.0% |
| 3 | `qwen35-0.8b-q4km` | 28.61% | 2/12 | 16.7% | 0.0% | 20.0% | 77.8% |
| 4 | `smollm3-3b-iq4xs` | 12.50% | 1/12 | 16.7% | 0.0% | 33.3% | 0.0% |

## Method

- 12 deterministic practical laptop workloads.
- 3 troubleshooting tasks.
- 3 code-review tasks.
- 3 data-work tasks.
- 3 everyday developer workflow tasks.
- Temperature 0, seed 42, reasoning disabled.
- CPU-only llama.cpp runtime.

