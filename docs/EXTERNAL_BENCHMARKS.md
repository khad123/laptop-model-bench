# Four-tool local model benchmark

This setup runs four complementary benchmarks against the installed GGUF files, one model at a time. It keeps tool dependencies in separate environments and stores run output under `results/external-four-suite/`.

## What each tool measures

| Tool | What the run measures | Fixed run size |
|---|---|---|
| `llama-bench` | CPU prompt processing and token generation speed | 512 prompt tokens, 128 generated tokens, 3 repeats, 4 threads |
| EvalPlus | Function-level Python code correctness against HumanEval+ tests | 10 evenly spaced HumanEval+ problems; model code is evaluated in a network-disabled Docker container |
| `llm-benchmark` | Small deterministic slice of arithmetic, reasoning, and instruction following | `math_001`, `math_003`, `reason_001`, `reason_004`, `instruct_001`, `instruct_004` |
| EleutherAI `lm-evaluation-harness` | Standardized multiple-choice language evaluation via llama.cpp log probabilities | First 50 HellaSwag examples |

All four use the same llama.cpp build and model cache. The default capability setup is CPU-only, 4 threads, 4096 context, temperature 0, and seed 42. These are deliberately bounded samples, not full benchmark leaderboards. EvalPlus is not the full 164-task suite, and HellaSwag is sampled at 50 items, so treat close scores as a reason to run a larger follow-up rather than a decisive tie-break.

The existing LMB Phase 3 coding and Phase 4 MiniSWE results remain separate and are not repeated by this runner.

## Install the tools

From the project root, run:

```bash
rtk bash scripts/setup_external_benchmarks.sh
```

The script installs `uv`-managed Python environments under the ignored `bench-tools/` directory, checks out the three GitHub suites at the exact revisions in `scripts/external_benchmark_revisions.json`, records installed Python package versions, and downloads the small HumanEval+ data file used by EvalPlus. `llama-bench` and `llama-server` are reused from the existing llama.cpp build; set `LLAMA_CPP_BIN` if that build lives elsewhere.

It does not load a model or start a benchmark. The first HellaSwag run will download its dataset if it is not already cached.

## Check the model list and plan

```bash
rtk python3 scripts/external_benchmark_runner.py --list-models
rtk python3 scripts/external_benchmark_runner.py --dry-run
```

Models are discovered from the current Hugging Face cache refs each time, and `mmproj` files are excluded. By default, all discovered standalone GGUF models are included. To select only one model:

```bash
rtk python3 scripts/external_benchmark_runner.py --model "K2-Horizon-0.9B-Q4_K_M.gguf" --dry-run
```

## Run all models

```bash
rtk python3 scripts/external_benchmark_runner.py
```

The runner shows the complete plan and asks before starting. It runs speed first, then starts one local `llama-server` for the model and runs the three API-based suites sequentially. It stops the server before loading the next model. Logs stream to the terminal and are saved with each tool's native results. Successful tool/model pairs can be skipped after interruption with `--resume` and the original output path:

```bash
rtk python3 scripts/external_benchmark_runner.py --resume --output results/external-four-suite/RUN_FOLDER
```

You can override the size of the bounded samples with `--evalplus-tasks 20` or `--hellaswag-limit 100`. Larger values take longer. A single-model pilot is a good way to update the time estimate before running the remaining models.

For the full 164-task EvalPlus run, select one model at a time and set a task
timeout. The default is 300 seconds per generated answer:

```bash
rtk python3 scripts/external_benchmark_runner.py \
  --model "HuggingFaceTB_SmolLM3-3B-IQ4_XS.gguf" \
  --tool evalplus --evalplus-tasks 164 \
  --evalplus-task-timeout 300 \
  --output results/external-four-suite/evalplus-164-all-models --resume
```

If a generation exceeds the limit or fails, the runner records an empty failed
sample and the reason in `<model>/evalplus/generation_failures.jsonl`, restarts
`llama-server`, and continues to the next task. Skipped answers remain in the
score as failures, so tasks are not silently removed. Completed task samples
are reused when resuming. You can change the limit with
`--evalplus-task-timeout SECONDS`. Reasoning is disabled consistently for this
benchmark; empty model responses are recorded as failed tasks instead of being
accepted as generated answers.

## Result folders

Each run has a `run.json` and `summary.json`, then one folder per model and one subfolder per tool:

```text
results/external-four-suite/<run>/
  run.json
  summary.json
  <model>/
    model.json
    llama-server.log
    llama-bench/status.json
    llama-bench/llama-bench.csv
    evalplus/status.json
    evalplus/generate.log
    evalplus/score-sandboxed.log
    llm-benchmark/status.json
    llm-benchmark/results/
    lm-eval/status.json
    lm-eval/results.json
```

`status.json` records success or failure independently for each tool. The runner streams logs to the screen as well as saving them.

## EvalPlus safety requirement

EvalPlus executes generated Python code. The runner refuses to score these outputs unless the Docker daemon is accessible. On the first run, it builds an evaluation image from the pinned EvalPlus source revision. The evaluation container has no network, is read-only except for that model's result folder and temporary files, and has CPU, memory, and process limits. Do not enable an unsandboxed fallback.

## Rough runtime

The actual time depends heavily on each model's generation speed. A preliminary estimate is around **20–60 minutes per model**, or roughly **3–10 hours for all ten**, plus initial setup and the first HellaSwag data download. This is an estimate, not a guarantee; the first model run will provide the useful measured rate. The 10/50 default samples keep the full pass bounded while preserving comparable prompts and settings.
