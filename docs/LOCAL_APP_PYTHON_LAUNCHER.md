# Local app benchmark: Python launcher

The launcher runs the selected prompt with the existing `llama-cli` binary. It
uses only Python's standard library and does not download models or install
packages.

## Start a run

From the `laptop-model-bench` folder:

```bash
python3 scripts/local_app_benchmark.py
```

Choose one installed GGUF and one project prompt from the menus. Before it
starts, the launcher shows the model, prompt, context, thread count, reasoning
mode, output limit, time limit, and save folder. Confirm with Enter. Each run
starts a fresh `llama-cli` process and receives only that one prompt.

The defaults are CPU-only, 4 threads, 32,768 context tokens, 8,192 maximum
generated tokens, temperature 0, seed 42, and reasoning off. The prompt and
generated output share the context window. Earlier load checks established
16,384 tokens for the model pool; run a common 32K load preflight across all
models before treating 32K results as a scored comparison. If a model cannot
load or a prompt does not fit, its failed/partial run is still recorded.

Task time limits default to 10 minutes for Pocket Dodge, 15 for Switchyard, 15
for Workshop Queue, 25 for Tower Defense, 30 for Fuel Stop, and 20 for Pocket
Courier. A timeout keeps the available partial output.

## Optional settings

The model and task can also be passed directly:

```bash
python3 scripts/local_app_benchmark.py --task pocket-dodge --model /path/to/model.gguf
```

To put several runs under one shared results folder, pass the same
`--run-root` each time:

```bash
python3 scripts/local_app_benchmark.py --run-root results/local-app-benchmark-32k
```

Useful adjustments include `--context 16384`, `--threads 4`, `--max-tokens
8192`, `--timeout-minutes 10`, `--reasoning off`, and `--llama-cli
/path/to/llama-cli`. `LLAMA_CLI` can also point to the binary. Use reasoning on
only for a separately labeled diagnostic run; it changes the benchmark setting.
The launcher displays any reasoning text the model/runtime actually emits. It
cannot expose hidden internal reasoning.

## Saved files

Runs are written under `results/` by default. Each model/project folder contains
the exact prompt copy, llama.cpp output transcript, complete terminal log, run
metadata, and response. If the response is a complete HTML document, the
launcher also creates `index.html`; if it has only outer Markdown fences, it
removes those fences in the launch copy and records that extraction in the
metadata. It never repairs or fills in model output.

The final screen reports prompt and generation speed, token counts, and
estimated context use when the selected llama.cpp build emits parseable timing
details. The prompt token count shown before generation is only a rough estimate;
runtime timing output is the source for the final figures. If the build changes
its timing format, the files are still saved and those numbers are marked as
unavailable rather than guessed.
