# Adding a model

This guide describes how to add a new local GGUF model to Laptop Model Bench without changing the frozen v1 methodology.

## 1. Add the model to the registry

Edit `docs/MODEL_REGISTRY.md`.

For a new base model, add one row under **Primary v1 capability pool** (or the corresponding pool for a future benchmark version):

```text
| model-id | Display name | owner/repository | Q4_K_M | 1.2G | Primary |
```

For another quantization of a base model that is already present, add it under **Same-base quant comparisons** and identify the quant it should be compared against.

### Model ID rules

Use a short stable ID that contains the base model and quant, for example:

```text
qwen35-2b-q4km
qwen35-2b-iq4xs
```

Do not reuse an existing ID for a different file or model revision.

## 2. Put the GGUF in the local Hugging Face cache

The benchmark runners resolve files from the local Hugging Face cache and intentionally do not download missing models during a benchmark run.

A registry row must therefore point to a repository that already exists under the local HF cache. The runner searches the current snapshot for one standalone `.gguf` matching the requested quant.

Projector/mmproj files are not standalone text models and must not be registered as separate model entries.

## 3. Preflight before inference

Run a preflight command before starting a large benchmark. For example:

```bash
./context.sh --dry-run --include-comparisons
```

Other runners expose similar model resolution behavior. Resolve ambiguous or missing GGUFs before collecting scores.

## 4. Keep the runtime fair

Do not add model-specific prompt tweaks, decoding settings, or thread counts simply because a model performs poorly.

The v1 fairness rules are:

- same laptop
- same runner/runtime for a category
- CPU-only where the phase specifies CPU-only
- 4 CPU threads
- deterministic decoding where supported
- same task prompt across models
- same output limit across models within the phase
- native chat template
- no internet during evaluation

If a new architecture requires a different llama.cpp build, record that fact explicitly in the result metadata rather than silently changing the protocol.

## 5. Run the frozen phases

For a model added to an existing benchmark version, run the frozen task set without editing prompts or expected answers after seeing its output.

The v1 phase entry points are:

```text
bench.sh         Phase 1 — speed/resources
capability.sh    Phase 2 — reasoning/knowledge
coding.sh        Phase 3 — executable coding
miniswe.sh       Phase 4 — repository-level SWE
instruction.sh   Phase 5 — instruction following
agent.sh         Phase 6 — tools/agents
context.sh       Phase 7 — context handling
```

Use `--only MODEL_ID` where supported to avoid rerunning the entire model pool.

## 6. Preserve raw artifacts

Do not edit generated model output before scoring. Raw phase artifacts are intentionally saved so failures can be audited later.

`results/raw/` is local and ignored by Git because it can become large. Summary JSON/CSV files may be retained for reproducibility and reporting.

## 7. Update reporting intentionally

Phase 9 uses explicit frozen run IDs rather than whatever happens to be stored in `*-latest.json`.

If a future model is being added to a new benchmark version, update the report builder's source set and model pool deliberately. Do not silently mix a validation subset with the official run.

If a model is only an alternate quant, keep it visible in the all-entry report and decide separately whether it becomes the recommended quant for that base model.

## 8. Versioning rule

The v1 leaderboard is frozen. Adding a new model after the v1 release should normally create a new benchmark/report version (for example v1.1) rather than rewriting historical v1 results.
