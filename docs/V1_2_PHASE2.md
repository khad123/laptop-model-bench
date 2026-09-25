# Laptop Model Bench v1.2 — Phase 2

Status: **FROZEN**

Official run: `20260914T141244Z`

## Method

- 4 finalist models
- 36 project-authored tasks
- 6 balanced domains
- 12 easy / 12 medium / 12 hard tasks
- 256-token reasoning budget
- 512-token total completion ceiling
- deterministic temperature/seed
- unparsed or unfinished answers score incorrect

## Results

| Rank | Model | Correct | Score | Parse rate |
|---:|---|---:|---:|---:|
| 1 | `minicpm5-2b-q4km` | 34/36 | 94.44% | 100.00% |
| 2 | `qwen35-2b-q4km` | 31/36 | 86.11% | 100.00% |
| 3 | `smollm3-3b-iq4xs` | 24/36 | 66.67% | 100.00% |
| 4 | `qwen35-0.8b-q4km` | 17/36 | 47.22% | 91.67% |

## Findings

- MiniCPM5-2B Q4_K_M leads Phase 2 at 94.44%.
- Qwen3.5-2B Q4_K_M follows at 86.11%.
- SmolLM3-3B IQ4_XS scores 66.67%.
- Qwen3.5-0.8B Q4_K_M scores 47.22% and produced three unparsed/unfinished answers.
- These are Phase 2 capability results only; they do not determine the final v1.2 overall ranking.
