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
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ["LMB_ROOT_DIR"])
THREADS = 4
CONTEXT = 8192
TEMPERATURE = 0.0
SEED = 42
MAX_TOKENS = 64
SERVER_START_TIMEOUT = 180
REQUEST_TIMEOUT = 240


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
        if not cells or cells[0] == "ID" or len(cells) < 6:
            continue
        if all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
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
        raise RuntimeError(f"no model rows found in {path}")
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
        model_path = next(iter(by_blob.values()))
        try:
            blob_id = model_path.resolve(strict=True).name
        except OSError:
            blob_id = ""
        return model_path, model_path.stat().st_size, snap.name, blob_id
    raise FileNotFoundError(f"no local {row['quant']} GGUF under {root / 'snapshots'}")


def load_tasks(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise RuntimeError("task file must contain a non-empty tasks array")
    seen = set()
    for task in tasks:
        for field in ("id", "bucket", "target_chars", "mode", "needles", "question", "expected_answer"):
            if field not in task:
                raise RuntimeError(f"task missing {field}: {task.get('id', '<unknown>')}")
        if task["id"] in seen:
            raise RuntimeError(f"duplicate task ID: {task['id']}")
        seen.add(task["id"])
        if task["bucket"] not in {"1k", "2k", "4k"}:
            raise RuntimeError(f"bad bucket in {task['id']}")
        if task["mode"] not in {"direct", "compose", "relational"}:
            raise RuntimeError(f"bad mode in {task['id']}")
        if not isinstance(task["target_chars"], int) or task["target_chars"] < 1000:
            raise RuntimeError(f"bad target_chars in {task['id']}")
        if not isinstance(task["needles"], list) or not task["needles"]:
            raise RuntimeError(f"no needles in {task['id']}")
        for needle in task["needles"]:
            if not (0.0 <= float(needle.get("fraction", -1)) <= 1.0) or not isinstance(needle.get("text"), str):
                raise RuntimeError(f"bad needle in {task['id']}")
    return payload


def build_reference(task: dict) -> str:
    target = int(task["target_chars"])
    colors = ["amber", "cobalt", "silver", "violet", "teal", "ochre", "indigo"]
    routes = ["north", "south", "east", "west", "central"]
    owners = ["Dara", "Omar", "Lea", "Noor", "Iris", "Tariq", "Mina"]
    records = []
    i = 1
    needle_chars = sum(len(n["text"]) + 1 for n in task["needles"])
    filler_target = max(500, target - needle_chars)
    total = 0
    while total < filler_target:
        line = (
            f"Record {i:03d}: routine station K{i % 47:02d} uses {colors[i % len(colors)]} channel, "
            f"{routes[i % len(routes)]} route, owner {owners[i % len(owners)]}, cycle {(i * 7) % 97 + 1}, "
            f"rack R{(i * 11) % 53:02d}. This maintenance entry is unrelated to the requested authoritative note."
        )
        records.append(line)
        total += len(line) + 1
        i += 1

    inserts = sorted(task["needles"], key=lambda n: float(n["fraction"]))
    offset = 0
    base_len = len(records)
    for needle in inserts:
        idx = min(len(records), max(0, int(round(float(needle["fraction"]) * base_len)) + offset))
        records.insert(idx, needle["text"])
        offset += 1
    return "\n".join(records)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def http_json(url: str, payload: dict | None = None, timeout: int = 10) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return int(exc.code), parsed


def wait_for_server(port: int, proc: subprocess.Popen, timeout_s: int) -> None:
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited early with code {proc.returncode}")
        try:
            status, body = http_json(f"http://127.0.0.1:{port}/health", timeout=2)
            last = (status, body)
            if status == 200:
                return
        except Exception as exc:
            last = str(exc)
        time.sleep(0.25)
    raise TimeoutError(f"server was not healthy after {timeout_s}s; last={last}")


def stop_server(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def response_content(response: dict) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("response missing choices")
    msg = choices[0].get("message", {})
    content = msg.get("content")
    if content is None:
        content = choices[0].get("text")
    if not isinstance(content, str):
        raise RuntimeError("response missing text content")
    return content


def answer_match(text: str, expected: str) -> bool:
    candidate = text.strip()
    exp = expected.strip()
    if candidate.casefold() == exp.casefold():
        return True
    lines = [x.strip().strip('`"\' ') for x in candidate.splitlines() if x.strip()]
    for line in lines[-2:]:
        cleaned = re.sub(r"^(?:final\s+answer|answer)\s*[:=-]\s*", "", line, flags=re.I).strip().rstrip(".!;,:")
        if cleaned.casefold() == exp.casefold():
            return True
    if exp.isdigit():
        return exp in re.findall(r"(?<!\d)\d+(?!\d)", candidate)
    pattern = r"(?<![A-Za-z0-9_-])" + re.escape(exp) + r"(?![A-Za-z0-9_-])"
    return re.search(pattern, candidate, flags=re.I) is not None


def command_text(cmd: list[str]) -> str | None:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
    except OSError:
        return None
    if p.returncode != 0:
        return None
    text = (p.stdout + "\n" + p.stderr).strip()
    return text or None


def summarize(rows: list[dict], entries: list[dict]) -> list[dict]:
    by_model = defaultdict(list)
    for row in rows:
        by_model[row["model_id"]].append(row)
    out = []
    for entry in entries:
        rs = by_model.get(entry["id"], [])
        scores = [float(r.get("task_score", 0.0)) for r in rs]
        buckets = {}
        for bucket in ("1k", "2k", "4k"):
            br = [r for r in rs if r["bucket"] == bucket]
            buckets[bucket] = round(sum(float(r["task_score"]) for r in br) / len(br), 2) if br else None
        modes = {}
        for mode in ("direct", "compose", "relational"):
            mr = [r for r in rs if r["mode"] == mode]
            modes[mode] = round(sum(float(r["task_score"]) for r in mr) / len(mr), 2) if mr else None
        degradation = None
        if buckets.get("1k") is not None and buckets.get("4k") is not None:
            degradation = round(buckets["1k"] - buckets["4k"], 2)
        prompt_tokens_by_bucket = {}
        for bucket in ("1k", "2k", "4k"):
            vals = [int(r["prompt_tokens"]) for r in rs if r["bucket"] == bucket and r.get("prompt_tokens") is not None]
            prompt_tokens_by_bucket[bucket] = round(sum(vals) / len(vals), 1) if vals else None
        out.append({
            "model_id": entry["id"],
            "model": entry["model"],
            "quant": entry["quant"],
            "tasks": len(rs),
            "solved": sum(bool(r.get("solved")) for r in rs),
            "phase7_score": round(sum(scores) / len(scores), 2) if scores else None,
            "buckets": buckets,
            "modes": modes,
            "degradation_1k_to_4k": degradation,
            "avg_prompt_tokens": prompt_tokens_by_bucket,
        })
    return out


def write_outputs(results_dir: Path, run_id: str, meta: dict, rows: list[dict], summaries: list[dict]):
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / f"phase7-{run_id}.json"
    csv_path = results_dir / f"phase7-{run_id}.csv"
    payload = {"schema_version": "phase7.v0.1", "run": meta, "models": summaries, "results": rows}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(text, encoding="utf-8")
    (results_dir / "phase7-latest.json").write_text(text, encoding="utf-8")
    fields = [
        "run_id", "model_id", "model", "quant", "task_id", "bucket", "mode", "status", "solved",
        "task_score", "prompt_tokens", "completion_tokens", "generation_seconds", "artifact_dir", "error",
    ]
    for out in (csv_path, results_dir / "phase7-latest.csv"):
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 7 context retrieval benchmark")
    parser.add_argument("--registry", default=str(ROOT / "docs" / "MODEL_REGISTRY.md"))
    parser.add_argument("--tasks", default=str(ROOT / "tasks" / "phase7_v0.1.json"))
    llama_cpp_dir = Path(os.environ.get("LLAMA_CPP_DIR", str(Path.home() / "Models/llama.cpp-k2"))).expanduser()
    parser.add_argument("--llama-server", default=os.environ.get("LLAMA_SERVER", str(llama_cpp_dir / "build/bin/llama-server")))
    parser.add_argument("--hf-cache", default=str(hf_cache_default()))
    parser.add_argument("--results-dir", default=str(ROOT / "results"))
    parser.add_argument("--only", action="append", default=[], metavar="MODEL_ID")
    parser.add_argument("--task", action="append", default=[], metavar="TASK_ID")
    parser.add_argument("--include-comparisons", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--server-timeout", type=int, default=SERVER_START_TIMEOUT)
    parser.add_argument("--request-timeout", type=int, default=REQUEST_TIMEOUT)
    args = parser.parse_args()

    registry_path = Path(args.registry).expanduser().resolve()
    task_path = Path(args.tasks).expanduser().resolve()
    server = Path(args.llama_server).expanduser().resolve()
    hf_cache = Path(args.hf_cache).expanduser().resolve()
    results_dir = Path(args.results_dir).expanduser().resolve()

    if not registry_path.is_file(): parser.error(f"registry not found: {registry_path}")
    if not task_path.is_file(): parser.error(f"task file not found: {task_path}")
    if not args.dry_run and not (server.is_file() and os.access(server, os.X_OK)):
        parser.error(f"llama-server is not executable: {server}")

    all_entries = parse_registry(registry_path)
    entries = all_entries if args.include_comparisons else [e for e in all_entries if e["group"] == "primary"]
    if args.only:
        wanted = set(args.only)
        known = {e["id"] for e in all_entries}
        unknown = sorted(wanted - known)
        if unknown: parser.error("unknown model ID(s): " + ", ".join(unknown))
        entries = [e for e in all_entries if e["id"] in wanted]

    task_payload = load_tasks(task_path)
    tasks = task_payload["tasks"]
    if args.task:
        wanted = set(args.task)
        known = {t["id"] for t in tasks}
        unknown = sorted(wanted - known)
        if unknown: parser.error("unknown task ID(s): " + ", ".join(unknown))
        tasks = [t for t in tasks if t["id"] in wanted]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_root = results_dir / "raw" / "phase7" / run_id
    raw_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": run_id,
        "started_at_utc": now_utc(),
        "benchmark_version": task_payload.get("benchmark_version", "phase7-v0.1"),
        "task_file": str(task_path),
        "registry_path": str(registry_path),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "kernel": platform.release(),
        "hf_cache": str(hf_cache),
        "llama_cpp_dir": str(llama_cpp_dir.resolve()),
        "llama_cpp_git_commit": command_text(["git", "-C", str(llama_cpp_dir), "rev-parse", "HEAD"]),
        "llama_server": str(server),
        "llama_server_version": None if args.dry_run else command_text([str(server), "--version"]),
        "settings": {
            "threads": THREADS, "n_gpu_layers": 0, "context": CONTEXT, "temperature": TEMPERATURE,
            "seed": SEED, "max_tokens": MAX_TOKENS, "cache_prompt": False, "reasoning_effort": "none",
        },
    }

    print(f"Phase 7 run: {run_id}")
    print(f"Benchmark version: {meta['benchmark_version']}")
    print(f"Models: {len(entries)}")
    print(f"Tasks per model: {len(tasks)}")
    print(f"HF cache: {hf_cache}")
    if not args.dry_run:
        print(f"llama-server: {server}")
        print(f"Settings: threads={THREADS}, ngl=0, ctx={CONTEXT}, temp={TEMPERATURE}, seed={SEED}, reasoning=none, max_tokens={MAX_TOKENS}")

    resolved = []
    preflight_failed = False
    for entry in entries:
        try:
            model_path, size_bytes, snapshot, blob_id = resolve_model(entry, hf_cache)
            item = dict(entry)
            item.update(model_path=model_path, size_bytes=size_bytes, hf_snapshot=snapshot, hf_blob_id=blob_id)
            resolved.append(item)
            print(f"[resolved] {entry['id']}: {model_path.name}")
        except Exception as exc:
            preflight_failed = True
            print(f"[failed] {entry['id']}: {exc}", file=sys.stderr)

    if args.dry_run:
        print(f"Preflight complete: {len(resolved)}/{len(entries)} models resolved, {len(tasks)} context tasks selected.")
        counts = defaultdict(int)
        for task in tasks: counts[task["bucket"]] += 1
        for bucket in ("1k", "2k", "4k"): print(f"  {bucket}: {counts[bucket]}")
        return 2 if preflight_failed else 0
    if preflight_failed:
        print("Preflight failed; fix missing/ambiguous models before Phase 7 testing.", file=sys.stderr)
        return 2

    system_prompt = task_payload.get("system_prompt", "Use the reference text to answer the question.")
    rows = []
    infrastructure_failed = False

    for model_index, entry in enumerate(resolved, 1):
        model_id = entry["id"]
        model_raw = raw_root / model_id
        model_raw.mkdir(parents=True, exist_ok=True)
        port = free_port()
        server_log = model_raw / "server.log"
        cmd = [str(server), "-m", str(entry["model_path"]), "-t", str(THREADS), "-ngl", "0", "-c", str(CONTEXT), "--host", "127.0.0.1", "--port", str(port), "--alias", model_id]
        print(f"\n[{model_index}/{len(resolved)}] {model_id} — {entry['model']} {entry['quant']}")
        print("  server:", shlex.join(cmd))
        proc = None
        log_handle = None
        try:
            env = os.environ.copy(); env["HF_HUB_OFFLINE"] = "1"; env["TRANSFORMERS_OFFLINE"] = "1"
            log_handle = server_log.open("wb")
            started = time.monotonic()
            proc = subprocess.Popen(cmd, stdout=log_handle, stderr=subprocess.STDOUT, env=env)
            wait_for_server(port, proc, args.server_timeout)
            print(f"  ready in {time.monotonic() - started:.2f}s")

            for task_index, task in enumerate(tasks, 1):
                task_dir = model_raw / task["id"]
                task_dir.mkdir(parents=True, exist_ok=True)
                reference = build_reference(task)
                prompt = f"REFERENCE TEXT:\n{reference}\n\nQUESTION:\n{task['question']}"
                (task_dir / "reference.txt").write_text(reference + "\n", encoding="utf-8")
                (task_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
                payload = {
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": TEMPERATURE,
                    "seed": SEED,
                    "max_tokens": MAX_TOKENS,
                    "cache_prompt": False,
                    "reasoning_effort": "none",
                }
                started_req = time.monotonic()
                try:
                    status, response = http_json(f"http://127.0.0.1:{port}/v1/chat/completions", payload, args.request_timeout)
                    elapsed = time.monotonic() - started_req
                    (task_dir / "response.json").write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
                    if status != 200:
                        raise RuntimeError(f"HTTP {status}: {response}")
                    content = response_content(response)
                    (task_dir / "model_output.txt").write_text(content, encoding="utf-8")
                    solved = answer_match(content, str(task["expected_answer"]))
                    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
                    row = {
                        "run_id": run_id, "model_id": model_id, "model": entry["model"], "quant": entry["quant"],
                        "task_id": task["id"], "bucket": task["bucket"], "mode": task["mode"],
                        "status": "PASS" if solved else "FAIL", "solved": solved, "task_score": 100.0 if solved else 0.0,
                        "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                        "generation_seconds": round(elapsed, 3), "artifact_dir": str(task_dir.relative_to(ROOT)), "error": "",
                    }
                    rows.append(row)
                    tok = f" tokens={row['prompt_tokens']}" if row["prompt_tokens"] is not None else ""
                    print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: {row['status']}{tok}")
                except Exception as exc:
                    infrastructure_failed = True
                    row = {
                        "run_id": run_id, "model_id": model_id, "model": entry["model"], "quant": entry["quant"],
                        "task_id": task["id"], "bucket": task["bucket"], "mode": task["mode"],
                        "status": "ERROR", "solved": False, "task_score": 0.0, "prompt_tokens": None,
                        "completion_tokens": None, "generation_seconds": round(time.monotonic() - started_req, 3),
                        "artifact_dir": str(task_dir.relative_to(ROOT)), "error": f"{type(exc).__name__}: {exc}",
                    }
                    rows.append(row)
                    print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: ERROR — {exc}")
        except Exception as exc:
            infrastructure_failed = True
            print(f"  MODEL ERROR — {exc}", file=sys.stderr)
        finally:
            stop_server(proc)
            if log_handle is not None: log_handle.close()

    summaries = summarize(rows, resolved)
    meta["finished_at_utc"] = now_utc()
    json_path, csv_path = write_outputs(results_dir, run_id, meta, rows, summaries)
    print("\nPhase 7 complete.")
    print(f"JSON summary: {json_path}")
    print(f"CSV task results: {csv_path}")
    print(f"Raw outputs: {raw_root}")
    print("\nMODEL SUMMARY")
    def fmt_pct(value):
        return "n/a" if value is None else f"{value:.1f}%"

    def fmt_num(value):
        return "n/a" if value is None else f"{value:.1f}"

    for s in sorted(summaries, key=lambda x: (x["phase7_score"] is not None, x["phase7_score"] or -1), reverse=True):
        b = s["buckets"]
        score = "n/a" if s["phase7_score"] is None else f"{s['phase7_score']:.2f}%"
        print(
            f"{s['model_id']:<28} context={score:>7} "
            f"solved={s['solved']:2d}/{s['tasks']:2d} "
            f"1k={fmt_pct(b['1k']):>6} "
            f"2k={fmt_pct(b['2k']):>6} "
            f"4k={fmt_pct(b['4k']):>6} "
            f"drop={fmt_num(s['degradation_1k_to_4k']):>5}"
        )
    return 2 if infrastructure_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
