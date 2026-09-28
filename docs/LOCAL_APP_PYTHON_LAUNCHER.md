# Local app benchmark: Python launcher

The launcher runs the selected prompt with an existing `llama-cli` binary. It
uses only Python's standard library and does not download models or install
packages. It runs on Linux, macOS, and Windows; on Windows, pass the path to
`llama-cli.exe` with `--llama-cli`.

## Start a run

From the repository folder, start it with:

```bash
python3 scripts/local_app_benchmark.py
```

On Windows PowerShell, use `py -3 .\scripts\local_app_benchmark.py`. The
repository README has installation steps for Linux and Windows.

Choose **Normal** or **ECC**, then select one installed GGUF and one project
prompt. Before starting, the launcher shows the model, prompt, context, thread
count, reasoning mode, output limit, time limit, and save folder. Confirm with
Enter. Normal mode preserves the prompt-only baseline. ECC mode adds the two
selected ECC skill documents to the project prompt for one-shot guidance.
In the interactive menus, enter `0` to go back one selection step (project →
model → run mode); enter `q` to quit.

ECC mode reads these skills from `~/Models/ECC` by default:

- `frontend-design-direction`
- `accessibility`

It records the ECC commit and skill names in `run-metadata.json`. Set `ECC_DIR`
or pass `--ecc-dir` to use a different checkout. Refresh the checkout with
`git -C ~/Models/ECC pull`.
On Windows, the default location is `%USERPROFILE%\Models\ECC`; clone the ECC
repository there or pass its location with `--ecc-dir`.

ECC mode is guided generation, not an autonomous coding agent: it does not give
`llama-cli` file-editing or test-running tools. The added skills consume context,
so the launcher shows a larger prompt-token estimate. Normal and ECC runs use
separate timestamped result roots.

The defaults are CPU-only, 4 threads, 32,768 context tokens, 8,192 maximum
generated tokens, temperature 0, seed 42, reasoning off, and DRY disabled. The prompt and
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

Use `--mode normal` or `--mode ecc` to select a mode without the mode menu.
Non-interactive calls default to Normal unless `--mode ecc` is provided.

To put several runs under one shared results folder, pass the same
`--run-root` each time:

```bash
python3 scripts/local_app_benchmark.py --run-root results/local-app-benchmark-32k
```

Useful adjustments include `--context 16384`, `--threads 4`, `--max-tokens
8192`, `--timeout-minutes 10`, `--reasoning off`, and `--llama-cli
/path/to/llama-cli`. `LLAMA_CLI` can also point to the binary. `--gpu-layers`
accepts `0`, a number, `auto`, or `all`; its default is `0` to preserve the
CPU-only baseline. For example, use `--gpu-layers all` with a CUDA-enabled
llama.cpp build on a Windows NVIDIA desktop. The launcher does not install the
GPU backend or its runtime libraries.

`--dry-multiplier 0.8` opts into llama.cpp's DRY repeated-sequence sampler; the
default `0` leaves it disabled. For a controlled baseline comparison, repeat
the same model, prompt, context, output cap, temperature, and seed, adding only
this flag to the DRY run. A penalty can reduce some repetition, but it cannot
guarantee that a small model will finish a large app. The launcher displays any
reasoning text the model/runtime actually emits; it cannot expose hidden
internal reasoning.

## Saved files

Runs are written under `results/` by default. Each model/project folder contains
the exact prompt copy, llama.cpp output transcript, complete terminal log, run
metadata, and response. If the response is an HTML document, the
launcher creates `index.html` and a named copy such as
`pocket-courier--smollm3-3b-iq4-xs--ecc.html`. The named file identifies the
project, model, and mode. HTML output that starts correctly but is cut off is
also saved under that name and marked `partial-html-copy`; only complete
documents receive `index.html`. An outer Markdown HTML fence is removed from
the browser-ready copy, while the original assistant response remains in
`response.txt`. The launcher never repairs or fills in model output.

`complete-html-copy` currently means the generated text starts like HTML and
ends with `</html>`; it does not mean the app's JavaScript works or that the
project requirements were met. Review the saved file before treating the
project as complete.

The final screen reports prompt and generation speed, token counts, and
estimated context use when the selected llama.cpp build emits parseable timing
details. The prompt token count shown before generation is only a rough estimate;
runtime timing output is the source for the final figures. If the build changes
its timing format, the files are still saved and those numbers are marked as
unavailable rather than guessed.
