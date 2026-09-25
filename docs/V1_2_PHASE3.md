# Laptop Model Bench v1.2 — Phase 3 Coding

Status: **FROZEN**

Official run: `20260915T000052Z`

## Results

| Rank | Model | Passed | Coding score | Easy | Medium | Hard |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `minicpm5-2b-q4km` | 19/20 | 95.00% | 100.00% | 100.00% | 83.33% |
| 2 | `smollm3-3b-iq4xs` | 17/20 | 85.00% | 83.33% | 75.00% | 100.00% |
| 3 | `qwen35-2b-q4km` | 15/20 | 75.00% | 100.00% | 50.00% | 83.33% |
| 4 | `qwen35-0.8b-q4km` | 7/20 | 35.00% | 50.00% | 25.00% | 33.33% |

## Method

- 20 project-authored executable Python tasks.
- 6 easy, 8 medium, 6 hard.
- Hidden deterministic tests.
- Code parsed and safety-checked before execution.
- Bubblewrap sandbox with networking disabled.
- A task scores as passed only when every hidden test passes.
- Direct coding mode with reasoning disabled.

## Result

- MiniCPM5-2B Q4_K_M: 95.00%.
- SmolLM3-3B IQ4_XS: 85.00%.
- Qwen3.5-2B Q4_K_M: 75.00%.
- Qwen3.5-0.8B Q4_K_M: 35.00%.

