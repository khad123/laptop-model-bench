#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from runtime_metrics import (
    ResourceSampler,
    summarize_repeats,
    system_memory_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REGISTRY = ROOT / "docs" / "MODEL_REGISTRY_V12.md"
DEFAULT_RESULTS = ROOT / "results" / "v12"

DEFAULT_THREADS = 4
DEFAULT_CONTEXT = 8192
DEFAULT_REPEATS = 3
DEFAULT_N_PREDICT = 128

PROMPT_WORDS = {
    "short": 128,
    "medium": 1024,
    "long": 4096,
}


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def hf_cache_default() -> Path:
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"]).expanduser()

    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]).expanduser() / "hub"

    return Path.home() / ".cache" / "huggingface" / "hub"


def parse_registry(path: Path) -> list[dict]:
    rows = []
    section = None

    for raw in path.read_text().splitlines():
        line = raw.strip()

        if line.startswith("## "):
            if line == "## Primary v1 capability pool":
                section = "primary"
            elif line == "## Optional reference models":
                section = "reference"
            else:
                section = None
            continue

        if section is None or not line.startswith("|"):
            continue

        cells = [
            c.strip().strip("`")
            for c in line.strip("|").split("|")
        ]

        if not cells or cells[0] == "ID":
            continue

        if all(
            re.fullmatch(r":?-{3,}:?", c.replace(" ", ""))
            for c in cells
        ):
            continue

        if len(cells) < 6:
            continue

        model_id, model, repo, quant, local_size, role = cells[:6]

        rows.append(
            {
                "id": model_id,
                "model": model,
                "repository": repo,
                "quant": quant,
                "registry_size": local_size,
                "role": role,
                "group": section,
            }
        )

    if not rows:
        raise RuntimeError(f"No model rows found in {path}")

    return rows


def snapshot_dirs(model_root: Path) -> list[Path]:
    snapshots = model_root / "snapshots"

    if not snapshots.is_dir():
        return []

    result = []

    main_ref = model_root / "refs" / "main"

    if main_ref.is_file():
        candidate = snapshots / main_ref.read_text().strip()

        if candidate.is_dir():
            result.append(candidate)

    others = [
        p for p in snapshots.iterdir()
        if p.is_dir() and p not in result
    ]

    others.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return result + others


def resolve_model(
    row: dict,
    hf_cache: Path,
) -> tuple[Path, int, str]:
    repo_root = (
        hf_cache
        / f"models--{row['repository'].replace('/', '--')}"
    )

    if not repo_root.is_dir():
        raise FileNotFoundError(
            f"HF repo cache missing: {repo_root}"
        )

    quant = row["quant"].upper()

    for snapshot in snapshot_dirs(repo_root):
        matches = []

        for path in snapshot.rglob("*.gguf"):
            name = path.name.upper()

            if (
                path.is_file()
                and quant in name
                and "MMPROJ" not in name
                and "PROJECTOR" not in name
            ):
                matches.append(path)

        unique = {}

        for path in matches:
            try:
                key = path.resolve(strict=True)
            except OSError:
                key = path.absolute()

            unique.setdefault(key, path)

        if len(unique) == 1:
            path = next(iter(unique.values()))

            return (
                path,
                path.stat().st_size,
                snapshot.name,
            )

        if len(unique) > 1:
            names = ", ".join(
                sorted(p.name for p in unique.values())
            )

            raise RuntimeError(
                f"Ambiguous GGUFs for {row['id']}: {names}"
            )

    raise FileNotFoundError(
        f"No {row['quant']} GGUF found for {row['id']}"
    )


def free_port() -> int:
    sock = socket.socket()

    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def http_json(
    url: str,
    payload: dict | None = None,
    timeout: float = 5.0,
):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
    )

    with urllib.request.urlopen(
        req,
        timeout=timeout,
    ) as response:
        return json.loads(response.read())


def wait_for_server(
    proc: subprocess.Popen,
    port: int,
    timeout_s: float,
) -> float:
    started = time.perf_counter()

    while True:
        if proc.poll() is not None:
            raise RuntimeError(
                f"llama-server exited early with "
                f"code {proc.returncode}"
            )

        try:
            http_json(
                f"http://127.0.0.1:{port}/health",
                timeout=1.0,
            )

            return time.perf_counter() - started

        except Exception:
            pass

        if time.perf_counter() - started > timeout_s:
            raise TimeoutError(
                f"llama-server did not become ready "
                f"within {timeout_s:.0f}s"
            )

        time.sleep(0.25)


def make_prompt(
    profile: str,
    run_number: int,
) -> str:
    word_count = PROMPT_WORDS[profile]

    block = (
        "alpha beta gamma delta epsilon zeta eta theta "
        "iota kappa lambda mu nu xi omicron pi rho sigma "
        "tau upsilon phi chi psi omega "
    )

    words = (block * ((word_count // 24) + 2)).split()
    payload = " ".join(words[:word_count])

    return (
        "Performance measurement input. "
        "Process all text before continuing.\n\n"
        f"{payload}\n\n"
        f"Run marker: {profile}-{run_number}\n"
        "Continue with arbitrary text."
    )


def timing_rate(
    timing: dict,
    prefix: str,
) -> float | None:
    direct = timing.get(f"{prefix}_per_second")

    if direct is not None:
        try:
            return float(direct)
        except (TypeError, ValueError):
            pass

    count = timing.get(f"{prefix}_n")
    ms = timing.get(f"{prefix}_ms")

    try:
        count = float(count)
        ms = float(ms)

        if ms > 0:
            return count / (ms / 1000.0)

    except (TypeError, ValueError):
        pass

    return None


def completion_stream(
    port: int,
    prompt: str,
    n_predict: int,
    timeout_s: float,
) -> dict:
    payload = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.0,
        "seed": 1,
        "stream": True,
        "cache_prompt": False,
        "ignore_eos": True,
    }

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/completion",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    started = time.perf_counter()

    first_token_s = None
    chunks = 0
    text_parts = []
    final_event = None
    timings = {}

    with urllib.request.urlopen(
        req,
        timeout=timeout_s,
    ) as response:
        for raw in response:
            line = raw.decode(
                "utf-8",
                errors="replace",
            ).strip()

            if not line:
                continue

            if line.startswith("data:"):
                line = line[5:].strip()

            if line == "[DONE]":
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            content = event.get("content")

            if content:
                if first_token_s is None:
                    first_token_s = (
                        time.perf_counter() - started
                    )

                text_parts.append(content)
                chunks += 1

            if event.get("timings"):
                timings = event["timings"]

            if event.get("stop") is True:
                final_event = event

    wall_s = time.perf_counter() - started

    if final_event and final_event.get("timings"):
        timings = final_event["timings"]

    pp = timing_rate(timings, "prompt")
    tg = timing_rate(timings, "predicted")

    predicted_n = timings.get("predicted_n")
    prompt_n = timings.get("prompt_n")

    # Fallback TG if this llama.cpp build does not expose timings.
    if tg is None and first_token_s is not None:
        generation_time = wall_s - first_token_s

        try:
            predicted = float(predicted_n or n_predict)

            if generation_time > 0:
                tg = predicted / generation_time
        except (TypeError, ValueError):
            pass

    return {
        "ttft_seconds": (
            round(first_token_s, 6)
            if first_token_s is not None else None
        ),
        "wall_seconds": round(wall_s, 6),

        "prompt_tokens": prompt_n,
        "predicted_tokens": predicted_n,

        "pp_tokens_per_s": (
            round(pp, 6)
            if pp is not None else None
        ),
        "tg_tokens_per_s": (
            round(tg, 6)
            if tg is not None else None
        ),

        "stream_chunks": chunks,
        "timings": timings,

        # Keep only a small preview.
        "output_preview": "".join(text_parts)[:500],
    }


def git_commit(path: Path) -> str | None:
    try:
        p = subprocess.run(
            [
                "git",
                "-C",
                str(path),
                "rev-parse",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if p.returncode == 0:
            return p.stdout.strip()

    except Exception:
        pass

    return None


def aggregate_model(rows: list[dict]) -> dict:
    output = {}

    metrics = [
        "ttft_seconds",
        "wall_seconds",
        "pp_tokens_per_s",
        "tg_tokens_per_s",
        "peak_process_rss_gib",
        "peak_system_ram_delta_gib",
        "swap_growth_gib",
        "avg_cpu_percent",
    ]

    for profile in PROMPT_WORDS:
        subset = [
            x for x in rows
            if x["profile"] == profile
            and x["status"] == "ok"
        ]

        result = {
            "successful_runs": len(subset),
        }

        for metric in metrics:
            vals = [
                float(x[metric])
                for x in subset
                if x.get(metric) is not None
            ]

            result[metric] = summarize_repeats(vals)

        output[profile] = result

    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Laptop Model Bench v1.2 Phase 1"
    )

    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
    )

    llama_cpp = Path(
        os.environ.get(
            "LLAMA_CPP_DIR",
            str(Path.home() / "Models/llama.cpp-k2"),
        )
    ).expanduser()

    parser.add_argument(
        "--llama-server",
        default=str(
            llama_cpp / "build/bin/llama-server"
        ),
    )

    parser.add_argument(
        "--hf-cache",
        default=str(hf_cache_default()),
    )

    parser.add_argument(
        "--results-dir",
        default=str(DEFAULT_RESULTS),
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=DEFAULT_THREADS,
    )

    parser.add_argument(
        "--context",
        type=int,
        default=DEFAULT_CONTEXT,
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=DEFAULT_REPEATS,
    )

    parser.add_argument(
        "--n-predict",
        type=int,
        default=DEFAULT_N_PREDICT,
    )

    parser.add_argument(
        "--profiles",
        default="short,medium,long",
    )

    parser.add_argument(
        "--only",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--include-reference",
        action="store_true",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=180.0,
    )

    parser.add_argument(
        "--request-timeout",
        type=float,
        default=900.0,
    )

    args = parser.parse_args()

    registry = Path(args.registry).resolve()
    server_bin = Path(args.llama_server).expanduser().resolve()
    hf_cache = Path(args.hf_cache).expanduser().resolve()
    results_dir = Path(args.results_dir).resolve()

    profiles = [
        x.strip()
        for x in args.profiles.split(",")
        if x.strip()
    ]

    unknown_profiles = [
        p for p in profiles
        if p not in PROMPT_WORDS
    ]

    if unknown_profiles:
        parser.error(
            "unknown profile(s): "
            + ", ".join(unknown_profiles)
        )

    entries = parse_registry(registry)

    if not args.include_reference:
        entries = [
            e for e in entries
            if e["group"] == "primary"
        ]

    if args.only:
        wanted = set(args.only)

        known = {e["id"] for e in entries}

        missing = wanted - known

        if missing:
            parser.error(
                "unknown model IDs: "
                + ", ".join(sorted(missing))
            )

        entries = [
            e for e in entries
            if e["id"] in wanted
        ]

    if not args.dry_run:
        if not (
            server_bin.is_file()
            and os.access(server_bin, os.X_OK)
        ):
            parser.error(
                f"llama-server not executable: "
                f"{server_bin}"
            )

    run_id = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    raw_dir = (
        results_dir
        / "raw"
        / f"phase1-{run_id}"
    )

    summary_dir = results_dir / "phase1"

    raw_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    resolved = []

    print(f"v1.2 Phase 1 run: {run_id}")
    print(f"Models: {len(entries)}")
    print(f"Profiles: {', '.join(profiles)}")
    print(f"Repeats: {args.repeats}")
    print(f"Threads: {args.threads}")
    print(f"Context: {args.context}")
    print()

    for entry in entries:
        try:
            path, size, snapshot = resolve_model(
                entry,
                hf_cache,
            )

            item = dict(entry)
            item.update(
                {
                    "model_path": str(path),
                    "model_size_bytes": size,
                    "model_size_gib": round(
                        size / 1024**3,
                        6,
                    ),
                    "hf_snapshot": snapshot,
                }
            )

            resolved.append(item)

            print(
                f"[resolved] {entry['id']}\n"
                f"  {path}\n"
                f"  {size / 1024**3:.3f} GiB"
            )

        except Exception as exc:
            print(
                f"[FAILED] {entry['id']}: {exc}",
                file=sys.stderr,
            )

            return 2

    if args.dry_run:
        print()
        print(
            f"DRY RUN PASS: "
            f"{len(resolved)} models resolved."
        )

        return 0

    all_rows = []
    model_summaries = {}

    for model_index, entry in enumerate(
        resolved,
        1,
    ):
        print()
        print(
            f"=== [{model_index}/{len(resolved)}] "
            f"{entry['id']} ==="
        )

        port = free_port()

        stdout_file = (
            raw_dir
            / f"{entry['id']}.server.stdout.log"
        )

        stderr_file = (
            raw_dir
            / f"{entry['id']}.server.stderr.log"
        )

        command = [
            str(server_bin),
            "-m",
            entry["model_path"],
            "-t",
            str(args.threads),
            "-ngl",
            "0",
            "-c",
            str(args.context),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]

        print(
            "Starting llama-server..."
        )

        out_handle = stdout_file.open("wb")
        err_handle = stderr_file.open("wb")

        startup_before = system_memory_snapshot()

        proc = subprocess.Popen(
            command,
            stdout=out_handle,
            stderr=err_handle,
            env={
                **os.environ,
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "LC_ALL": "C",
            },
        )

        startup_sampler = ResourceSampler(
            proc.pid,
            interval_s=0.10,
        )
        startup_sampler.start()

        try:
            startup_s = wait_for_server(
                proc,
                port,
                args.startup_timeout,
            )

            startup_metrics = startup_sampler.stop()

            startup_peak_ram = (
                startup_metrics.get("peak_system_ram_used_bytes")
                or startup_before["ram_used_bytes"]
            )

            startup_ram_delta = max(
                0,
                startup_peak_ram - startup_before["ram_used_bytes"],
            )

            startup_peak_swap = (
                startup_metrics.get("peak_swap_used_bytes")
                or startup_before["swap_used_bytes"]
            )

            startup_swap_growth = max(
                0,
                startup_peak_swap - startup_before["swap_used_bytes"],
            )

            startup_summary = {
                "server_startup_seconds": round(startup_s, 6),
                "startup_peak_process_rss_gib":
                    startup_metrics["peak_process_rss_gib"],
                "startup_peak_system_ram_used_gib":
                    startup_metrics["peak_system_ram_used_gib"],
                "startup_system_ram_delta_gib":
                    round(startup_ram_delta / 1024**3, 6),
                "startup_peak_swap_used_gib":
                    startup_metrics["peak_swap_used_gib"],
                "startup_swap_growth_gib":
                    round(startup_swap_growth / 1024**3, 6),
                "startup_avg_cpu_percent":
                    startup_metrics["avg_cpu_percent"],
            }

            print(
                f"Server ready in {startup_s:.2f}s "
                f"| load RSS="
                f"{startup_summary['startup_peak_process_rss_gib']:.2f}GiB "
                f"| RAM Δ="
                f"{startup_summary['startup_system_ram_delta_gib']:.2f}GiB "
                f"| swap Δ="
                f"{startup_summary['startup_swap_growth_gib']:.2f}GiB"
            )

            for profile in profiles:
                print()
                print(
                    f"  Profile: {profile} "
                    f"({PROMPT_WORDS[profile]} words)"
                )

                for repeat in range(
                    1,
                    args.repeats + 1,
                ):
                    prompt = make_prompt(
                        profile,
                        repeat,
                    )

                    before = system_memory_snapshot()

                    sampler = ResourceSampler(
                        proc.pid,
                        interval_s=0.10,
                    )

                    sampler.start()

                    error = None
                    metrics = None

                    try:
                        metrics = completion_stream(
                            port,
                            prompt,
                            args.n_predict,
                            args.request_timeout,
                        )

                    except Exception as exc:
                        error = (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        )

                    sampled = sampler.stop()

                    after = system_memory_snapshot()

                    start_ram = sampled.get(
                        "system_ram_used_start_bytes"
                    ) or before["ram_used_bytes"]

                    peak_ram = sampled.get(
                        "peak_system_ram_used_bytes"
                    ) or start_ram

                    peak_delta = max(
                        0,
                        peak_ram - start_ram,
                    )

                    swap_start = sampled.get(
                        "swap_used_start_bytes"
                    )

                    if swap_start is None:
                        swap_start = before[
                            "swap_used_bytes"
                        ]

                    swap_peak = sampled.get(
                        "peak_swap_used_bytes"
                    ) or swap_start

                    swap_growth = max(
                        0,
                        swap_peak - swap_start,
                    )

                    row = {
                        "run_id": run_id,
                        "model_id": entry["id"],
                        "model": entry["model"],
                        "quant": entry["quant"],
                        "model_size_gib":
                            entry["model_size_gib"],
                        "profile": profile,
                        "requested_words":
                            PROMPT_WORDS[profile],
                        "repeat": repeat,
                        "status": (
                            "failed"
                            if error else "ok"
                        ),
                        "error": error,
                        **startup_summary,
                        "threads": args.threads,
                        "context": args.context,
                        "n_predict":
                            args.n_predict,
                        **sampled,
                        "peak_system_ram_delta_gib":
                            round(
                                peak_delta / 1024**3,
                                6,
                            ),
                        "swap_growth_gib":
                            round(
                                swap_growth / 1024**3,
                                6,
                            ),
                        "system_ram_after_gib":
                            round(
                                after["ram_used_bytes"]
                                / 1024**3,
                                6,
                            ),
                        "swap_after_gib":
                            round(
                                after["swap_used_bytes"]
                                / 1024**3,
                                6,
                            ),
                    }

                    if metrics:
                        row.update(metrics)

                    all_rows.append(row)

                    raw_request = (
                        raw_dir
                        / (
                            f"{entry['id']}."
                            f"{profile}.r{repeat}.json"
                        )
                    )

                    raw_request.write_text(
                        json.dumps(
                            row,
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n"
                    )

                    if error:
                        print(
                            f"    run {repeat}: "
                            f"FAILED: {error}"
                        )
                    else:
                        print(
                            f"    run {repeat}: "
                            f"TTFT={row['ttft_seconds']:.2f}s "
                            f"wall={row['wall_seconds']:.2f}s "
                            f"PP={row.get('pp_tokens_per_s')} "
                            f"TG={row.get('tg_tokens_per_s')} "
                            f"RSS={row['peak_process_rss_gib']:.2f}GiB"
                        )

            model_rows = [
                x for x in all_rows
                if x["model_id"] == entry["id"]
            ]

            model_summaries[
                entry["id"]
            ] = aggregate_model(model_rows)

        finally:
            if (
                "startup_sampler" in locals()
                and startup_sampler._thread is not None
                and startup_sampler.finished_perf is None
            ):
                try:
                    startup_sampler.stop()
                except Exception:
                    pass

            print("Stopping llama-server...")

            if proc.poll() is None:
                proc.terminate()

                try:
                    proc.wait(timeout=15)

                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)

            out_handle.close()
            err_handle.close()

    payload = {
        "schema_version": "phase1.v12-dev",
        "run": {
            "run_id": run_id,
            "started_at_utc": utc_now(),
            "registry": str(registry),
            "llama_server": str(server_bin),
            "llama_cpp_commit":
                git_commit(llama_cpp),
            "threads": args.threads,
            "context": args.context,
            "repeats": args.repeats,
            "n_predict": args.n_predict,
            "profiles": {
                p: PROMPT_WORDS[p]
                for p in profiles
            },
        },
        "models": resolved,
        "results": all_rows,
        "summary": model_summaries,
    }

    out_file = (
        summary_dir
        / f"phase1-v12-{run_id}.json"
    )

    out_file.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    latest = (
        summary_dir
        / "phase1-v12-latest.json"
    )

    latest.write_text(out_file.read_text())

    print()
    print("Phase 1 complete.")
    print(f"Summary: {out_file}")
    print(f"Raw:     {raw_dir}")

    failures = [
        r for r in all_rows
        if r["status"] != "ok"
    ]

    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
