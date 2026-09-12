# Phase 6 — Mini Tool / Agent Runner

Phase 6 measures practical local agent behavior with deterministic mock tools and no external network or API dependencies.

## Entry point

```bash
./agent.sh
```

Task file:

```text
tasks/phase6_v0.1.json
```

Phase 6 v0.1 is development-only until the pilot is audited and the task set is frozen.

## What it tests

The compact v0.1 set contains 10 tasks:

- 3 simple single-tool tasks
- 3 similar-tool disambiguation tasks
- 2 missing-required-information tasks
- 2 multi-step tool sequences

The benchmark tests whether a model can:

- emit valid structured actions
- choose the correct tool
- provide the correct arguments
- distinguish similar tools
- ask for required missing information instead of inventing it
- use prior tool results in later calls
- terminate with the correct final result

## Runtime-neutral action protocol

This phase deliberately does not use the OpenAI `tools` request field. Tool support in chat templates varies substantially across local models and runtimes. Instead, every model sees the same textual tool catalog and must emit exactly one JSON action per turn.

Tool call:

```json
{"action":"tool","name":"weather_lookup","arguments":{"city":"Rabat"}}
```

Missing required information:

```json
{"action":"ask","field":"city"}
```

Final answer:

```json
{"action":"final","answer":24}
```

The runner executes valid mock-tool calls locally, appends the deterministic tool result to the conversation, and requests the next JSON action. This preserves the decision/action/result loop while avoiding runtime-specific native-tool templates.

## Mock tools

The local catalog includes deterministic functions for:

- weather lookup
- addition and multiplication
- order lookup
- customer lookup by email or ID
- inventory lookup by SKU or product name
- exchange-rate lookup and amount conversion
- customer-order lookup

No tool performs external I/O or network access.

## Scoring

Each expected action step is checked for:

- valid JSON
- valid action schema
- correct action type/order
- correct tool name when applicable
- exact semantic arguments when applicable
- correct ask field or final result when applicable

An additional sequence-length check penalizes missing or extra actions.

`task_score` is the percentage of checks passed for that task. `phase6_score` is the equal-weight mean of task scores, so complex multi-step tasks do not receive extra top-level weight merely because they contain more checks.

The summary also reports aggregate diagnostic metrics:

- `structured`
- `sequence`
- `tool_choice`
- `arguments`
- `outcome`

Numeric JSON values are compared semantically, so `20` and `20.0` are treated as the same numeric argument. Booleans remain type-strict.

## Runtime defaults

- CPU-only
- 4 threads
- context: 4096
- temperature: 0
- seed: 42
- `reasoning_effort=none`
- prompt cache disabled
- maximum 192 generated tokens per action
- maximum 4 model actions per task

## Common commands

Preflight all 12 model/quant entries:

```bash
./agent.sh --dry-run --include-comparisons
```

Single-task smoke test:

```bash
./agent.sh --only qwen35-2b-q4km --task agent-09
```

Full pilot on one model:

```bash
./agent.sh --only qwen35-2b-q4km
```

Full 12-entry run after the task set is validated:

```bash
./agent.sh --include-comparisons
```

## Artifacts

Summary files:

```text
results/phase6-<run-id>.json
results/phase6-<run-id>.csv
results/phase6-latest.json
results/phase6-latest.csv
```

Raw artifacts:

```text
results/raw/phase6/<run-id>/<model-id>/<task-id>/
```

Each task directory contains per-step request/response JSON, raw model output, the complete action/tool transcript, and a deterministic score breakdown.

## Freeze rule

Before the official all-model run:

1. verify all local models and tasks resolve in dry-run mode;
2. smoke-test at least one multi-step task;
3. run all 10 tasks on one pilot model;
4. audit failures for protocol/scorer ambiguity;
5. only then freeze Phase 6 and run every model/quant entry.
