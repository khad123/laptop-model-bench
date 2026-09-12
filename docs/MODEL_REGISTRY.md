# Model Registry — v1

This file records the exact local model pool for the first benchmark round.

The registry distinguishes between:

- **Primary** — the quant used for capability leaderboards.
- **Quant comparison** — same base model, alternate quant used to measure speed/RAM/quality trade-offs.
- **Excluded** — installed locally but intentionally not treated as a separate benchmark model.

## Primary v1 capability pool

| ID | Model | Repository | Quant | Role |
|---|---|---|---|---|
| `k2-0.9b-q4km` | K2-Horizon-0.9B | `NANI-Nithin/K2-Horizon-0.9B-GGUF` | `Q4_K_M` | Primary |
| `qwen35-0.8b-q4km` | Qwen3.5-0.8B | `bartowski/Qwen_Qwen3.5-0.8B-GGUF` | `Q4_K_M` | Primary |
| `qwen35-2b-q4km` | Qwen3.5-2B | `bartowski/Qwen_Qwen3.5-2B-GGUF` | `Q4_K_M` | Primary/reference quant |
| `lfm25-1.2b-q4km` | LFM2.5-1.2B-Instruct | `LiquidAI/LFM2.5-1.2B-Instruct-GGUF` | `Q4_K_M` | Primary |
| `smollm3-3b-iq4xs` | SmolLM3-3B | `bartowski/HuggingFaceTB_SmolLM3-3B-GGUF` | `IQ4_XS` | Primary compressed quant |
| `gemma3-1b-iq4xs` | Gemma 3 1B IT | `bartowski/google_gemma-3-1b-it-GGUF` | `IQ4_XS` | Primary compressed quant |
| `llama32-1b-iq4xs` | Llama 3.2 1B Instruct | `bartowski/Llama-3.2-1B-Instruct-GGUF` | `IQ4_XS` | Primary compressed quant |

## Same-base quant comparisons

These are benchmarked separately so we can measure whether the smaller/larger quant is worth it on this laptop.

| ID | Model | Repository | Quant | Compare against |
|---|---|---|---|---|
| `k2-0.9b-q6k` | K2-Horizon-0.9B | `NANI-Nithin/K2-Horizon-0.9B-GGUF` | `Q6_K` | K2 Q4_K_M |
| `qwen35-2b-iq4xs` | Qwen3.5-2B | `bartowski/Qwen_Qwen3.5-2B-GGUF` | `IQ4_XS` | Qwen3.5-2B Q4_K_M |
| `smollm3-3b-q4km` | SmolLM3-3B | `ggml-org/SmolLM3-3B-GGUF` | `Q4_K_M` | SmolLM3 IQ4_XS |
| `gemma3-1b-q4km` | Gemma 3 1B IT | `ggml-org/gemma-3-1b-it-GGUF` | `Q4_K_M` | Gemma 3 IQ4_XS |
| `llama32-1b-q4km` | Llama 3.2 1B Instruct | `bartowski/Llama-3.2-1B-Instruct-GGUF` | `Q4_K_M` | Llama 3.2 IQ4_XS |

## Installed but excluded from v1 leaderboard

### LFM2-1.2B Q4_K_M HIP-optimized

Local cache:

`LiquidAI/LFM2-1.2B-GGUF`

Downloaded file:

`LFM2-1.2B-Q4_K_M-hip-optimized.gguf`

Reason for exclusion: this is the older LFM2 generation and the cached file is explicitly HIP-optimized. The v1 benchmark uses newer LFM2.5-1.2B-Instruct Q4_K_M instead. It may be tested later as a historical comparison.

### Ollama `llama3.2:1b`

Installed in Ollama, size shown locally as 1.3 GB.

Reason for exclusion: the benchmark standardizes on the local llama.cpp runtime and already has explicit Llama 3.2 GGUF Q4_K_M and IQ4_XS variants. The Ollama copy would be a runtime/package duplicate, not a new base model.

### Qwen3.5 `mmproj` files

Downloaded alongside Qwen3.5 0.8B/2B:

- `mmproj-Qwen_Qwen3.5-0.8B-bf16.gguf`
- `mmproj-Qwen_Qwen3.5-2B-bf16.gguf`

Reason for exclusion: these are multimodal projector files, not standalone language models. The initial benchmark is text-only/CPU-focused.

## Exact local cache repositories observed

- `NANI-Nithin/K2-Horizon-0.9B-GGUF`
- `bartowski/Llama-3.2-1B-Instruct-GGUF`
- `LiquidAI/LFM2-1.2B-GGUF`
- `ggml-org/SmolLM3-3B-GGUF`
- `ggml-org/gemma-3-1b-it-GGUF`
- `bartowski/Qwen_Qwen3.5-2B-GGUF`
- `bartowski/Qwen_Qwen3.5-0.8B-GGUF`
- `LiquidAI/LFM2.5-1.2B-Instruct-GGUF`
- `bartowski/HuggingFaceTB_SmolLM3-3B-GGUF`
- `bartowski/google_gemma-3-1b-it-GGUF`

## v1 rules for model identity

1. Base model + quantization is a unique benchmark entry.
2. Different repositories containing the same base model do not automatically count as different models.
3. Multimodal projector files do not count as standalone models.
4. Primary capability leaderboards compare one chosen quant per base model.
5. Alternate quants are reported in the quantization leaderboard and speed/resource tables.
6. All llama.cpp speed runs use 4 CPU threads unless the protocol explicitly changes before v1 is frozen.
7. Capability tests use 4096 context unless a dedicated context-length test says otherwise.

## Primary llama.cpp selectors

```text
NANI-Nithin/K2-Horizon-0.9B-GGUF:Q4_K_M
bartowski/Qwen_Qwen3.5-0.8B-GGUF:Q4_K_M
bartowski/Qwen_Qwen3.5-2B-GGUF:Q4_K_M
LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M
bartowski/HuggingFaceTB_SmolLM3-3B-GGUF:IQ4_XS
bartowski/google_gemma-3-1b-it-GGUF:IQ4_XS
bartowski/Llama-3.2-1B-Instruct-GGUF:IQ4_XS
```

## Current known pre-project measurements

K2-Horizon-0.9B Q4_K_M, 4 CPU threads:

- Prompt processing: ~96.96 tok/s
- Generation: ~22.93 tok/s

K2-Horizon-0.9B Q6_K, 4 CPU threads:

- Prompt processing: ~60.42 tok/s
- Generation: ~18.45 tok/s

These measurements are useful references but will be re-run by the final automated runner before being included as official v1 results.
