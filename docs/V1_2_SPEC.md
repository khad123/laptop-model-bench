# Laptop Model Bench v1.2 Specification

## Goal

v1.2 is a deeper, more reliable benchmark for small local models running CPU-only on this laptop.

It is not intended to rank every model on the internet. It answers:

> Which local model is actually the most useful on this specific low-resource laptop?

v1.0 and v1.1 remain frozen and unchanged.

---

## Finalist Pool

Primary v1.2 finalists:

| ID | Model | Quant | Role |
|---|---|---|---|
| `qwen35-0.8b-q4km` | Qwen3.5-0.8B | Q4_K_M | Lightweight all-rounder |
| `qwen35-2b-q4km` | Qwen3.5-2B | Q4_K_M | Overall / agent leader |
| `minicpm5-2b-q4km` | MiniCPM5-2B | Q4_K_M | Coding / MiniSWE leader |
| `smollm3-3b-iq4xs` | SmolLM3-3B | IQ4_XS | Context / repo-work contender |

Optional reference:
- `k2-0.9b-q4km` — specialist/reference only, not required in every expensive v1.2 phase.

---

# Phase 1 — Laptop Performance

Measure each model under controlled conditions.

## Metrics

- prompt-processing speed (PP tok/s)
- generation speed (TG tok/s)
- time to first token (TTFT)
- total wall-clock completion time
- peak model-process RSS
- peak total system RAM usage
- swap usage before/after
- model file size
- CPU utilization
- failures / crashes / timeouts

## Prompt sizes

At minimum:

- short prompt
- medium prompt
- long prompt

Do not rely on one tiny synthetic prompt.

## Repeats

Run each important performance case 3 times.

Report:
- median
- min/max
- variation

---

# Phase 2 — Reasoning and Knowledge

Target: approximately 30–40 tasks.

Include:

- arithmetic
- multi-step numerical reasoning
- logic
- deduction
- commonsense reasoning
- science / technical knowledge
- software-engineering knowledge
- ambiguity handling

Difficulty mix:

- easy
- medium
- hard

Prefer automatically scorable answers where possible.

---

# Phase 3 — Coding

Target: at least 20 executable tasks.

Include:

- functions
- algorithms
- parsing
- data structures
- bug fixing
- edge cases
- refactoring
- shell / Linux
- Python
- C or systems-style tasks
- JavaScript where practical

Scoring should primarily use tests, not subjective text grading.

Track:

- tests passed
- syntax failures
- runtime failures
- incomplete answers
- unnecessary prose / format failures

---

# Phase 4 — MiniSWE v2

Increase from the small v1 set to approximately 15–20 repository tasks.

Test real software-engineering behavior:

- locate correct file
- understand multiple files
- fix an existing bug
- implement a small feature
- update tests
- preserve existing behavior
- modify configuration
- follow project conventions
- diagnose failing tests

Scoring:

- automated tests
- patch validity
- correct files changed
- regression checks
- partial-credit test count

This phase should have significantly more weight than isolated code generation.

---

# Phase 5 — Instruction Following

Test the same abilities using multiple prompt wordings.

Include:

- exact output format
- JSON schema
- required fields
- forbidden fields
- ordering constraints
- length constraints
- transformation tasks
- multiple simultaneous constraints
- conflicting / distracting information

Use 2–3 variants for important instruction types to reduce prompt-luck effects.

---

# Phase 6 — Agents and Tool Use

This phase must distinguish model capability from protocol compatibility.

## A. Common Protocol

All models receive the exact same generic tool-call protocol.

This preserves apples-to-apples comparison with v1/v1.1.

## B. Native Protocol

Where supported, test the model using its intended/native tool format.

Report Common and Native separately.

Do NOT silently replace Common scores with Native scores.

## Tasks

Include:

- select correct tool
- choose not to call a tool
- fill arguments correctly
- multi-tool sequences
- use previous tool result
- recover from failed tool result
- avoid unnecessary calls
- preserve state across steps
- tool + reasoning + final answer

Track separately:

- structured-call validity
- correct tool
- argument accuracy
- task outcome
- sequence/order
- recovery behavior

---

# Phase 7 — Context Scaling

Test actual context scaling instead of only short retrieval.

Target context sizes:

- 8K
- 16K
- 32K
- 64K

128K is optional and only attempted if 64K is still practical.

At each context size measure:

- retrieval accuracy
- instruction retention
- multi-fact synthesis
- long-code understanding
- PP speed
- TTFT
- peak RAM
- swap
- wall time
- timeout / crash

Do not give a model credit merely because it technically accepts the context length.

Usability matters.

---

# Phase 8 — Real Laptop Workloads

Create several end-to-end tasks representing actual use.

Examples:

1. Read a small repository, find a bug, fix it, and explain the cause.
2. Answer a question requiring information from several files.
3. Write code, run tests, inspect failure, then correct the implementation.
4. Complete a multi-step tool workflow.
5. Read a long technical document and preserve important facts.
6. Follow a long prompt containing many simultaneous constraints.
7. Normal conversational reasoning with useful response quality.

Measure both quality and elapsed time.

---

# Phase 9 — Reliability / Repeatability

The benchmark should explicitly measure instability.

Repeat:
- close leaderboard comparisons
- important coding cases
- MiniSWE cases where results differ strongly between runs
- selected agent cases

At least 3 runs for selected validation cases.

Track:

- pass consistency
- score standard deviation
- output instability
- crashes
- timeouts

Create a Confidence / Reliability score.

---

# Scoring

Do not collapse everything into one opaque number.

Publish separately:

1. Capability Score
2. Laptop Efficiency Score
3. Developer Score
4. Agent Score
5. Long-Context Score
6. Reliability Score
7. Overall Laptop Score

The overall score should remain secondary to the category scores.

## Proposed capability structure

Capability should emphasize real work:

- Reasoning / knowledge: 15%
- Coding: 15%
- MiniSWE: 25%
- Instruction following: 10%
- Agents / tools: 20%
- Context: 10%
- Real-world workload: 15%

Normalize internally when producing the final capability score.

Exact final weights must be frozen before official v1.2 runs begin.

---

# Experimental Rules

For official comparison runs:

- same laptop
- CPU-only
- same llama.cpp build
- same thread count
- same sampling settings
- same benchmark prompts
- no unrelated heavy processes
- one model benchmark at a time
- record runtime/version information
- preserve raw outputs locally
- commit only frozen summaries needed for reproducibility

A failed task is not the same as infrastructure failure.

Record separately:

- model failure
- parser failure
- timeout
- process crash
- infrastructure error

---

# Important v1.1 Findings To Validate

v1.2 should specifically investigate:

## MiniCPM5-2B

v1.1 showed:
- excellent coding
- excellent MiniSWE
- excellent instruction following
- very weak generic agent/tool score

Determine whether the low agent score is:
1. actual reasoning weakness, or
2. tool-protocol incompatibility.

## SmolLM3-3B

MiniSWE changed substantially between benchmark runs.

v1.2 must test repeatability and confidence.

## Qwen3.5-2B

v1.1 overall leader and 100% generic agent score.

Verify with a larger, harder agent set.

## Qwen3.5-0.8B

Strong lightweight efficiency.

Determine how far it can scale in context and real-world work before quality drops.

---

# Release Rule

Do not call the benchmark v1.2.0 until:

- methodology is frozen
- task sets are frozen
- scoring weights are frozen
- all official finalist runs complete
- integrity checks pass
- report can be reproduced from frozen result files

Development versions may use `v1.2-dev`.
