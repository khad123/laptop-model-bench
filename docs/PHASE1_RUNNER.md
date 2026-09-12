# Phase 1 speed / efficiency runner

`./bench.sh` is the Phase 1 automation entry point. It reads the frozen v1 tables in `docs/MODEL_REGISTRY.md` and benchmarks each primary and quant-comparison entry one at a time.

## Official default profile

- Runtime: local `llama-bench` from `~/Models/llama.cpp-k2/build/bin/llama-bench`
- CPU threads: `4`
- GPU layers: `0` (CPU-only)
- Prompt-processing test: `512` tokens
- Token-generation test: `128` tokens
- Repetitions: `5`
- Protocol context target: `4096` tokens (recorded as protocol metadata; `llama-bench` speed tests use their explicit pp/tg lengths)

The runner passes a local `-m /path/to/model.gguf` path. It never calls the `-hf` downloader. A missing model therefore fails only that registry entry instead of triggering a download.

## First run

Preflight the registry and Hugging Face cache without running inference:

```bash
./bench.sh --dry-run
```

Then run the complete Phase 1 benchmark:

```bash
./bench.sh
```

To rerun only one entry while debugging:

```bash
./bench.sh --only k2-0.9b-q4km
```

Repeat `--only` to select multiple IDs.

If the llama.cpp checkout or binary lives somewhere else:

```bash
LLAMA_BENCH=/path/to/llama-bench LLAMA_CPP_DIR=/path/to/llama.cpp ./bench.sh
```

If the Hugging Face hub cache is non-standard, use `HF_HUB_CACHE` or `--hf-cache`.

## Outputs

Every invocation receives a UTC run ID such as `20260912T120000Z`.

Raw per-model evidence is written under:

```text
results/raw/<run-id>/
```

This includes the untouched `llama-bench` JSON stdout, stderr logs, load-probe output, per-model metadata, and a run manifest. `results/raw/` remains ignored by Git because it is bulky machine-local evidence.

Machine-readable summaries are written as:

```text
results/phase1-<run-id>.json
results/phase1-<run-id>.csv
results/phase1-latest.json
results/phase1-latest.csv
```

The summary records model identity, exact local file size, HF snapshot/blob identity, prompt speed, generation speed, llama.cpp checkout/build metadata, host metadata, wall time, peak RSS, CPU usage, and failure/warning state.

## Peak RAM method

On Linux the runner launches `llama-bench` as a child process and collects that exact child's `ru_maxrss` through `wait4()`. The CSV/JSON field is `peak_rss_kb`, with a derived `peak_rss_gib` value.

This is the benchmark process's peak resident set size, not total system RAM consumption. It is suitable for repeatable same-machine model comparisons and does not require root access or sampling `/proc` in a loop.

## CPU usage method

The same Linux `wait4()` result provides user CPU time (`ru_utime`) and system CPU time (`ru_stime`) for the exact `llama-bench` child process. The runner stores:

- `cpu_user_seconds`
- `cpu_system_seconds`
- `cpu_total_seconds`
- `avg_cpu_percent`
- `cpu_thread_util_percent`

`avg_cpu_percent` follows the common process convention where **100% means one logical CPU fully busy**. A four-thread benchmark can therefore approach 400%.

`cpu_thread_util_percent` divides that value by the configured benchmark thread count. With the standard four-thread profile, 100% means the four allowed benchmark threads were fully occupied on average. This normalized value is useful when comparing how efficiently models keep the fixed four-thread CPU budget busy.

The load probe records matching `load_probe_*` CPU fields separately.

## Load-time probe

After a successful speed run, the runner performs a tiny separate `llama-bench` invocation (`pp=1`, `tg=0`, one repetition). If the installed fork supports it, `--no-warmup` is used. Its process wall time is recorded as `load_probe_wall_seconds`.

This is deliberately named a **load probe**, not a guaranteed cold-load time. Linux filesystem page cache state can change between runs, and dropping caches would require intrusive/root-only behavior. Treat this metric as best-effort startup/load overhead on the current machine state.

Use `--skip-load-probe` to omit it.

## Failure behavior

A missing GGUF, unsupported model, llama.cpp crash, or malformed result is recorded on that model's row. The runner continues through the rest of the registry and returns exit code `2` after finishing if any entry failed.

This makes a partial run auditable without hiding failures or losing successful measurements.
