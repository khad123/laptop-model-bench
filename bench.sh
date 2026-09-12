#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export LMB_ROOT_DIR="$ROOT_DIR"
exec "${PYTHON_BIN:-python3}" - "$@" <<'PY'
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ["LMB_ROOT_DIR"])
THREADS = 4
PP_TOKENS = 512
TG_TOKENS = 128
REPETITIONS = 5
CONTEXT = 4096


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hf_cache_default() -> Path:
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"]).expanduser()
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]).expanduser() / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def parse_registry(path: Path) -> list[dict]:
    section = None
    rows = []
    seen = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            section = {
                "## Primary v1 capability pool": "primary",
                "## Same-base quant comparisons": "quant_comparison",
            }.get(line)
            continue
        if not section or not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if not cells or cells[0] == "ID" or all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
            continue
        if len(cells) < 6:
            continue
        model_id, model, repo, quant, registry_size, tail = cells[:6]
        if model_id in seen:
            raise RuntimeError(f"duplicate registry ID: {model_id}")
        seen.add(model_id)
        rows.append({
            "id": model_id,
            "model": model,
            "repository": repo,
            "quant": quant,
            "registry_size": registry_size,
            "group": section,
            "registry_role": tail if section == "primary" else "",
            "compare_against": tail if section == "quant_comparison" else "",
        })
    if not rows:
        raise RuntimeError(f"no v1 model rows found in {path}")
    return rows


def snapshot_dirs(model_root: Path) -> list[Path]:
    snapshots = model_root / "snapshots"
    if not snapshots.is_dir():
        return []
    result = []
    main_ref = model_root / "refs" / "main"
    if main_ref.is_file():
        snap = snapshots / main_ref.read_text(encoding="utf-8").strip()
        if snap.is_dir():
            result.append(snap)
    others = [p for p in snapshots.iterdir() if p.is_dir() and p not in result]
    others.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return result + others


def resolve_model(row: dict, hf_cache: Path) -> tuple[Path, int, str, str]:
    root = hf_cache / f"models--{row['repository'].replace('/', '--')}"
    if not root.is_dir():
        raise FileNotFoundError(f"HF cache repository missing: {root}")
    target = row["quant"].upper()
    for snap in snapshot_dirs(root):
        matches = []
        for p in snap.rglob("*.gguf"):
            name = p.name.upper()
            if p.is_file() and target in name and "MMPROJ" not in name and "PROJECTOR" not in name:
                matches.append(p)
        if not matches:
            continue
        by_blob = {}
        for p in matches:
            try:
                by_blob.setdefault(p.resolve(strict=True), p)
            except OSError:
                by_blob.setdefault(p.absolute(), p)
        if len(by_blob) != 1:
            raise RuntimeError("ambiguous local GGUFs: " + ", ".join(sorted(p.name for p in matches)))
        path = next(iter(by_blob.values()))
        try:
            blob_id = path.resolve(strict=True).name
        except OSError:
            blob_id = ""
        return path, path.stat().st_size, snap.name, blob_id
    raise FileNotFoundError(f"no local {row['quant']} GGUF under {root / 'snapshots'}")


def run_child(cmd: list[str], stdout_path: Path, stderr_path: Path, threads: int) -> dict:
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env.setdefault("LC_ALL", "C")
    started = time.perf_counter()
    rss_kb = None
    user_s = None
    system_s = None

    with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
        proc = subprocess.Popen(cmd, stdout=out, stderr=err, env=env)
        if hasattr(os, "wait4"):
            _, status, usage = os.wait4(proc.pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
            rss_kb = int(usage.ru_maxrss / 1024) if sys.platform == "darwin" else int(usage.ru_maxrss)
            user_s = float(usage.ru_utime)
            system_s = float(usage.ru_stime)
        else:
            proc.wait()

    wall_s = time.perf_counter() - started
    cpu_total_s = (user_s + system_s) if user_s is not None and system_s is not None else None
    avg_cpu_percent = (cpu_total_s / wall_s * 100.0) if cpu_total_s is not None and wall_s > 0 else None
    thread_util_percent = (avg_cpu_percent / threads) if avg_cpu_percent is not None and threads > 0 else None

    return {
        "exit_code": int(proc.returncode or 0),
        "wall_seconds": round(wall_s, 6),
        "peak_rss_kb": rss_kb,
        "cpu_user_seconds": round(user_s, 6) if user_s is not None else None,
        "cpu_system_seconds": round(system_s, 6) if system_s is not None else None,
        "cpu_total_seconds": round(cpu_total_s, 6) if cpu_total_s is not None else None,
        "avg_cpu_percent": round(avg_cpu_percent, 3) if avg_cpu_percent is not None else None,
        "cpu_thread_util_percent": round(thread_util_percent, 3) if thread_util_percent is not None else None,
    }


def read_bench_json(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        a, b = text.find("["), text.rfind("]")
        if a < 0 or b < a:
            raise
        data = json.loads(text[a:b + 1])
    if isinstance(data, dict):
        data = data.get("results")
    if not isinstance(data, list):
        raise RuntimeError("unexpected llama-bench JSON shape")
    return data


def speed_metrics(rows: list[dict]) -> dict:
    pp = next((r for r in rows if int(r.get("n_prompt", 0) or 0) > 0 and int(r.get("n_gen", 0) or 0) == 0), None)
    tg = next((r for r in rows if int(r.get("n_prompt", 0) or 0) == 0 and int(r.get("n_gen", 0) or 0) > 0), None)
    if not pp or not tg:
        raise RuntimeError("missing prompt-processing or generation result row")
    return {
        "pp_tokens_per_s": pp.get("avg_ts"),
        "pp_stddev_tokens_per_s": pp.get("stddev_ts"),
        "tg_tokens_per_s": tg.get("avg_ts"),
        "tg_stddev_tokens_per_s": tg.get("stddev_ts"),
        "llama_build_commit": pp.get("build_commit") or tg.get("build_commit"),
        "llama_build_number": pp.get("build_number") or tg.get("build_number"),
        "cpu_info": pp.get("cpu_info") or tg.get("cpu_info"),
        "backends": pp.get("backends") or tg.get("backends"),
        "reported_model_type": pp.get("model_type") or tg.get("model_type"),
        "reported_model_params": pp.get("model_n_params") or tg.get("model_n_params"),
    }


def command_text(cmd: list[str]) -> str | None:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
    except OSError:
        return None
    if p.returncode != 0:
        return None
    text = (p.stdout + "\n" + p.stderr).strip()
    return text or None


def cpu_model() -> str | None:
    p = Path("/proc/cpuinfo")
    if p.is_file():
        for line in p.read_text(errors="replace").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()
    return platform.processor() or None


def mem_total_kb() -> int | None:
    p = Path("/proc/meminfo")
    if p.is_file():
        m = re.search(r"^MemTotal:\s+(\d+)\s+kB$", p.read_text(), re.MULTILINE)
        if m:
            return int(m.group(1))
    return None


def write_summaries(results_dir: Path, run_id: str, meta: dict, rows: list[dict]) -> tuple[Path, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / f"phase1-{run_id}.json"
    csv_path = results_dir / f"phase1-{run_id}.csv"
    payload = {"schema_version": "phase1.v1", "run": meta, "results": rows}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(text, encoding="utf-8")
    (results_dir / "phase1-latest.json").write_text(text, encoding="utf-8")

    fields = [
        "run_id", "status", "error", "warning", "id", "group", "model", "repository", "quant",
        "compare_against", "model_path", "model_filename", "model_size_bytes", "model_size_gib",
        "hf_snapshot", "hf_blob_id", "threads", "n_gpu_layers", "prompt_tokens", "generation_tokens",
        "repetitions", "pp_tokens_per_s", "pp_stddev_tokens_per_s", "tg_tokens_per_s",
        "tg_stddev_tokens_per_s", "bench_wall_seconds", "peak_rss_kb", "peak_rss_gib",
        "cpu_user_seconds", "cpu_system_seconds", "cpu_total_seconds", "avg_cpu_percent",
        "cpu_thread_util_percent", "load_probe_wall_seconds", "load_probe_peak_rss_kb",
        "load_probe_cpu_user_seconds", "load_probe_cpu_system_seconds", "load_probe_cpu_total_seconds",
        "load_probe_avg_cpu_percent", "load_probe_cpu_thread_util_percent", "llama_build_commit",
        "llama_build_number", "cpu_info", "backends", "raw_bench_json", "raw_bench_stderr", "raw_meta_json"
    ]
    extra = sorted({k for r in rows for k in r if k not in fields})
    for out in (csv_path, results_dir / "phase1-latest.csv"):
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields + extra, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return json_path, csv_path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 llama-bench speed/efficiency runner")
    parser.add_argument("--registry", default=str(ROOT / "docs" / "MODEL_REGISTRY.md"))
    llama_cpp_dir = Path(os.environ.get("LLAMA_CPP_DIR", str(Path.home() / "Models/llama.cpp-k2"))).expanduser()
    parser.add_argument("--llama-bench", default=os.environ.get("LLAMA_BENCH", str(llama_cpp_dir / "build/bin/llama-bench")))
    parser.add_argument("--hf-cache", default=str(hf_cache_default()))
    parser.add_argument("--results-dir", default=str(ROOT / "results"))
    parser.add_argument("--only", action="append", default=[], metavar="ID")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-load-probe", action="store_true")
    args = parser.parse_args()

    registry = Path(args.registry).expanduser().resolve()
    bench = Path(args.llama_bench).expanduser().resolve()
    hf_cache = Path(args.hf_cache).expanduser().resolve()
    results_dir = Path(args.results_dir).expanduser().resolve()
    if not registry.is_file():
        parser.error(f"registry not found: {registry}")
    if not args.dry_run and not (bench.is_file() and os.access(bench, os.X_OK)):
        parser.error(f"llama-bench is not executable: {bench}")

    entries = parse_registry(registry)
    if args.only:
        wanted = set(args.only)
        known = {r["id"] for r in entries}
        unknown = sorted(wanted - known)
        if unknown:
            parser.error("unknown registry ID(s): " + ", ".join(unknown))
        entries = [r for r in entries if r["id"] in wanted]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = results_dir / "raw" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    help_text = None if args.dry_run else command_text([str(bench), "--help"])
    meta = {
        "run_id": run_id,
        "started_at_utc": now_utc(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "kernel": platform.release(),
        "cpu_model": cpu_model(),
        "mem_total_kb": mem_total_kb(),
        "registry_path": str(registry),
        "hf_cache": str(hf_cache),
        "llama_cpp_dir": str(llama_cpp_dir.resolve()),
        "llama_cpp_git_commit": command_text(["git", "-C", str(llama_cpp_dir), "rev-parse", "HEAD"]),
        "llama_bench": str(bench),
        "llama_bench_version": None if args.dry_run else command_text([str(bench), "--version"]),
        "cpu_percent_definition": "100% = one fully busy logical CPU; cpu_thread_util_percent normalizes avg_cpu_percent by benchmark thread count",
        "settings": {
            "threads": THREADS, "n_gpu_layers": 0, "protocol_context": CONTEXT,
            "prompt_tokens": PP_TOKENS, "generation_tokens": TG_TOKENS,
            "repetitions": REPETITIONS, "dry_run": args.dry_run,
        },
    }
    (raw_dir / "run.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Phase 1 run: {run_id}")
    print(f"Registry entries: {len(entries)}")
    print(f"HF cache: {hf_cache}")
    if not args.dry_run:
        print(f"llama-bench: {bench}")
        print(f"Settings: threads={THREADS}, ngl=0, pp={PP_TOKENS}, tg={TG_TOKENS}, repetitions={REPETITIONS}")

    results = []
    failed = False
    supports_no_warmup = bool(help_text and "--no-warmup" in help_text)

    for i, entry in enumerate(entries, 1):
        print(f"\n[{i}/{len(entries)}] {entry['id']} — {entry['model']} {entry['quant']}")
        row = dict(entry)
        row.update({
            "run_id": run_id, "status": "pending", "error": "", "warning": "",
            "threads": THREADS, "n_gpu_layers": 0, "prompt_tokens": PP_TOKENS,
            "generation_tokens": TG_TOKENS, "repetitions": REPETITIONS,
        })
        try:
            model_path, size_bytes, snapshot, blob_id = resolve_model(entry, hf_cache)
            row.update({
                "model_path": str(model_path), "model_filename": model_path.name,
                "model_size_bytes": size_bytes, "model_size_gib": round(size_bytes / 1024**3, 6),
                "hf_snapshot": snapshot, "hf_blob_id": blob_id,
            })
        except Exception as exc:
            row.update(status="failed", error=f"model_resolution: {exc}")
            failed = True
            results.append(row)
            print(f"[failed] {entry['id']}: {row['error']}")
            write_summaries(results_dir, run_id, meta, results)
            continue

        if args.dry_run:
            row["status"] = "resolved"
            results.append(row)
            print(f"[resolved] {entry['id']}: {model_path}")
            write_summaries(results_dir, run_id, meta, results)
            continue

        bench_json = raw_dir / f"{entry['id']}.bench.json"
        bench_err = raw_dir / f"{entry['id']}.bench.stderr.log"
        meta_json = raw_dir / f"{entry['id']}.meta.json"
        cmd = [str(bench), "-m", str(model_path), "-t", str(THREADS), "-ngl", "0",
               "-p", str(PP_TOKENS), "-n", str(TG_TOKENS), "-r", str(REPETITIONS), "-o", "json"]
        print("  running:", shlex.join(cmd))
        usage = run_child(cmd, bench_json, bench_err, THREADS)
        row.update({
            "bench_exit_code": usage["exit_code"], "bench_wall_seconds": usage["wall_seconds"],
            "peak_rss_kb": usage["peak_rss_kb"],
            "peak_rss_gib": round(usage["peak_rss_kb"] / 1024**2, 6) if usage["peak_rss_kb"] is not None else None,
            "cpu_user_seconds": usage["cpu_user_seconds"],
            "cpu_system_seconds": usage["cpu_system_seconds"],
            "cpu_total_seconds": usage["cpu_total_seconds"],
            "avg_cpu_percent": usage["avg_cpu_percent"],
            "cpu_thread_util_percent": usage["cpu_thread_util_percent"],
            "raw_bench_json": rel(bench_json), "raw_bench_stderr": rel(bench_err), "raw_meta_json": rel(meta_json),
        })
        if usage["exit_code"] != 0:
            row.update(status="failed", error=f"llama-bench exited with code {usage['exit_code']}")
            failed = True
        else:
            try:
                row.update(speed_metrics(read_bench_json(bench_json)))
                row["status"] = "ok"
            except Exception as exc:
                row.update(status="failed", error=f"metric_parse: {exc}")
                failed = True

        load_cmd = None
        load_usage = None
        if row["status"] == "ok" and not args.skip_load_probe:
            load_json = raw_dir / f"{entry['id']}.load.json"
            load_err = raw_dir / f"{entry['id']}.load.stderr.log"
            load_cmd = [str(bench), "-m", str(model_path), "-t", str(THREADS), "-ngl", "0",
                        "-p", "1", "-n", "0", "-r", "1", "-o", "json"]
            if supports_no_warmup:
                load_cmd.insert(1, "--no-warmup")
            load_usage = run_child(load_cmd, load_json, load_err, THREADS)
            row.update({
                "load_probe_exit_code": load_usage["exit_code"],
                "load_probe_wall_seconds": load_usage["wall_seconds"],
                "load_probe_peak_rss_kb": load_usage["peak_rss_kb"],
                "load_probe_cpu_user_seconds": load_usage["cpu_user_seconds"],
                "load_probe_cpu_system_seconds": load_usage["cpu_system_seconds"],
                "load_probe_cpu_total_seconds": load_usage["cpu_total_seconds"],
                "load_probe_avg_cpu_percent": load_usage["avg_cpu_percent"],
                "load_probe_cpu_thread_util_percent": load_usage["cpu_thread_util_percent"],
                "load_probe_no_warmup": supports_no_warmup,
                "raw_load_json": rel(load_json), "raw_load_stderr": rel(load_err),
            })
            if load_usage["exit_code"] != 0:
                row.update(status="ok_with_warnings", warning=f"load probe exited with code {load_usage['exit_code']}")

        meta_json.write_text(json.dumps({
            "entry": entry, "bench_command": cmd, "bench_usage": usage,
            "load_probe_command": load_cmd, "load_probe_usage": load_usage, "result": row,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        results.append(row)
        if row["status"] in ("ok", "ok_with_warnings"):
            cpu_text = f", cpu={row['avg_cpu_percent']:.1f}% ({row['cpu_thread_util_percent']:.1f}% of {THREADS}T)" if row.get("avg_cpu_percent") is not None else ""
            print(f"[{row['status']}] {entry['id']}: pp={row['pp_tokens_per_s']:.2f} tok/s, tg={row['tg_tokens_per_s']:.2f} tok/s, peak_rss={row['peak_rss_gib']:.2f} GiB{cpu_text}")
        else:
            print(f"[failed] {entry['id']}: {row['error']}")
        write_summaries(results_dir, run_id, meta, results)

    meta["finished_at_utc"] = now_utc()
    meta["completed_entries"] = len(results)
    meta["failed_entries"] = sum(r["status"] == "failed" for r in results)
    json_path, csv_path = write_summaries(results_dir, run_id, meta, results)
    (raw_dir / "run.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("\nPhase 1 complete.")
    print(f"JSON summary: {json_path}")
    print(f"CSV summary:  {csv_path}")
    print(f"Raw outputs:  {raw_dir}")
    if failed:
        print("One or more entries failed; all remaining entries were still attempted.", file=sys.stderr)
        return 2
    return 0


raise SystemExit(main())
PY
