# Laptop Model Bench

This repository contains two things: the frozen Laptop Model Bench benchmark suite, and a small Python launcher for comparing local models on self-contained browser-app prompts. The launcher runs one prompt with `llama-cli`, saves the full response and timing log, and saves HTML output when the model produces it.

## Quick start

You need Python 3.10 or newer, a local GGUF model, and a working `llama-cli` executable. The launcher uses Python's standard library only; it does not install packages or download models.

From Linux or macOS:

```bash
git clone --branch v1.2 https://github.com/khad123/laptop-model-bench.git
cd laptop-model-bench
python3 scripts/local_app_benchmark.py
```

From Windows PowerShell:

```powershell
git clone --branch v1.2 https://github.com/khad123/laptop-model-bench.git
Set-Location laptop-model-bench
py -3 .\scripts\local_app_benchmark.py
```

Choose **Normal** or **ECC**, then choose an installed model and prompt. To run non-interactively or use a model file outside the Hugging Face cache, pass `--model` and `--task` as shown below.

## Windows setup with an NVIDIA GPU

For an RTX 3060, use a CUDA-enabled Windows x64 build of `llama.cpp`:

1. Install Git for Windows and Python 3.10+ (enable the Python launcher during installation).
2. Download a current Windows x64 **CUDA 12** build and its matching CUDA DLL archive from the [official llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases). Extract both archives so the required DLLs are available beside the executables. A Windows x64 CPU build also works, but will not use the 3060.
3. Put a GGUF model file on the desktop PC. Model files are not included in this GitHub repository.
4. From the repository folder, launch one model and prompt. Replace the paths with the locations on your PC:

```powershell
$LlamaCli = "C:\AI\llama.cpp\llama-cli.exe"
$Model = "D:\Models\Qwen_Qwen3.5-2B-Q4_K_M.gguf"

py -3 .\scripts\local_app_benchmark.py `
  --llama-cli $LlamaCli `
  --model $Model `
  --task pocket-courier `
  --mode normal `
  --gpu-layers all
```

The defaults remain **32,768 context tokens**, **8,192 output tokens**, **4 CPU threads**, temperature 0, and seed 42. `--gpu-layers all` asks llama.cpp to offload as many layers as it can; if the model does not fit in VRAM, use a number such as `--gpu-layers 20`, or omit the option to run CPU-only. Check CUDA/GPU detection in PowerShell with `& $LlamaCli --list-devices`.

## Linux desktop setup with an NVIDIA GPU

On Ubuntu x64, the [official llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) provide Ubuntu CUDA builds and matching CUDA libraries. Download a matching CUDA 12 build/library pair, extract them, and point the launcher to its `llama-cli` binary. Alternatively, build from source using the [official CUDA build instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md). Then, from this repository:

```bash
python3 scripts/local_app_benchmark.py \
  --llama-cli "$HOME/Models/llama.cpp/build/bin/llama-cli" \
  --model "$HOME/Models/example.gguf" \
  --task pocket-courier --mode normal --gpu-layers all
```

Use `--list-devices` with the selected binary to check whether it sees the GPU. For other Linux distributions, use a compatible build or follow llama.cpp's source-build instructions.

## Compare baseline with DRY

DRY is off by default. To make a controlled comparison, run the same model and prompt twice with the same settings. The first run is the baseline; add `--dry-multiplier 0.8` only to the second run:

```powershell
$Common = @(
  "--llama-cli", $LlamaCli,
  "--model", $Model,
  "--task", "pocket-courier",
  "--mode", "normal",
  "--gpu-layers", "all",
  "--run-root", ".\results\desktop-dry-comparison"
)

py -3 .\scripts\local_app_benchmark.py @Common
py -3 .\scripts\local_app_benchmark.py @Common --dry-multiplier 0.8
```

The shared run folder keeps the pair together. Context, output limit, temperature, and seed stay unchanged; the only difference is DRY. The second run may be saved in an `attempt-*` subfolder to avoid overwriting the first.

On Linux or macOS, use the same flags with `python3` and POSIX paths. Set `--gpu-layers all` only with a GPU-enabled build; use `0` for the CPU-only baseline:

```bash
python3 scripts/local_app_benchmark.py \
  --llama-cli "$HOME/Models/llama.cpp/build/bin/llama-cli" \
  --model "$HOME/Models/example.gguf" \
  --task pocket-courier --mode normal --gpu-layers 0

python3 scripts/local_app_benchmark.py \
  --llama-cli "$HOME/Models/llama.cpp/build/bin/llama-cli" \
  --model "$HOME/Models/example.gguf" \
  --task pocket-courier --mode normal --gpu-layers 0 --dry-multiplier 0.8
```

## Prompts

The prompt pack is [`tasks/local-app-prompts.md`](tasks/local-app-prompts.md). It contains 14 standalone prompts:

- Games: Pocket Dodge, Switchyard, Workshop Queue, Tower Defense, Fuel Stop, Pocket Courier, Sudoku, Tic-Tac-Toe.
- Apps: Soundboard Studio, Budget Tracker, Kanban Board, Study Cards, E-commerce Store, Movie Catalog.

Select a prompt by its ID, for example `--task pocket-courier` or `--task budget-tracker`. Each asks for one self-contained HTML document. Normal mode is the prompt-only baseline. ECC mode prepends selected frontend and accessibility guidance; it remains one-shot generation and does not give the model tools to edit files or run tests.

ECC is optional. To install the guidance checkout in the default location on Windows, run `git clone https://github.com/affaan-m/ECC.git "$HOME\Models\ECC"` in PowerShell; on Linux/macOS use `git clone https://github.com/affaan-m/ECC.git "$HOME/Models/ECC"`. Then select ECC in the menu or pass `--mode ecc` (and `--ecc-dir PATH` if it is elsewhere).

## Results

Runs are saved under `results/` unless `--run-root` is specified. Each run folder contains the prompt, `response.txt`, the llama.cpp transcript and log, and `run-metadata.json`. HTML output is saved as a project/model/mode-named `.html` file, including partial output. `index.html` is written only when the output has a closing HTML tag. A completed run means `llama-cli` exited successfully; it does not mean the generated app is complete or playable.

## Four-tool model comparison

To compare all installed GGUF models with `llama-bench`, EvalPlus, `llm-benchmark`, and EleutherAI's `lm-evaluation-harness`, install the pinned tools and use the sequential runner:

```bash
rtk bash scripts/setup_external_benchmarks.sh
rtk python3 scripts/external_benchmark_runner.py --dry-run
rtk python3 scripts/external_benchmark_runner.py
```

The runner uses bounded, fixed samples and saves results under `results/external-four-suite/`. It checks the current Hugging Face cache each time and loads models one by one. EvalPlus requires Docker to safely evaluate generated code. See [`docs/EXTERNAL_BENCHMARKS.md`](docs/EXTERNAL_BENCHMARKS.md) for exact coverage, settings, resume and model-selection options, result paths, and runtime estimates.

## Useful options

```text
--model PATH             Use a specific GGUF file
--task ID                Select a saved prompt
--mode normal|ecc        Select the run mode
--llama-cli PATH         Select llama-cli (use llama-cli.exe on Windows)
--context N              Context size; default 32768
--max-tokens N           Output cap; default 8192
--threads N              CPU threads; default 4
--gpu-layers N|auto|all  GPU layers; default 0 (CPU-only)
--dry-multiplier N       Optional DRY repetition control; default 0 (off)
--timeout-minutes N      Override the prompt's time limit
--run-root PATH          Put repeated runs under a shared folder
```

See [`docs/LOCAL_APP_PYTHON_LAUNCHER.md`](docs/LOCAL_APP_PYTHON_LAUNCHER.md) for menu navigation, ECC setup, and saved-file details. The original benchmark phases and results are documented in the `docs/` directory; the main benchmark entry points are `bench.sh`, `capability.sh`, `coding.sh`, `miniswe.sh`, `instruction.sh`, `agent.sh`, and `context.sh`.
