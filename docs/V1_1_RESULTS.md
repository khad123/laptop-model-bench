# Laptop Model Bench v1.1 Results

v1.1 reruns the original v1 benchmark methodology on six current finalists.
The v1.0.0 release remains frozen and unchanged.

## Overall leaderboard

| Rank | Model | Overall | Capability | Efficiency | Developer | Speed | Quality/GiB |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `qwen35-2b-q4km` | 78.59 | 85.49 | 39.51 | 87.02 | 39.09 | 65.74 |
| 2 | `minicpm5-2b-q4km` | 66.34 | 71.96 | 34.49 | 72.96 | 36.23 | 49.49 |
| 3 | `smollm3-3b-iq4xs` | 59.33 | 64.36 | 30.81 | 63.90 | 26.08 | 40.09 |
| 4 | `qwen35-0.8b-q4km` | 56.85 | 51.59 | 86.65 | 39.40 | 78.01 | 95.58 |
| 5 | `k2-0.9b-q4km` | 55.66 | 52.33 | 74.53 | 44.63 | 75.89 | 84.34 |
| 6 | `minicpm5-1b-q4km` | 46.90 | 39.18 | 90.66 | 26.83 | 100.00 | 61.14 |

## Capability breakdown

| Model | Reasoning | Coding | MiniSWE | Instruction | Agents | Context |
|---|---:|---:|---:|---:|---:|---:|
| `qwen35-2b-q4km` | 80.00 | 75.00 | 86.29 | 83.33 | 100.00 | 77.78 |
| `minicpm5-2b-q4km` | 77.50 | 91.67 | 97.14 | 89.58 | 22.00 | 66.67 |
| `smollm3-3b-iq4xs` | 77.50 | 66.67 | 94.00 | 44.06 | 21.00 | 100.00 |
| `qwen35-0.8b-q4km` | 65.84 | 50.00 | 32.00 | 72.08 | 38.67 | 88.89 |
| `k2-0.9b-q4km` | 68.34 | 83.33 | 8.57 | 77.08 | 54.00 | 44.44 |
| `minicpm5-1b-q4km` | 64.16 | 66.67 | 8.57 | 89.58 | 11.33 | 33.33 |

## Laptop performance

| Model | PP tok/s | TG tok/s | Peak RSS GiB | Size GiB |
|---|---:|---:|---:|---:|
| `qwen35-2b-q4km` | 49.81 | 10.43 | 1.87 | 1.30 |
| `minicpm5-2b-q4km` | 40.76 | 10.21 | 2.46 | 1.45 |
| `smollm3-3b-iq4xs` | 15.53 | 8.76 | 1.78 | 1.61 |
| `qwen35-0.8b-q4km` | 116.19 | 19.09 | 0.76 | 0.54 |
| `k2-0.9b-q4km` | 84.46 | 21.48 | 1.11 | 0.62 |
| `minicpm5-1b-q4km` | 155.79 | 23.78 | 1.04 | 0.64 |

## Category winners

- **Reasoning / knowledge:** `qwen35-2b-q4km` — 80.00
- **Coding:** `minicpm5-2b-q4km` — 91.67
- **MiniSWE:** `minicpm5-2b-q4km` — 97.14
- **Instruction:** `minicpm5-2b-q4km` — 89.58
- **Agents / tools:** `qwen35-2b-q4km` — 100.00
- **Context:** `smollm3-3b-iq4xs` — 100.00
- **Prompt speed:** `minicpm5-1b-q4km` — 155.79
- **Generation speed:** `minicpm5-1b-q4km` — 23.78

## Main findings

- **Qwen3.5-2B Q4_K_M** remains the strongest overall laptop model and the clear agent/tool-use winner.
- **MiniCPM5-2B Q4_K_M** is the strongest coding and MiniSWE model in this six-model run.
- **SmolLM3-3B IQ4_XS** is the context winner.
- **Qwen3.5-0.8B Q4_K_M** remains the strongest balanced lightweight choice.
- **MiniCPM5-1B Q4_K_M** is the raw speed winner, but its capability score is substantially lower.

## Scoring

- Overall laptop score: **85% capability + 15% efficiency**.
- Capability weights are unchanged from v1.0.
- Efficiency uses normalized prompt speed, generation speed, peak RSS, and model size.
- Efficiency normalization is relative to the six-model v1.1 pool.
- Developer score: **30% coding + 40% MiniSWE + 30% agents**.

v1.2 will expand task coverage, context scaling, repeatability, system-resource measurements, and real-world workloads.
