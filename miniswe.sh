#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export LMB_ROOT_DIR="$ROOT_DIR"
exec "${PYTHON_BIN:-python3}" - "$@" <<'PY'
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import platform
import re
import resource
import shlex
import shutil
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
MAX_TOKENS = 1024
SERVER_START_TIMEOUT = 180
REQUEST_TIMEOUT = 240
TEST_WALL_TIMEOUT = 10
TEST_CPU_SECONDS = 4
TEST_MEMORY_BYTES = 768 * 1024 * 1024

DANGEROUS_IMPORT_ROOTS = {
    "os", "subprocess", "socket", "pathlib", "shutil", "tempfile", "ctypes",
    "multiprocessing", "threading", "asyncio", "urllib", "http", "ftplib", "ssl",
}
DANGEROUS_CALLS = {"open", "eval", "exec", "compile", "__import__", "input", "breakpoint"}


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
            "id": model_id, "model": model, "repository": repo, "quant": quant,
            "registry_size": registry_size, "group": section,
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
        required = {"id", "category", "issue", "files", "hidden_tests"}
        missing = sorted(required - set(task))
        if missing:
            raise RuntimeError(f"task missing fields {missing}: {task.get('id', '<unknown>')}")
        if task["id"] in seen:
            raise RuntimeError(f"duplicate task ID: {task['id']}")
        seen.add(task["id"])
        if not isinstance(task["files"], dict) or not task["files"]:
            raise RuntimeError(f"task {task['id']} has no repository files")
        for rel, content in task["files"].items():
            p = Path(rel)
            if p.is_absolute() or ".." in p.parts or not rel.endswith(".py"):
                raise RuntimeError(f"unsafe/non-Python repository path in {task['id']}: {rel}")
            if not isinstance(content, str):
                raise RuntimeError(f"non-string file content in {task['id']}: {rel}")
            ast.parse(content or "\n", filename=rel)
        if not isinstance(task["hidden_tests"], str) or not task["hidden_tests"].strip():
            raise RuntimeError(f"task {task['id']} has no hidden tests")
        ast.parse(task["hidden_tests"], filename=f"{task['id']}:hidden_tests")
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


def render_prompt(task: dict) -> str:
    chunks = ["Fix the repository issue below.", "", "ISSUE:", task["issue"], "", "REPOSITORY FILES:"]
    for path in sorted(task["files"]):
        chunks.extend([f"--- {path} ---", task["files"][path], f"--- end {path} ---", ""])
    chunks.extend([
        "Return ONLY the complete contents of files you changed using this exact format:",
        '<file path="relative/path.py">', "complete file contents", "</file>", "",
        "You may emit multiple <file> blocks. Do not include unchanged files. Do not add explanations or Markdown fences.",
    ])
    return "\n".join(chunks)


def strip_optional_fence(content: str) -> str:
    text = content.strip()
    m = re.fullmatch(r"```(?:python|py)?\s*\n(.*)\n```", text, re.IGNORECASE | re.DOTALL)
    return m.group(1).rstrip() + "\n" if m else content.strip("\n") + "\n"


def parse_replacements(text: str, allowed: set[str]) -> dict[str, str]:
    pattern = re.compile(r'<file\s+path=["\']([^"\']+)["\']\s*>\s*(.*?)\s*</file>', re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(text)
    if not matches:
        raise ValueError("no <file path=\"...\"> replacement blocks found")
    replacements: dict[str, str] = {}
    for raw_path, content in matches:
        path = raw_path.strip()
        if path not in allowed:
            raise ValueError(f"replacement path not allowed: {path}")
        if path in replacements:
            raise ValueError(f"duplicate replacement path: {path}")
        replacements[path] = strip_optional_fence(content)
    return replacements


def validate_replacements(replacements: dict[str, str]) -> tuple[bool, str]:
    for path, code in replacements.items():
        try:
            tree = ast.parse(code, filename=path)
        except SyntaxError as exc:
            return False, f"syntax_error:{path}:{exc.msg}:line={exc.lineno}"
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                names = []
            for name in names:
                if name.split(".")[0] in DANGEROUS_IMPORT_ROOTS:
                    return False, f"unsafe_import:{path}:{name}"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
                return False, f"unsafe_call:{path}:{node.func.id}"
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return False, f"unsafe_dunder:{path}:{node.attr}"
    return True, "ok"


def limit_child() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (TEST_CPU_SECONDS, TEST_CPU_SECONDS + 1))
    resource.setrlimit(resource.RLIMIT_AS, (TEST_MEMORY_BYTES, TEST_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024 * 1024, 4 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def bwrap_command(workdir: Path) -> list[str]:
    cmd = [
        "bwrap", "--die-with-parent", "--new-session", "--unshare-net", "--unshare-pid",
        "--unshare-ipc", "--unshare-uts", "--ro-bind", "/usr", "/usr",
    ]
    for path in ("/lib", "/lib64", "/etc"):
        if Path(path).exists() or Path(path).is_symlink():
            cmd += ["--ro-bind", path, path]
    cmd += [
        "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
        "--bind", str(workdir), "/work", "--chdir", "/work",
        "/usr/bin/python3", "-I", "/work/__bench_tests.py",
    ]
    return cmd


def prepare_repo(task: dict, artifact_dir: Path, replacements: dict[str, str]) -> Path:
    original = artifact_dir / "original"
    work = artifact_dir / "work"
    if original.exists():
        shutil.rmtree(original)
    if work.exists():
        shutil.rmtree(work)
    for base in (original, work):
        for rel, content in task["files"].items():
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    for rel, content in replacements.items():
        (work / rel).write_text(content, encoding="utf-8")
    (work / "__bench_tests.py").write_text(task["hidden_tests"], encoding="utf-8")
    return work


def run_hidden_tests(task: dict, artifact_dir: Path, replacements: dict[str, str]) -> tuple[dict, str, str, float]:
    work = prepare_repo(task, artifact_dir, replacements)
    started = time.monotonic()
    try:
        p = subprocess.run(
            bwrap_command(work.resolve()), capture_output=True, text=True, timeout=TEST_WALL_TIMEOUT,
            env={"PATH": "/usr/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
            preexec_fn=limit_child, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        return {"status": "timeout", "passed": 0, "total": 1}, exc.stdout or "", exc.stderr or "", elapsed
    elapsed = time.monotonic() - started
    parsed = None
    for line in reversed(p.stdout.splitlines()):
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and {"status", "passed", "total"} <= set(obj):
                parsed = obj
                break
        except json.JSONDecodeError:
            pass
    if parsed is None:
        parsed = {"status": f"sandbox_exit_{p.returncode}", "passed": 0, "total": 1}
    return parsed, p.stdout, p.stderr, elapsed


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
    summaries = []
    for entry in entries:
        rs = by_model.get(entry["id"], [])
        scores = [float(r.get("task_score", 0.0)) for r in rs]
        summaries.append({
            "model_id": entry["id"], "model": entry["model"], "quant": entry["quant"],
            "solved": sum(r.get("result") == "solved" for r in rs),
            "partial": sum(r.get("result") == "partial" for r in rs),
            "failed": sum(r.get("result") == "failed" for r in rs),
            "tasks": len(rs),
            "phase4_score": round(sum(scores) / len(scores), 2) if scores else None,
        })
    return summaries


def write_outputs(results_dir: Path, run_id: str, meta: dict, rows: list[dict], summaries: list[dict]) -> tuple[Path, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / f"phase4-{run_id}.json"
    csv_path = results_dir / f"phase4-{run_id}.csv"
    payload = {"schema_version": "phase4.v0.1", "run": meta, "models": summaries, "results": rows}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(text, encoding="utf-8")
    (results_dir / "phase4-latest.json").write_text(text, encoding="utf-8")
    fields = [
        "run_id", "model_id", "model", "quant", "task_id", "category", "status", "result",
        "passed_checks", "total_checks", "task_score", "changed_files", "generation_seconds",
        "test_seconds", "prompt_tokens", "completion_tokens", "failure_type", "artifact_dir", "error",
    ]
    for out in (csv_path, results_dir / "phase4-latest.csv"):
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4 compact MiniSWE repository-level benchmark")
    parser.add_argument("--registry", default=str(ROOT / "docs" / "MODEL_REGISTRY.md"))
    parser.add_argument("--tasks", default=str(ROOT / "tasks" / "phase4_v0.1.json"))
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
    if not args.dry_run and shutil.which("bwrap") is None:
        parser.error("bubblewrap (bwrap) is required for sandboxed repository tests")

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
    raw_root = results_dir / "raw" / "phase4" / run_id
    raw_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": run_id, "started_at_utc": now_utc(),
        "benchmark_version": task_payload.get("benchmark_version", "phase4-v0.1"),
        "task_file": str(task_path), "registry_path": str(registry_path),
        "hostname": platform.node(), "platform": platform.platform(), "kernel": platform.release(),
        "hf_cache": str(hf_cache), "llama_cpp_dir": str(llama_cpp_dir.resolve()),
        "llama_cpp_git_commit": command_text(["git", "-C", str(llama_cpp_dir), "rev-parse", "HEAD"]),
        "llama_server": str(server),
        "llama_server_version": None if args.dry_run else command_text([str(server), "--version"]),
        "settings": {
            "threads": THREADS, "n_gpu_layers": 0, "context": CONTEXT, "temperature": TEMPERATURE,
            "seed": SEED, "max_tokens": MAX_TOKENS, "cache_prompt": False, "reasoning_effort": "none",
            "sandbox": "bubblewrap", "network": "disabled", "test_wall_timeout_seconds": TEST_WALL_TIMEOUT,
            "test_cpu_seconds": TEST_CPU_SECONDS, "test_memory_bytes": TEST_MEMORY_BYTES,
            "patch_format": "full-file replacement blocks",
        },
    }

    print(f"Phase 4 run: {run_id}")
    print(f"Benchmark version: {meta['benchmark_version']}")
    print(f"Models: {len(entries)}")
    print(f"Tasks per model: {len(tasks)}")
    print(f"HF cache: {hf_cache}")
    if not args.dry_run:
        print(f"llama-server: {server}")
        print(f"Settings: threads={THREADS}, ngl=0, ctx={CONTEXT}, temp={TEMPERATURE}, seed={SEED}, reasoning=none, max_tokens={MAX_TOKENS}")
        print(f"Sandbox: bwrap, network=off, wall={TEST_WALL_TIMEOUT}s, cpu={TEST_CPU_SECONDS}s, mem={TEST_MEMORY_BYTES // (1024*1024)}MiB")

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
        print(f"Preflight complete: {len(resolved)}/{len(entries)} models resolved, {len(tasks)} MiniSWE tasks selected.")
        for task in tasks:
            print(f"  {task['id']}: {task['category']} ({len(task['files'])} visible files)")
        return 2 if preflight_failed else 0
    if preflight_failed:
        print("Preflight failed; fix missing/ambiguous models before MiniSWE testing.", file=sys.stderr)
        return 2

    system_prompt = task_payload.get("system_prompt", "Fix the repository and return replacement files only.")
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
                    "task_id": task["id"], "category": task["category"], "status": "pending", "result": "failed",
                    "passed_checks": 0, "total_checks": 0, "task_score": 0.0, "changed_files": "",
                    "generation_seconds": "", "test_seconds": "", "prompt_tokens": "", "completion_tokens": "",
                    "failure_type": "", "artifact_dir": str(artifact_dir.relative_to(ROOT)) if artifact_dir.is_relative_to(ROOT) else str(artifact_dir), "error": "",
                }
                try:
                    request_body = {
                        "model": model_id,
                        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": render_prompt(task)}],
                        "temperature": TEMPERATURE, "seed": SEED, "max_tokens": MAX_TOKENS,
                        "stream": False, "cache_prompt": False, "reasoning_effort": "none",
                    }
                    gen_start = time.monotonic()
                    status, response = http_json(f"http://127.0.0.1:{port}/v1/chat/completions", request_body, timeout=args.request_timeout)
                    gen_elapsed = time.monotonic() - gen_start
                    row["generation_seconds"] = round(gen_elapsed, 6)
                    (artifact_dir / "response.json").write_text(json.dumps({"task": {"id": task["id"], "category": task["category"], "issue": task["issue"], "files": task["files"]}, "request": request_body, "http_status": status, "response": response, "generation_seconds": gen_elapsed}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    if status != 200: raise RuntimeError(f"HTTP {status}: {response}")

                    content = response_content(response)
                    (artifact_dir / "model_output.txt").write_text(content, encoding="utf-8")
                    usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
                    row["prompt_tokens"] = usage.get("prompt_tokens", ""); row["completion_tokens"] = usage.get("completion_tokens", "")

                    try:
                        replacements = parse_replacements(content, set(task["files"]))
                    except ValueError as exc:
                        row["status"] = "ok"; row["failure_type"] = "patch_parse_error"; row["error"] = str(exc)
                        print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: FAIL (patch_parse_error)")
                        rows.append(row); continue

                    row["changed_files"] = ";".join(sorted(replacements))
                    valid, reason = validate_replacements(replacements)
                    if not valid:
                        row["status"] = "ok"; row["failure_type"] = reason.split(":", 1)[0]; row["error"] = reason
                        print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: FAIL ({reason})")
                        rows.append(row); continue

                    result, stdout, stderr, test_elapsed = run_hidden_tests(task, artifact_dir, replacements)
                    (artifact_dir / "test_stdout.txt").write_text(stdout, encoding="utf-8")
                    (artifact_dir / "test_stderr.txt").write_text(stderr, encoding="utf-8")
                    row["test_seconds"] = round(test_elapsed, 6)
                    passed = int(result.get("passed", 0)); total = int(result.get("total", 0))
                    row["passed_checks"] = passed; row["total_checks"] = total
                    row["task_score"] = round((passed / total * 100) if total else 0.0, 2); row["status"] = "ok"
                    if total and passed == total: row["result"] = "solved"
                    elif passed > 0: row["result"] = "partial"
                    else: row["result"] = "failed"
                    if str(result.get("status", "")).startswith("sandbox_exit_") or result.get("status") == "timeout":
                        row["failure_type"] = str(result.get("status"))
                    mark = "SOLVED" if row["result"] == "solved" else f"{row['result'].upper()} ({passed}/{total})"
                    print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: {mark}")
                except Exception as exc:
                    infrastructure_failed = True; row["status"] = "failed"; row["failure_type"] = "execution_error"; row["error"] = str(exc)
                    print(f"  [{task_index:02d}/{len(tasks):02d}] {task['id']}: ERROR — {exc}")
                rows.append(row)
        except Exception as exc:
            infrastructure_failed = True
            print(f"[failed] {model_id}: server_start: {exc}", file=sys.stderr)
            existing = {r["task_id"] for r in rows if r["model_id"] == model_id}
            for task in tasks:
                if task["id"] in existing: continue
                rows.append({"run_id": run_id, "model_id": model_id, "model": entry["model"], "quant": entry["quant"], "task_id": task["id"], "category": task["category"], "status": "failed", "result": "failed", "passed_checks": 0, "total_checks": 0, "task_score": 0.0, "changed_files": "", "generation_seconds": "", "test_seconds": "", "prompt_tokens": "", "completion_tokens": "", "failure_type": "server_start", "artifact_dir": "", "error": str(exc)})
        finally:
            stop_server(proc)
            if log_handle is not None: log_handle.close()

        summaries = summarize(rows, resolved)
        current = next((s for s in summaries if s["model_id"] == model_id), None)
        if current:
            print(f"  MiniSWE score: {current['phase4_score']:.2f}% solved={current['solved']}/{current['tasks']} partial={current['partial']}")
        write_outputs(results_dir, run_id, meta, rows, summaries)

    meta["finished_at_utc"] = now_utc()
    summaries = summarize(rows, resolved)
    json_path, csv_path = write_outputs(results_dir, run_id, meta, rows, summaries)
    print("\nPhase 4 complete.")
    print(f"JSON summary: {json_path}")
    print(f"CSV task results: {csv_path}")
    print(f"Raw outputs: {raw_root}")
    print("\nMODEL SUMMARY")
    for s in sorted(summaries, key=lambda x: (x["phase4_score"] or -1), reverse=True):
        print(f"{s['model_id']:24} MiniSWE={s['phase4_score']:6.2f}% solved={s['solved']:2}/{s['tasks']:2} partial={s['partial']:2}")
    if infrastructure_failed:
        print("One or more infrastructure executions failed; successful outputs were retained.", file=sys.stderr)
        return 2
    return 0

raise SystemExit(main())
PY
