# Project Plan

## Goal

Build a compact, reproducible local-LLM benchmark for an 8 GB CPU-only laptop. The suite should be small enough to run repeatedly, but broad enough to distinguish models by speed, reasoning, coding, software-engineering ability, instruction following, tool use, context handling, and efficiency.

## Phase 0 — Freeze the methodology

Before implementation or official scoring:

- Define the model inventory format.
- Define the exact runtime defaults.
- Define deterministic decoding settings.
- Define each benchmark category and its score.
- Decide which tests are imported from public benchmark suites and which are custom.
- Define a frozen v1 task set.
- Define raw-output and result formats.
- Define practical leaderboards and any composite scores.

Deliverables:

- `README.md`
- `docs/PLAN.md`
- `docs/CHECKLIST.md`
- `docs/BENCHMARK_PROTOCOL.md`

## Phase 1 — Model inventory and speed harness

Build a model registry containing:

- display name
- base model
- quantization
- Hugging Face repository
- local cache/file information where useful
- approximate model size
- runtime compatibility

Build an automated speed benchmark using `llama-bench` and supplementary measurements for:

- prompt processing tokens/s
- generation tokens/s
- model load time
- peak RAM if reliable measurement is available
- on-disk model size

Raw benchmark output must be saved.

## Phase 2 — Compact intelligence benchmarks

Add small standardized tests for:

### Reasoning

- tinyGSM8K-style arithmetic/multi-step reasoning
- tinyARC-style logical/scientific reasoning

### General knowledge

- tinyMMLU-style multi-domain evaluation

Where possible, use established task definitions rather than rewriting benchmark questions manually.

## Phase 3 — Coding benchmark

Add executable coding tasks inspired by or sampled from:

- HumanEval+
- MBPP+

Requirements:

- generated code is executed in isolation
- scoring is based on tests, not subjective inspection
- pass/fail and failure type are stored
- prompts are identical across models

## Phase 4 — MiniSWE

Create a small repository-level software-engineering benchmark inspired by SWE-bench, but practical on this laptop.

Target v1:

- 5–10 tiny repositories/tasks
- Python first; JavaScript/TypeScript can be added later
- each task includes an issue description and automated tests
- model must patch existing code rather than answer a trivia question

Skills tested:

- understanding existing code
- locating bugs
- respecting constraints
- making minimal changes
- passing tests

## Phase 5 — Instruction-following benchmark

Create compact automatically-checkable tasks involving constraints such as:

- exact number of bullets
- required/forbidden words
- output schema
- length constraints
- ordering
- formatting

Scoring should be deterministic wherever possible.

## Phase 6 — Mini tool / agent benchmark

Create a lightweight BFCL-style evaluation for:

- selecting the correct function
- emitting valid structured arguments
- choosing between similar functions
- handling missing information
- simple multi-step tool sequences

No external internet is required. Tools can be deterministic local mock functions.

## Phase 7 — Context handling

Evaluate retrieval/use of information at increasing prompt lengths, initially targeting approximately:

- 1K tokens
- 2K tokens
- 4K tokens

Tests should check more than literal keyword copying where possible.

## Phase 8 — Quantization comparison

For base models with more than one quant, compare the quantizations directly.

Initial important comparison:

- Qwen3.5-2B Q4_K_M
- Qwen3.5-2B IQ4_XS

Track:

- size difference
- RAM difference
- prompt speed
- generation speed
- category score change

This allows a practical answer to: “How much capability do I lose for the resource savings?”

## Phase 9 — Reporting and leaderboards

Generate machine-readable and human-readable results.

Planned outputs:

- per-model detailed result
- per-category leaderboard
- overall laptop recommendation
- quantization comparison report
- raw benchmark artifacts

Leaderboards:

- Smartest
- Fastest
- Best overall laptop model
- Best coding model
- Best MiniSWE model
- Best tool/agent model
- Best instruction follower
- Best reasoning model
- Best quality per GB
- Best quantization trade-off

## Phase 10 — Reproducibility and expansion

After v1 is stable:

- add a single-command benchmark runner
- add environment/system metadata capture
- add CSV/JSON export
- add plots/tables
- document how to add a new model
- document how to add a benchmark task
- optionally add a second machine profile for desktop GPU testing

## Initial model pool

Current target pool:

1. K2-Horizon-0.9B Q4_K_M
2. Qwen3.5-0.8B Q4_K_M
3. Qwen3.5-2B Q4_K_M
4. Qwen3.5-2B IQ4_XS
5. LFM2.5-1.2B-Instruct Q4_K_M
6. SmolLM3-3B (quant to freeze before official run)
7. Gemma 3 1B (quant to freeze before official run)
8. Llama 3.2 1B Instruct (quant to freeze before official run)

## Non-goals for v1

- Reproducing full SWE-bench Verified
- Running giant benchmark suites for hours/days
- Comparing cloud APIs against local models
- Hiding results behind one unexplained composite score
- Changing prompts after seeing model results
