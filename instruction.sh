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
CONTEXT = 4096
TEMPERATURE = 0.0
SEED = 42
MAX_TOKENS = 256
SERVER_START_TIMEOUT = 180
REQUEST_TIMEOUT = 180


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
        path = next(iter(by_blob.values()))
        try:
            blob_id = path.resolve(strict=True).name
        except OSError:
            blob_id = ""
        return path, path.stat().st_size, snap.name, blob_id
    raise FileNotFoundError(f"no local {row['quant']} GGUF under {root / 'snapshots'}")


def load_tasks(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise RuntimeError("task file must contain a non-empty tasks array")
    seen = set()
    valid_types = {
        "equals", "contains", "not_contains", "not_contains_ci", "count", "contains_word",
        "regex_fullmatch", "line_count", "word_count", "starts_with", "ends_with", "ordered",
        "json_valid", "json_object", "json_keys_exact", "json_nested_keys_exact", "json_value",
    }
    for task in tasks:
        for field in ("id", "category", "prompt", "checks"):
            if field not in task:
                raise RuntimeError(f"task missing {field}: {task.get('id', '<unknown>')}")
        if task["id"] in seen:
            raise RuntimeError(f"duplicate task ID: {task['id']}")
        seen.add(task["id"])
        if not isinstance(task["checks"], list) or not task["checks"]:
            raise RuntimeError(f"task has no checks: {task['id']}")
        for check in task["checks"]:
            if check.get("type") not in valid_types:
                raise RuntimeError(f"unsupported check type in {task['id']}: {check.get('type')}")
            if check.get("type") == "regex_fullmatch":
                re.compile(check["pattern"])
    return payload


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


def normalize_output(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return text


def strict_json_equal(actual, expected) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(strict_json_equal(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(strict_json_equal(actual[k], expected[k]) for k in expected)
    return actual == expected


def json_path_value(obj, path: list):
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            raise KeyError(key)
        cur = cur[key]
    return cur


def evaluate_check(text: str, check: dict, parsed_json, json_error: str | None) -> tuple[bool, str]:
    kind = check["type"]
    if kind == "equals":
        ok = text == check["value"]
    elif kind == "contains":
        ok = check["text"] in text
    elif kind == "not_contains":
        ok = check["text"] not in text
    elif kind == "not_contains_ci":
        ok = check["text"].casefold() not in text.casefold()
    elif kind == "count":
        ok = text.count(check["text"]) == int(check["value"])
    elif kind == "contains_word":
        ok = re.search(r"(?<!\w)" + re.escape(check["text"]) + r"(?!\w)", text) is not None
    elif kind == "regex_fullmatch":
        ok = re.fullmatch(check["pattern"], text) is not None
    elif kind == "line_count":
        n = 0 if text == "" else len(text.split("\n"))
        ok = n == int(check["value"])
    elif kind == "word_count":
        ok = len(text.split()) == int(check["value"])
    elif kind == "starts_with":
        ok = text.startswith(check["value"])
    elif kind == "ends_with":
        ok = text.endswith(check["value"])
    elif kind == "ordered":
        pos = -1
        ok = True
        for value in check["values"]:
            nxt = text.find(value, pos + 1)
            if nxt < 0:
                ok = False
                break
            pos = nxt
    elif kind == "json_valid":
        ok = json_error is None
    elif kind == "json_object":
        ok = json_error is None and isinstance(parsed_json, dict)
    elif kind == "json_keys_exact":
        ok = json_error is None and isinstance(parsed_json, dict) and set(parsed_json.keys()) == set(check["keys"]) and len(parsed_json) == len(check["keys"])
    elif kind == "json_nested_keys_exact":
        try:
            value = json_path_value(parsed_json, check.get("path", [])) if json_error is None else None
            ok = isinstance(value, dict) and set(value.keys()) == set(check["keys"]) and len(value) == len(check["keys"])
        except (KeyError, TypeError):
            ok = False
    elif kind == "json_value":
        try:
            value = json_path_value(parsed_json, check.get("path", [])) if json_error is None else None
            ok = strict_json_equal(value, check["value"])
        except (KeyError, TypeError):
            ok = False
    else:
        raise RuntimeError(f"unsupported check type: {kind}")
    return bool(ok), kind


def score_task(content: str, task: dict) -> dict:
    text = normalize_output(content)
    parsed_json = None
    json_error = None
    try:
        parsed_json = json.loads(text)
    except Exception as exc:
        json_error = f"{type(exc).__name__}: {exc}"

    details = []
    passed = 0
    for idx, check in enumerate(task["checks"], 1):
        ok, kind = evaluate_check(text, check, parsed_json, json_error)
        details.append({"index": idx, "type": kind, "passed": ok})
        passed += int(ok)
    total = len(task["checks"])
    return {
        "passed": passed,
        "total": total,
        "task_score": round(passed / total * 100, 2),
        "solved": passed == total,
        "checks": details,
        "normalized_output": text,
        "json_error": json_error,
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


def summarize(rows: list[dict], entries: list[dict]) -> list[dict]:
    by_model = defaultdict(list)
    for row in rows:
        by_model[row["model_id"]].append(row)
    out = []
    for entry in entries:
        rs = by_model.get(entry["id"], [])
        scores = [float(r.get("task_score", 0.0)) for r in rs]
        categories = {}
        for category in sorted({r["category"] for r in rs}):
            cr = [r for r in rs if r["category"] == category]
            categories[category] = round(sum(float(r["task_score"]) for r in cr) / len(cr), 2) if cr else None
        out.append({
            "model_id": entry["id"],
            "model": entry["model"],
            "quant": entry["quant"],
            "tasks": len(rs),
            "solved": sum(bool(r.get("solved")) for r in rs),
            "phase5_score": round(sum(scores) / len(scores), 2) if scores else None,
            "categories": categories,
        })
    return out


def write_outputs(results_dir: Path, run_id: str, meta: dict, rows: list[dict], summaries: list[dict]):
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / f"phase5-{run_id}.json"
    csv_path = results_dir / f"phase5-{run_id}.csv"
    payload = {"schema_version": "phase5.v0.1", "run": meta, "models": summaries, "results": rows}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(text, encoding="utf-8")
    (results_dir / "phase5-latest.json").write_text(text, encoding="utf-8")
    fields = [
        "run_id", "model_id", "model", "quant", "task_id", "category", "status", "solved",
        "passed_checks", "total_checks", "task_score", "generation_seconds", "prompt_tokens",
        "completion_tokens", "artifact_dir", "error",
    ]
    for out in (csv_path, results_dir / "phase5-latest.csv"):
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 deterministic instruction-following benchmark")
    parser.add_argument("--registry", default=str(ROOT / "docs" / "MODEL_REGISTRY.md"))
    parser.add_argument("--tasks", default=str(ROOT / "tasks" / "phase5_v0.1.json"))
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
    raw_root = results_dir / "raw" / "phase5" / run_id
    raw_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": run_id,
        "started_at_utc": now_utc(),
        "benchmark_version": task_payload.get("benchmark_version", "phase5-v0.1"),
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
            "terminal_newline_policy": "ignore_one_final_newline_only",
        },
    }

    print(f"Phase 5 run: {run_id}")
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
        print(f"Preflight complete: {len(resolved)}/{len(entries)} models resolved, {len(tasks)} instruction tasks selected.")
        counts = defaultdict(int)
        for task in tasks:
            counts[task["category"]] += 1
        for category in sorted(counts):
            print(f"  {category}: {counts[category]}")
        return 2 if preflight_failed else 0
    if preflight_failed:
        print("Preflight failed; fix missing/ambiguous models before Phase 5 testing.", file=sys.stderr)
        return 2

    system_prompt = task_payload.get("system_prompt", "Follow the instruction exactly.")
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
                artifact_dir = model_raw / task["id"]
                artifact_dir.mkdir(parents=True, exist_ok=True)
                row = {
                    "run_id": run_id, "model_id": model_id, "model": entry["model"], "quant": entry["quant"],
                    "task_id": task["id"], "category": task["category"], "status": "pending", "solved": False,
                    "passed_checks": 0, "total_checks": len(task["checks"]), "task_score": 0.0,
                    "generation_seconds": "", "prompt_tokens": "", "completion_tokens": "",
                    "artifact_dir": str(artifact_dir.relative_to(ROOT)) if artifact_dir.is_relative_to(ROOT) else str(artifact_dir),
                    "error": "",
                }
                try:
                    request_body = {
                        "model": model_id,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": task["prompt"]},
                        ],
                        "temperature": TEMPERATURE,
                        "seed": SEED,
                        "max_tokens": MAX_TOKENS,
                        "stream": False,
                        "cache_prompt": False,
                        "reasoning_effort": "none",
                    }
                    gen_start = time.monotonic()
                    status, response = http_json(f"http://127.0.0.1:{port}/v1/chat/completions", request_body, timeout=args.request_timeout)
                    elapsed = time.monotonic() - gen_start
                    row["generation_seconds"] = round(elapsed, 6)
                    (artifact_dir / "response.json").write_text(json.dumps({
                        "task": task, "request": request_body, "http_status": status,
                        "response": response, "generation_seconds": elapsed,
                    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    if status != 200:
                        raise RuntimeError(f"HTTP {status}: {response}")
                    content = response_content(response)
                    (artifact_dir / "model_output.txt").write_text(content, encoding="utf-8")
                    usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
                    row["prompt_tokens"] = usage.get("prompt_tokens", "")
                    row["completion_tokens"] = usage.get("completion_tokens", "")

                    scored = score_task(content, task)
                    (artifact_dir / "score.json").write_text(json.dumps(scored, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    row["status"] = "ok"
                    row["solved"] = scored["solved"]
                    row["passed_checks"] = scored["passed"]
                    row["total_checks"] = scored["total"]
                    row["task_score"] = scored["task_score"]
                    mark = "PASS" if scored["solved"] else f"PARTIAL ({scored['passed']}/{scored['total']})"
                    print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: {mark}")
                except Exception as exc:
                    infrastructure_failed = True
                    row["status"] = "failed"
                    row["error"] = str(exc)
                    print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: ERROR — {exc}")
                rows.append(row)
        except Exception as exc:
            infrastructure_failed = True
            print(f"[failed] {model_id}: server_start: {exc}", file=sys.stderr)
            existing = {r["task_id"] for r in rows if r["model_id"] == model_id}
            for task in tasks:
                if task["id"] in existing:
                    continue
                rows.append({
                    "run_id": run_id, "model_id": model_id, "model": entry["model"], "quant": entry["quant"],
                    "task_id": task["id"], "category": task["category"], "status": "failed", "solved": False,
                    "passed_checks": 0, "total_checks": len(task["checks"]), "task_score": 0.0,
                    "generation_seconds": "", "prompt_tokens": "", "completion_tokens": "", "artifact_dir": "",
                    "error": f"server_start: {exc}",
                })
        finally:
            stop_server(proc)
            if log_handle is not None:
                log_handle.close()

        summaries = summarize(rows, resolved)
        current = next((s for s in summaries if s["model_id"] == model_id), None)
        if current and current["phase5_score"] is not None:
            print(f"  instruction score: {current['phase5_score']:.2f}% solved={current['solved']}/{current['tasks']}")
        write_outputs(results_dir, run_id, meta, rows, summaries)

    meta["finished_at_utc"] = now_utc()
    summaries = summarize(rows, resolved)
    json_path, csv_path = write_outputs(results_dir, run_id, meta, rows, summaries)
    print("\nPhase 5 complete.")
    print(f"JSON summary: {json_path}")
    print(f"CSV task results: {csv_path}")
    print(f"Raw outputs: {raw_root}")
    print("\nMODEL SUMMARY")
    for s in sorted(summaries, key=lambda x: (x["phase5_score"] if x["phase5_score"] is not None else -1), reverse=True):
        cats = " ".join(f"{k}={v:.1f}%" for k, v in s["categories"].items())
        print(f"{s['model_id']:24} instruction={s['phase5_score']:6.2f}% solved={s['solved']:2}/{s['tasks']:2} {cats}")
    if infrastructure_failed:
        print("One or more infrastructure executions failed; successful outputs were retained.", file=sys.stderr)
        return 2
    return 0

raise SystemExit(main())
PY
