# Benchmark Protocol

This document defines the rules for official Laptop Model Bench results.

The protocol exists to prevent accidental cherry-picking, prompt changes, or configuration drift between models.

## 1. Hardware profile

Initial official profile:

- Laptop CPU: Intel Core i5, 8th generation
- RAM: 8 GB
- GPU acceleration: disabled for the CPU-only profile
- OS: Linux

Exact CPU model, kernel, RAM availability, llama.cpp commit, and other environment metadata will be captured automatically once the runner is implemented.

## 2. Runtime

Default runtime:

- `llama.cpp`
- current local K2-compatible build initially allowed
- exact binary version and Git commit must be recorded in every official run

If runtime changes materially, results must be marked as belonging to a different runtime profile rather than silently mixed.

## 3. Default inference configuration

Unless a benchmark requires another configuration:

- CPU threads: `4`
- context size: `4096`
- temperature: `0` / deterministic decoding where supported
- fixed seed where supported
- same maximum generation length for the same task
- native model chat template
- no network access during benchmark tasks
- no external tools except in the explicit Tool/Agent category

## 4. Model identity

Every result must record:

- model display name
- base model family
- parameter count if known
- quantization
- GGUF repository/source
- exact GGUF filename or Hugging Face selector
- model file size
- model hash if practical

Different quantizations of the same model are separate benchmark entries.

## 5. Speed benchmark

Use `llama-bench` for reproducible core throughput measurements.

Required metrics:

- prompt processing tokens/s
- token generation tokens/s
- model size
- runtime version
- number of CPU threads

Additional metrics to implement:

- wall-clock model load time
- peak resident RAM if measurable reliably

Run multiple iterations where the tool supports them and retain the reported variation.

Do not compare a 4-thread result from one model against an 8-thread result from another in the primary leaderboard.

## 6. Capability benchmark principles

### Same questions

Every model gets the exact same frozen v1 tasks.

### No adaptive prompt editing

A prompt must not be rewritten because one model performs poorly on it. Changes to a benchmark task create a new benchmark version.

### Automated scoring first

Prefer objective scoring:

- exact answer
- multiple choice
- unit tests
- schema validation
- rule validation

Subjective judging should be avoided in v1 unless absolutely necessary.

### Save raw outputs

Every generated response must be stored before scoring so incorrect or surprising scores can be audited.

## 7. Reasoning

Reasoning score should come from a compact, fixed set covering:

- arithmetic
- multi-step word problems
- logic/scientific reasoning

Prefer established compact benchmark definitions where licensing and tooling allow.

Primary metric: accuracy percentage.

## 8. General knowledge

Use a compact multi-domain test rather than a large full benchmark.

Primary metric: accuracy percentage.

Where categories exist, preserve sub-scores instead of only storing one total.

## 9. Coding

Coding tasks must be executable and automatically tested.

For each task record:

- prompt
- raw model output
- extracted code
- execution/test result
- timeout/failure type

Primary metric: pass rate.

No model receives manual fixes before execution.

## 10. MiniSWE

MiniSWE tests repository-level engineering rather than standalone code generation.

Each task must include:

- a small repository snapshot
- issue description
- hidden or protected tests where practical
- deterministic test command

Primary score:

- solved: all required tests pass
- partial: optional diagnostic score, clearly separate from solved rate
- failed: required tests still fail or patch cannot be applied

The headline metric is percentage fully solved.

## 11. Instruction following

Tasks should be objectively checkable, including requirements such as:

- exact item count
- required phrases
- forbidden phrases
- maximum lengths
- ordering
- JSON/schema structure

Primary metric: percentage of constraints satisfied, with full-task success reported separately.

## 12. Tool / agent tasks

Use deterministic local mock functions.

Score components can include:

- correct function selection
- valid structured output
- correct parameter names
- correct parameter values
- correct multi-step sequence

Do not give models live internet access for v1.

## 13. Context handling

Initial context levels:

- ~1K
- ~2K
- ~4K tokens

The information placement should vary across tasks so the suite does not only measure recall from the final paragraph.

Primary metric: answer accuracy at each context length.

## 14. Quantization comparisons

Quantization experiments compare variants of the same base model.

Report separately:

- disk-size reduction
- RAM reduction if measured
- prompt-speed change
- generation-speed change
- capability-score change by category

Do not claim an exact percentage of “intelligence lost.” Instead report measured benchmark deltas.

## 15. Leaderboards

Do not collapse all information into one number only.

Primary leaderboards:

- Fastest
- Smartest / best capability aggregate
- Best reasoning
- Best coding
- Best MiniSWE
- Best instruction following
- Best tool/agent
- Best quality per GB
- Best overall laptop model
- Best quantization trade-off

Any aggregate score must publish its formula and weights.

## 16. Overall laptop score

The exact formula is not frozen yet.

It should balance at least:

- capability
- generation responsiveness
- memory/storage efficiency

The raw metrics must always remain visible so users can disagree with the weighting and choose their own winner.

## 17. Benchmark versioning

Once v1 tasks are frozen:

- tasks must not change silently
- prompt/scoring changes require a version bump
- results must record benchmark version

Suggested versioning:

- `v0.x` during development
- `v1.0` first frozen public suite

## 18. Existing unofficial baseline

A pre-protocol measurement exists for:

**K2-Horizon-0.9B Q4_K_M**

- threads: 4
- prompt processing: ~96.96 tok/s
- generation: ~22.93 tok/s

This is useful as a sanity check but should be re-run and saved by the automated harness before becoming an official result.
