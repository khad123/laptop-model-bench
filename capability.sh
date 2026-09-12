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
MAX_TOKENS = 32
SERVER_START_TIMEOUT = 180
REQUEST_TIMEOUT = 120


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
    for task in tasks:
        required = {"id", "domain", "category", "question", "choices", "answer"}
        missing = sorted(required - set(task))
        if missing:
            raise RuntimeError(f"task missing fields {missing}: {task}")
        if task["id"] in seen:
            raise RuntimeError(f"duplicate task ID: {task['id']}")
        seen.add(task["id"])
        if set(task["choices"]) != {"A", "B", "C", "D"}:
            raise RuntimeError(f"task {task['id']} must have choices A/B/C/D")
        if task["answer"] not in {"A", "B", "C", "D"}:
            raise RuntimeError(f"task {task['id']} has invalid answer")
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
    url = f"http://127.0.0.1:{port}/health"
    last = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited early with code {proc.returncode}")
        try:
            status, body = http_json(url, timeout=2)
            last = (status, body)
            if status == 200:
                return
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
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


def format_prompt(task: dict) -> str:
    c = task["choices"]
    return (
        f"Question: {task['question']}\n\n"
        f"A. {c['A']}\nB. {c['B']}\nC. {c['C']}\nD. {c['D']}\n\n"
        "Choose the best answer. Return only one uppercase letter: A, B, C, or D."
    )


def extract_choice(text: str) -> tuple[str | None, str]:
    cleaned = text.strip()
    upper = cleaned.upper()
    if re.fullmatch(r"[ABCD][\s\.!\)]*", upper):
        return upper[0], "exact"
    for pat in (
        r"(?:FINAL\s+ANSWER|FINAL|ANSWER|CHOICE|OPTION)\s*[:=\-]?\s*\(?([ABCD])\)?",
        r"^\s*\(?([ABCD])\)?(?:[\s\.!,:;]|$)",
    ):
        m = re.search(pat, upper, re.MULTILINE)
        if m:
            return m.group(1), "label"
    letters = re.findall(r"(?<![A-Z])([ABCD])(?![A-Z])", upper)
    unique = sorted(set(letters))
    if len(unique) == 1:
        return unique[0], "unique_letter"
    return None, "unparsed"


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


def summarize(rows: list[dict], entries: list[dict]) -> list[dict]:
    by_model = defaultdict(list)
    for row in rows:
        by_model[row["model_id"]].append(row)
    entry_map = {e["id"]: e for e in entries}
    summaries = []
    for model_id in [e["id"] for e in entries]:
        rs = by_model.get(model_id, [])
        scored = [r for r in rs if r["status"] == "ok"]
        total = len(rs)
        correct = sum(int(r.get("correct", 0)) for r in scored)
        parsed = sum(r.get("extracted_answer") in {"A", "B", "C", "D"} for r in scored)
        domains = {}
        categories = {}
        for field, dest in (("domain", domains), ("category", categories)):
            values = sorted({r[field] for r in rs})
            for value in values:
                subset = [r for r in scored if r[field] == value]
                denom = len([r for r in rs if r[field] == value])
                hits = sum(int(r.get("correct", 0)) for r in subset)
                dest[value] = {
                    "correct": hits,
                    "total": denom,
                    "accuracy": round(hits / denom * 100, 2) if denom else None,
                }
        entry = entry_map[model_id]
        domain_scores = [v["accuracy"] for v in domains.values() if v.get("accuracy") is not None]
        phase2_score = round(sum(domain_scores) / len(domain_scores), 2) if domain_scores else None
        summaries.append({
            "model_id": model_id,
            "model": entry["model"],
            "quant": entry["quant"],
            "correct": correct,
            "total": total,
            "accuracy": round(correct / total * 100, 2) if total else None,
            "phase2_score": phase2_score,
            "parsed": parsed,
            "parse_rate": round(parsed / total * 100, 2) if total else None,
            "domains": domains,
            "categories": categories,
        })
    return summaries


def write_outputs(results_dir: Path, run_id: str, meta: dict, rows: list[dict], summaries: list[dict]) -> tuple[Path, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / f"phase2-{run_id}.json"
    csv_path = results_dir / f"phase2-{run_id}.csv"
    payload = {"schema_version": "phase2.v0.1", "run": meta, "models": summaries, "results": rows}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(text, encoding="utf-8")
    (results_dir / "phase2-latest.json").write_text(text, encoding="utf-8")

    fields = [
        "run_id", "model_id", "model", "quant", "task_id", "domain", "category", "status",
        "expected_answer", "extracted_answer", "correct", "extraction_method", "response_text",
        "http_status", "elapsed_seconds", "prompt_tokens", "completion_tokens", "error", "raw_response_json"
    ]
    for out in (csv_path, results_dir / "phase2-latest.csv"):
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return json_path, csv_path


def command_text(cmd: list[str]) -> str | None:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
    except OSError:
        return None
    if p.returncode != 0:
        return None
    text = (p.stdout + "\n" + p.stderr).strip()
    return text or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2 deterministic reasoning + knowledge benchmark")
    parser.add_argument("--registry", default=str(ROOT / "docs" / "MODEL_REGISTRY.md"))
    parser.add_argument("--tasks", default=str(ROOT / "tasks" / "phase2_v0.1.json"))
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

    if not registry_path.is_file():
        parser.error(f"registry not found: {registry_path}")
    if not task_path.is_file():
        parser.error(f"task file not found: {task_path}")
    if not args.dry_run and not (server.is_file() and os.access(server, os.X_OK)):
        parser.error(f"llama-server is not executable: {server}")

    all_entries = parse_registry(registry_path)
    entries = all_entries if args.include_comparisons else [e for e in all_entries if e["group"] == "primary"]
    if args.only:
        wanted = set(args.only)
        known = {e["id"] for e in all_entries}
        unknown = sorted(wanted - known)
        if unknown:
            parser.error("unknown model ID(s): " + ", ".join(unknown))
        entries = [e for e in all_entries if e["id"] in wanted]

    task_payload = load_tasks(task_path)
    tasks = task_payload["tasks"]
    if args.task:
        wanted_tasks = set(args.task)
        known_tasks = {t["id"] for t in tasks}
        unknown_tasks = sorted(wanted_tasks - known_tasks)
        if unknown_tasks:
            parser.error("unknown task ID(s): " + ", ".join(unknown_tasks))
        tasks = [t for t in tasks if t["id"] in wanted_tasks]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_root = results_dir / "raw" / "phase2" / run_id
    raw_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": run_id,
        "started_at_utc": now_utc(),
        "benchmark_version": task_payload.get("benchmark_version", "phase2-v0.1"),
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
            "threads": THREADS,
            "n_gpu_layers": 0,
            "context": CONTEXT,
            "temperature": TEMPERATURE,
            "seed": SEED,
            "max_tokens": MAX_TOKENS,
            "cache_prompt": False,
        },
    }

    print(f"Phase 2 run: {run_id}")
    print(f"Benchmark version: {meta['benchmark_version']}")
    print(f"Models: {len(entries)}")
    print(f"Tasks per model: {len(tasks)}")
    print(f"HF cache: {hf_cache}")
    if not args.dry_run:
        print(f"llama-server: {server}")
        print(f"Settings: threads={THREADS}, ngl=0, ctx={CONTEXT}, temp={TEMPERATURE}, seed={SEED}")

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
        print(f"Preflight complete: {len(resolved)}/{len(entries)} models resolved, {len(tasks)} tasks selected.")
        return 2 if preflight_failed else 0
    if preflight_failed:
        print("Preflight failed; fix missing/ambiguous models before capability testing.", file=sys.stderr)
        return 2

    system_prompt = task_payload.get(
        "system_prompt",
        "You are taking a deterministic multiple-choice benchmark. Answer the question without tools or external access."
    )
    rows = []
    any_failed = False

    for model_index, entry in enumerate(resolved, 1):
        model_id = entry["id"]
        model_raw = raw_root / model_id
        model_raw.mkdir(parents=True, exist_ok=True)
        port = free_port()
        server_log = model_raw / "server.log"
        cmd = [
            str(server), "-m", str(entry["model_path"]), "-t", str(THREADS), "-ngl", "0",
            "-c", str(CONTEXT), "--host", "127.0.0.1", "--port", str(port), "--alias", model_id,
        ]
        print(f"\n[{model_index}/{len(resolved)}] {model_id} — {entry['model']} {entry['quant']}")
        print("  server:", shlex.join(cmd))
        proc = None
        log_handle = None
        model_start = time.monotonic()
        try:
            env = os.environ.copy()
            env["HF_HUB_OFFLINE"] = "1"
            env["TRANSFORMERS_OFFLINE"] = "1"
            log_handle = server_log.open("wb")
            proc = subprocess.Popen(cmd, stdout=log_handle, stderr=subprocess.STDOUT, env=env)
            wait_for_server(port, proc, args.server_timeout)
            print(f"  ready in {time.monotonic() - model_start:.2f}s")

            for task_index, task in enumerate(tasks, 1):
                task_started = time.monotonic()
                raw_path = model_raw / f"{task['id']}.json"
                row = {
                    "run_id": run_id,
                    "model_id": model_id,
                    "model": entry["model"],
                    "quant": entry["quant"],
                    "task_id": task["id"],
                    "domain": task["domain"],
                    "category": task["category"],
                    "status": "pending",
                    "expected_answer": task["answer"],
                    "extracted_answer": "",
                    "correct": 0,
                    "extraction_method": "",
                    "response_text": "",
                    "http_status": "",
                    "elapsed_seconds": "",
                    "prompt_tokens": "",
                    "completion_tokens": "",
                    "error": "",
                    "raw_response_json": str(raw_path.relative_to(ROOT)) if raw_path.is_relative_to(ROOT) else str(raw_path),
                }
                try:
                    request_body = {
                        "model": model_id,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": format_prompt(task)},
                        ],
                        "temperature": TEMPERATURE,
                        "seed": SEED,
                        "max_tokens": MAX_TOKENS,
                        "stream": False,
                        "cache_prompt": False,
                    }
                    status, response = http_json(
                        f"http://127.0.0.1:{port}/v1/chat/completions",
                        request_body,
                        timeout=args.request_timeout,
                    )
                    elapsed = time.monotonic() - task_started
                    raw_path.write_text(json.dumps({
                        "task": task,
                        "request": request_body,
                        "http_status": status,
                        "response": response,
                        "elapsed_seconds": elapsed,
                    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    row["http_status"] = status
                    row["elapsed_seconds"] = round(elapsed, 6)
                    if status != 200:
                        raise RuntimeError(f"HTTP {status}: {response}")
                    content = response_content(response)
                    extracted, method = extract_choice(content)
                    usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
                    row.update({
                        "status": "ok",
                        "response_text": content.replace("\n", "\\n"),
                        "extracted_answer": extracted or "",
                        "extraction_method": method,
                        "correct": int(extracted == task["answer"]),
                        "prompt_tokens": usage.get("prompt_tokens", ""),
                        "completion_tokens": usage.get("completion_tokens", ""),
                    })
                    mark = "✓" if row["correct"] else "✗"
                    shown = extracted or "?"
                    print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: {shown} / {task['answer']} {mark}")
                except Exception as exc:
                    any_failed = True
                    row["status"] = "failed"
                    row["error"] = str(exc)
                    row["elapsed_seconds"] = round(time.monotonic() - task_started, 6)
                    if not raw_path.exists():
                        raw_path.write_text(json.dumps({"task": task, "error": str(exc)}, indent=2) + "\n", encoding="utf-8")
                    print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: FAILED — {exc}")
                rows.append(row)

        except Exception as exc:
            any_failed = True
            print(f"[failed] {model_id}: server_start: {exc}", file=sys.stderr)
            existing = {r["task_id"] for r in rows if r["model_id"] == model_id}
            for task in tasks:
                if task["id"] in existing:
                    continue
                rows.append({
                    "run_id": run_id, "model_id": model_id, "model": entry["model"], "quant": entry["quant"],
                    "task_id": task["id"], "domain": task["domain"], "category": task["category"],
                    "status": "failed", "expected_answer": task["answer"], "extracted_answer": "", "correct": 0,
                    "extraction_method": "", "response_text": "", "http_status": "", "elapsed_seconds": "",
                    "prompt_tokens": "", "completion_tokens": "", "error": f"server_start: {exc}", "raw_response_json": "",
                })
        finally:
            stop_server(proc)
            if log_handle is not None:
                log_handle.close()

        summaries = summarize(rows, resolved)
        current = next((s for s in summaries if s["model_id"] == model_id), None)
        if current:
            print(f"  score: {current['correct']}/{current['total']} = {current['accuracy']:.2f}%")
        write_outputs(results_dir, run_id, meta, rows, summaries)

    meta["finished_at_utc"] = now_utc()
    summaries = summarize(rows, resolved)
    json_path, csv_path = write_outputs(results_dir, run_id, meta, rows, summaries)

    print("\nPhase 2 complete.")
    print(f"JSON summary: {json_path}")
    print(f"CSV task results: {csv_path}")
    print(f"Raw outputs: {raw_root}")
    print("\nMODEL SUMMARY")
    for s in sorted(summaries, key=lambda x: (x["phase2_score"] or -1), reverse=True):
        reason = s["domains"].get("reasoning", {})
        know = s["domains"].get("knowledge", {})
        print(
            f"{s['model_id']:24} score={s['phase2_score']:6.2f}% raw={s['accuracy']:6.2f}% "
            f"reasoning={reason.get('accuracy', 0):6.2f}% knowledge={know.get('accuracy', 0):6.2f}% "
            f"parse={s['parse_rate']:6.2f}%"
        )

    if any_failed:
        print("One or more task/model executions failed; successful outputs were retained.", file=sys.stderr)
        return 2
    return 0


raise SystemExit(main())
PY
