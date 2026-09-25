# Laptop Model Bench v1.2 — Phase 5 Instruction Following

Status: **FROZEN**

Official run: `20260915T030326Z`

| Rank | Model | Score | Solved | Legacy | New hard |
|---:|---|---:|---:|---:|---:|
| 1 | `minicpm5-2b-q4km` | 91.07% | 20/24 | 89.58% | 94.05% |
| 2 | `qwen35-2b-q4km` | 86.81% | 20/24 | 83.33% | 93.75% |
| 3 | `qwen35-0.8b-q4km` | 79.31% | 18/24 | 72.08% | 93.75% |
| 4 | `smollm3-3b-iq4xs` | 46.24% | 6/24 | 44.06% | 50.59% |

## Category results

| Model | Strict format | Required / forbidden | Ordering | JSON schema |
|---|---:|---:|---:|---:|
| `minicpm5-2b-q4km` | 100.00% | 80.95% | 83.33% | 100.00% |
| `qwen35-2b-q4km` | 100.00% | 80.55% | 66.67% | 100.00% |
| `qwen35-0.8b-q4km` | 83.33% | 80.55% | 66.67% | 86.67% |
| `smollm3-3b-iq4xs` | 0.00% | 57.74% | 27.22% | 100.00% |

## Method

- 24 deterministic instruction-following tasks.
- 16 legacy baseline tasks plus 8 harder multi-constraint tasks.
- 6 tasks each for strict formatting, required/forbidden content, ordering, and JSON/schema.
- Temperature 0, seed 42.
- Reasoning disabled.
- Partial credit based on deterministic checks.

