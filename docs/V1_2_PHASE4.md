# Laptop Model Bench v1.2 — Phase 4 MiniSWE

Status: **FROZEN**

| Rank | Model | MiniSWE | Solved | Partial |
|---:|---|---:|---:|---:|
| 1 | `minicpm5-2b-q4km` | 67.50% | 7/15 | 5 |
| 2 | `qwen35-2b-q4km` | 64.25% | 4/15 | 9 |
| 3 | `smollm3-3b-iq4xs` | 52.99% | 3/15 | 8 |
| 4 | `qwen35-0.8b-q4km` | 34.69% | 0/15 | 10 |

## Correction

- `swe-14` expected ordering corrected from `[2,1,3]` to `[2,3,1]`.
- All four models were rerun on the corrected task.
- All four still failed because the generated repair used `normalize_text` without importing it.
- Final scores therefore did not change.

