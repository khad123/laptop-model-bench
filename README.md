# Laptop Model Bench

A lightweight, reproducible benchmark suite for comparing small local LLMs on a low-resource laptop.

The goal is not to reproduce every large industry benchmark. The goal is to answer practical questions for this machine:

- Which model is fastest?
- Which model is smartest overall?
- Which model is best for coding?
- Which model is best at small software-engineering tasks?
- Which model follows instructions best?
- Which model is best at tool/function calling?
- Which model gives the best quality per GB of RAM/storage?
- Which quantization gives the best quality/resource trade-off?

## Target hardware

Initial target machine:

- CPU: Intel Core i5, 8th generation
- RAM: 8 GB
- GPU: CPU-only benchmark target
- OS: Linux
- Runtime: `llama.cpp`
- Default CPU threads: `4`
- Default context: `4096`

The benchmark is designed so additional machines can be added later without changing the test set.

## Benchmark categories

1. **Speed & efficiency** — prompt processing, generation speed, model size, load time, RAM usage.
2. **Reasoning** — compact math and logic tests inspired by tinyGSM8K/tinyARC-style evaluation.
3. **General knowledge** — a compact multi-domain benchmark inspired by tinyMMLU.
4. **Coding** — small HumanEval+/MBPP+-style executable tasks.
5. **MiniSWE** — tiny repository bug-fixing tasks with automated tests.
6. **Instruction following** — strict-format and constraint-following tasks.
7. **Tool / agent ability** — function selection, JSON arguments, multi-step tool-style tasks.
8. **Context handling** — retrieval and use of information at increasing prompt lengths.
9. **Quantization comparison** — compare variants such as Q4_K_M vs IQ4_XS on the same base model.

## Planned leaderboards

The project will report multiple winners instead of hiding everything behind one score:

- Smartest model
- Fastest model
- Best overall laptop model
- Best coding model
- Best MiniSWE model
- Best tool/agent model
- Best instruction follower
- Best reasoning model
- Best quality per GB
- Best quantization trade-off

## Fair-test defaults

Unless a task explicitly requires something different:

- Same laptop
- Same runtime
- 4 CPU threads
- 4096-token context
- Deterministic decoding / temperature 0 where supported
- Fixed seed where supported
- Same prompt for every model
- Same output limit
- Native chat template
- No internet during evaluation
- Raw outputs saved before scoring

See [`docs/BENCHMARK_PROTOCOL.md`](docs/BENCHMARK_PROTOCOL.md) for the full protocol.

## Initial model pool

Planned initial comparisons include:

- K2-Horizon-0.9B Q4_K_M
- Qwen3.5-0.8B Q4_K_M
- Qwen3.5-2B Q4_K_M
- Qwen3.5-2B IQ4_XS
- LFM2.5-1.2B-Instruct Q4_K_M
- SmolLM3-3B
- Gemma 3 1B
- Llama 3.2 1B Instruct

The exact quant used for each model will be recorded with every result.

## Known baseline

K2-Horizon-0.9B Q4_K_M on this laptop, 4 threads:

- Prompt processing: ~96.96 tokens/s
- Token generation: ~22.93 tokens/s

This is an existing measurement and will be re-run under the final automated protocol before being treated as an official result.

## Project status

We are currently in **Phase 0 — methodology and test-set design**. No model should be declared a winner until the protocol and v1 task set are frozen.

- [Plan](docs/PLAN.md)
- [Checklist](docs/CHECKLIST.md)
- [Benchmark protocol](docs/BENCHMARK_PROTOCOL.md)

## Philosophy

A small local model should not be judged only by benchmark accuracy or only by tokens per second. On an 8 GB laptop, a slightly weaker model may be much more useful if it is dramatically faster, smaller, and more responsive.

This project therefore keeps **capability**, **speed**, and **resource efficiency** as separate measurements, then combines them only in clearly defined practical leaderboards.
