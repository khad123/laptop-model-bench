# v1.2 Phase 1 — Laptop Performance

Official run: `20260914T122353Z`

36 measurements: 4 models × 3 prompt profiles × 3 repeats.
All 36 completed successfully.

## Median performance

| Model | Profile | TTFT s | Wall s | PP tok/s | TG tok/s | RSS GiB | PP CV% |
|---|---|---:|---:|---:|---:|---:|---:|
| `qwen35-0.8b-q4km` | short | 1.54 | 10.72 | 112.73 | 13.83 | 0.99 | 24.74 |
| `qwen35-0.8b-q4km` | medium | 11.85 | 18.55 | 102.95 | 18.51 | 1.02 | 3.65 |
| `qwen35-0.8b-q4km` | long | 51.29 | 61.66 | 93.68 | 12.25 | 1.03 | 13.78 |
| `qwen35-2b-q4km` | short | 4.62 | 19.69 | 37.45 | 8.41 | 2.03 | 3.32 |
| `qwen35-2b-q4km` | medium | 29.47 | 45.46 | 41.38 | 8.78 | 2.07 | 15.07 |
| `qwen35-2b-q4km` | long | 127.36 | 151.23 | 37.72 | 8.09 | 1.97 | 15.72 |
| `minicpm5-2b-q4km` | short | 3.63 | 18.10 | 47.38 | 9.72 | 2.60 | 23.58 |
| `minicpm5-2b-q4km` | medium | 40.20 | 61.92 | 30.33 | 5.85 | 2.61 | 10.28 |
| `minicpm5-2b-q4km` | long | 156.55 | 180.63 | 30.68 | 5.27 | 2.54 | 0.49 |
| `smollm3-3b-iq4xs` | short | 11.25 | 26.32 | 15.29 | 8.42 | 2.27 | 3.36 |
| `smollm3-3b-iq4xs` | medium | 81.77 | 99.69 | 14.90 | 7.10 | 2.33 | 0.12 |
| `smollm3-3b-iq4xs` | long | 353.16 | 392.08 | 13.60 | 3.26 | 2.33 | 0.25 |

## Findings

- Qwen3.5-0.8B is the clear speed/latency leader.
- MiniCPM5-2B is competitive with Qwen3.5-2B on short prompts, but Qwen3.5-2B is faster on medium and long prompts.
- SmolLM3-3B is highly repeatable but substantially slower, especially on long prompts.
- System-wide RAM and swap deltas are retained as diagnostics; process RSS is the cleaner model-comparison metric.
- Variation in several runs supports retaining repeatability testing in v1.2.
