# v1.2 Phase 9B — Runtime Optimization

Status: FROZEN

Phase 9B tunes deployment/runtime settings only.
These results do not replace or modify the Phase 1 baseline efficiency scores.

## Recommended CPU Runtime Profile

Target:
- CPU-only laptop
- 8 GB RAM class
- llama.cpp
- Qwen3.5-2B Q4_K_M reference model

Recommended settings:

    -t 4
    -b 512
    -ub 512
    -ctk f16
    -ctv f16
    -ngl 0

## Results

### Threads
Winner: `-t 4`

### Ubatch

Performance mode:

| ubatch | PP2048 | TG128 |
|---:|---:|---:|
| 512 | 49.84 ± 0.62 | 10.58 ± 0.02 |
| 1024 | 46.50 ± 2.15 | 10.08 ± 0.54 |

Winner: `-ub 512`

Power Saver validation:

| ubatch | PP2048 | TG128 |
|---:|---:|---:|
| 512 | 19.35 ± 0.04 | 5.06 ± 0.10 |
| 1024 | 18.95 ± 0.16 | 5.15 ± 0.01 |

`-ub 512` remains the recommended general default.

### Batch size

| batch | PP2048 | TG128 |
|---:|---:|---:|
| 512 | 51.15 ± 2.20 | 10.18 ± 0.01 |
| 1024 | 49.54 ± 0.06 | 10.18 ± 0.01 |
| 2048 | 49.55 ± 0.06 | 10.14 ± 0.02 |

Winner: `-b 512`

### Batch/prompt threads

`-tb` is unsupported by llama-bench build `35999d101 (10671)`.

Status: SKIPPED / unsupported.

### KV cache

2K test:

| KV | PP2048 | TG128 |
|---|---:|---:|
| F16 | 49.62 ± 0.56 | 10.18 ± 0.01 |
| Q8_0 | 45.98 ± 0.01 | 10.15 ± 0.02 |

8K test:

| KV | PP8192 | TG128 | Peak RSS |
|---|---:|---:|---:|
| F16 | 45.65 | 10.16 | 2,076,092 KB |
| Q8_0 | 35.45 | 10.13 | 2,030,232 KB |

Q8_0 saved only about 45 MiB of peak RSS while significantly reducing prompt-processing throughput.

Winner:
- `-ctk f16`
- `-ctv f16`

## Final Phase 9B Profile

    -t 4
    -b 512
    -ub 512
    -ctk f16
    -ctv f16
    -ngl 0

This profile is the frozen Phase 9B recommendation for v1.2.
