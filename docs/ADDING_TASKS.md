# Adding benchmark tasks

This guide describes how to extend Laptop Model Bench without invalidating the frozen v1 results.

## First rule: do not mutate frozen v1 tasks

The v1 task files are part of the benchmark definition. After v1 is frozen, do not change their prompts, hidden tests, expected answers, scoring logic, or ordering merely because a model failed them.

For new tasks, create a new task-set version such as `phase3_v0.2.json` or a future benchmark version rather than rewriting the historical v1 files.

## General task principles

A good task should be:

- deterministic enough to score automatically
- small enough to run on the target laptop
- identical for every model
- free of model-specific prompt workarounds
- auditable from saved raw output
- focused on the category it is supposed to measure
- resistant to accidental formatting or parser artifacts unless formatting itself is the category

Keep infrastructure failures separate from model failures.

## Phase 2 — reasoning and knowledge

Task file: `tasks/phase2_v0.3.json`

Phase 2 uses compact multiple-choice tasks and balances answer positions. Preserve the distinction between reasoning and knowledge because the final Phase 2 score gives the two domains equal top-level weight.

When adding tasks:

1. Keep answers objectively checkable.
2. Maintain balanced A/B/C/D answer positions.
3. Avoid questions whose answer depends on current news or external internet access.
4. Review difficulty with a pilot before freezing the new task-set version.

## Phase 3 — coding

Task file: `tasks/phase3_v0.1.json`

Coding tasks generate Python functions that are evaluated by hidden deterministic tests inside Bubblewrap.

When adding tasks:

1. Define the function contract clearly.
2. Write hidden tests before benchmarking models.
3. Include edge cases rather than only happy-path examples.
4. Keep execution bounded by the existing CPU/RAM/wall-time sandbox limits.
5. Do not inspect a model's answer and then add a special test just for that model within the same frozen benchmark version.

## Phase 4 — MiniSWE

Task file: `tasks/phase4_v0.2.json`

MiniSWE measures repository-level software engineering, not strict formatting.

Each task should contain:

- a tiny deterministic repository fixture
- an issue description
- an allow-list of files the model may replace
- hidden tests/checks
- enough partial checks to distinguish partial progress from total failure

Keep repositories small enough that the prompt and test cycle remain practical on the target laptop.

## Phase 5 — instruction following

Task file: `tasks/phase5_v0.1.json`

This phase intentionally measures exact compliance. New tasks may test:

- exact formatting
- required/forbidden content
- ordering
- JSON/schema compliance
- length/count constraints

Unlike MiniSWE, extra prose can intentionally count as failure here.

Every constraint should be expressible as a deterministic checker. Avoid subjective style judgments.

## Phase 6 — tool / agent use

Task file: `tasks/phase6_v0.1.json`

Phase 6 uses deterministic local mock tools. It does not rely on native provider-specific tool-calling APIs.

New tasks should specify:

- available tools
- required or missing information
- expected action/tool sequence
- expected arguments
- expected final outcome

Prefer tasks that discriminate between similar tools or require a short multi-step sequence. Keep the environment deterministic and offline.

## Phase 7 — context handling

Task file: `tasks/phase7_v0.2.json`

Phase 7 v0.2 uses paired tasks across approximately 1K, 2K, and 4K prompt lengths. The semantic task stays the same while only irrelevant filler grows.

For new context families:

1. Define one semantic problem first.
2. Repeat that same problem across all target lengths.
3. Keep evidence positions comparable across lengths.
4. Record actual prompt tokens from `llama-server`; character count is only a construction target.
5. Separate infrastructure timeouts from wrong answers.

Do not compare different questions at different lengths and call the difference context degradation.

## Pilot and freeze workflow

For a future task-set version:

1. Write the task and deterministic checker.
2. Run a single-model smoke test.
3. Audit failures for parser/scorer mistakes.
4. Run a small pilot if necessary.
5. Freeze the task set before the official all-model run.
6. Record the task-set version and exact official run ID in the docs.

## Reporting compatibility

When a phase version changes, update the Phase 9/reporting source list explicitly. Never assume `phaseX-latest.json` is the official result because latest aliases may point to pilots or validation subsets.

Historical v1 scores should remain reproducible from their original frozen task files and timestamped result files.
