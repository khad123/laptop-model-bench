#!/usr/bin/env python3
"""A small, local launcher for repeatable llama.cpp app-generation runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROMPT_CANDIDATES = (
    HERE / "local-app-prompts.md",
    HERE.parent / "tasks" / "local-app-prompts.md",
)
PROMPT_FILE = next((path for path in PROMPT_CANDIDATES if path.is_file()), PROMPT_CANDIDATES[0])
DEFAULT_CLI = Path.home() / "Models/llama.cpp-k2-current/build/bin/llama-cli"
DEFAULT_RESULTS = Path.home() / "laptop-model-bench/results"
TASK_TIMEOUT_MINUTES = {
    "pocket-dodge": 10,
    "switchyard": 15,
    "workshop-queue": 15,
    "tower-defense": 25,
    "fuel-stop": 30,
    "pocket-courier": 20,
}

ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "blue": "\033[34m",
}


def paint(value: str, color: str, enabled: bool = True) -> str:
    if not enabled:
        return value
    return f"{ANSI[color]}{value}{ANSI['reset']}"


def slug(value: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return result.lower() or "model"


def parse_prompts(source: Path = PROMPT_FILE) -> list[dict[str, str]]:
    """Read all numbered copy-ready prompt blocks without changing their contents."""
    text = source.read_text(encoding="utf-8")
    matches = re.finditer(
        r"^##\s+\d+\.\s+(.+?)\s*\n\s*```text\s*\n(.*?)\n```",
        text,
        re.MULTILINE | re.DOTALL,
    )
    prompts = []
    for match in matches:
        name = match.group(1).strip()
        body = match.group(2) + "\n"
        prompts.append({"name": name, "id": slug(name), "text": body})
    if not prompts:
        raise ValueError(f"No prompt blocks found in {source}")
    return prompts


def find_models() -> list[Path]:
    """Find installed GGUFs in Hugging Face snapshot folders, deduplicated."""
    hub = Path(os.environ.get("HF_HUB_CACHE", Path.home() / ".cache/huggingface/hub"))
    models: dict[str, Path] = {}
    if not hub.is_dir():
        return []
    for model_dir in sorted(hub.glob("models--*")):
        snapshots = model_dir / "snapshots"
        main_ref = model_dir / "refs" / "main"
        if main_ref.is_file():
            revision = main_ref.read_text(encoding="utf-8").strip()
            snapshot_dirs = [snapshots / revision] if revision else []
        else:
            # Some caches have no main ref (for example, snapshots downloaded
            # by commit hash). Keep those discoverable as a fallback.
            snapshot_dirs = sorted(snapshots.iterdir()) if snapshots.is_dir() else []
        for snapshot in snapshot_dirs:
            for candidate in sorted(snapshot.glob("*.gguf")):
                # mmproj files are image/audio projectors, not standalone models.
                if candidate.name.lower().startswith("mmproj"):
                    continue
                try:
                    resolved = candidate.resolve(strict=True)
                except (FileNotFoundError, OSError):
                    continue
                if resolved.is_file():
                    # Keep the snapshot symlink path: it carries repo and revision
                    # information that disappears if we store only the blob path.
                    models[str(resolved)] = candidate.absolute()
    return sorted(models.values(), key=lambda path: (path.name.lower(), str(path).lower()))


def model_label(path: Path) -> str:
    repo = ""
    for parent in path.parents:
        if parent.name.startswith("models--"):
            repo = parent.name.removeprefix("models--").replace("--", "/")
            break
    return f"{path.name}  ·  {repo}" if repo else path.name


def prompt_token_estimate(text: str) -> int:
    """Roughly estimate tokens for a pre-run heads-up; runtime stats are authoritative."""
    return max(1, round(len(text.encode("utf-8")) / 3.7))


def choose(items: list, title: str, describe, color: bool) -> object:
    print(paint(f"\n{title}", "bold", color))
    for index, item in enumerate(items, 1):
        print(f"  {paint(str(index), 'cyan', color)}. {describe(item)}")
    while True:
        raw = input("Choose a number (or q to quit): ").strip().lower()
        if raw in {"q", "quit", "exit"}:
            raise SystemExit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1]
        print("Please enter one of the listed numbers.")


def detect_cli(argument: str | None) -> Path:
    candidates = [Path(argument).expanduser()] if argument else []
    env_cli = os.environ.get("LLAMA_CLI")
    if env_cli and not argument:
        candidates.append(Path(env_cli).expanduser())
    candidates.extend([DEFAULT_CLI, Path(shutil.which("llama-cli") or "/nonexistent")])
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    raise FileNotFoundError(
        "Could not find an executable llama-cli. Pass --llama-cli /path/to/llama-cli "
        "or set LLAMA_CLI."
    )


def extract_assistant(text: str) -> tuple[str, str]:
    markers = ("\nAssistant:\n", "\nassistant:\n")
    for marker in markers:
        if marker in text:
            return text.rsplit(marker, 1)[1], "assistant-marker"
    return text, "raw-output"


def parse_stats(log: str) -> dict[str, float | int | None]:
    stats: dict[str, float | int | None] = {
        "prompt_tokens": None,
        "generated_tokens": None,
        "prompt_tokens_per_second": None,
        "generation_tokens_per_second": None,
    }
    prompt = re.search(
        r"prompt eval time\s*=.*?/\s*(\d+)\s+tokens.*?([\d.]+)\s+tokens per second",
        log,
        re.IGNORECASE,
    )
    generated = re.search(
        r"eval time\s*=.*?/\s*(\d+)\s+runs.*?([\d.]+)\s+tokens per second",
        log,
        re.IGNORECASE,
    )
    compact = re.search(
        r"Prompt:\s*([\d.]+)\s*t/s\s*\|\s*Generation:\s*([\d.]+)\s*t/s",
        log,
        re.IGNORECASE,
    )
    if prompt:
        stats["prompt_tokens"] = int(prompt.group(1))
        stats["prompt_tokens_per_second"] = float(prompt.group(2))
    if generated:
        stats["generated_tokens"] = int(generated.group(1))
        stats["generation_tokens_per_second"] = float(generated.group(2))
    if compact:
        stats["prompt_tokens_per_second"] = float(compact.group(1))
        stats["generation_tokens_per_second"] = float(compact.group(2))
    return stats


def metadata_for_model(path: Path) -> dict[str, str | None]:
    repo = None
    revision = None
    for parent in path.parents:
        if parent.name == "snapshots" and parent.parent.name.startswith("models--"):
            revision = path.parent.name
            repo = parent.parent.name.removeprefix("models--").replace("--", "/")
            break
    quant = re.search(
        r"(?:^|[-_])(IQ\d+_[A-Z0-9]+(?:_[A-Z0-9]+)?|Q\d+_[A-Z0-9]+(?:_[A-Z0-9]+)?|F16|BF16|Q\d+_\d+)(?:[-_.]|$)",
        path.name,
        re.I,
    )
    return {
        "file": path.name,
        "path": str(path),
        "repository": repo,
        "revision": revision,
        "quantization": quant.group(1).upper() if quant else None,
    }


def run_streamed(command: list[str], log_path: Path, timeout_seconds: int, color: bool):
    """Run llama-cli while mirroring its output, with a timeout and preserved log."""
    started = time.monotonic()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    chunks: queue.Queue[bytes | None] = queue.Queue()

    def read_output():
        assert process.stdout is not None
        try:
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                chunks.put(chunk)
        finally:
            chunks.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    timed_out = False
    ended = False
    with log_path.open("wb") as log_file:
        try:
            while not ended:
                if time.monotonic() - started >= timeout_seconds and process.poll() is None:
                    timed_out = True
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                try:
                    chunk = chunks.get(timeout=0.1)
                except queue.Empty:
                    if process.poll() is not None and not reader.is_alive():
                        break
                    continue
                if chunk is None:
                    ended = True
                else:
                    log_file.write(chunk)
                    log_file.flush()
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
        except KeyboardInterrupt:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            reader.join(timeout=2)
            while True:
                try:
                    queued = chunks.get_nowait()
                except queue.Empty:
                    break
                if queued:
                    log_file.write(queued)
            log_file.flush()
            raise
    return process.wait(), time.monotonic() - started, timed_out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Choose an installed GGUF and a saved app prompt, then run llama-cli locally."
    )
    parser.add_argument("--model", help="GGUF model path; otherwise choose from the HF cache")
    parser.add_argument("--task", help="Prompt ID, such as pocket-dodge or fuel-stop")
    parser.add_argument("--prompt-file", type=Path, default=PROMPT_FILE, help="Markdown source containing prompt blocks")
    parser.add_argument("--llama-cli", help="Path to llama-cli; can also use LLAMA_CLI")
    parser.add_argument("--run-root", type=Path, help="Shared run folder for organizing multiple model/task results")
    parser.add_argument("--context", type=int, default=32768, help="Context window (default: 32768)")
    parser.add_argument("--threads", type=int, default=4, help="CPU threads (default: 4)")
    parser.add_argument("--max-tokens", type=int, default=8192, help="Maximum generated tokens (default: 8192)")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature (default: 0)")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed (default: 42)")
    parser.add_argument("--reasoning", choices=("off", "on", "auto"), default="off", help="Reasoning mode (default: off)")
    parser.add_argument("--timeout-minutes", type=int, help="Override the task's time limit")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal colors")
    parser.add_argument("--yes", action="store_true", help="Skip the final settings confirmation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    color = sys.stdout.isatty() and not args.no_color

    try:
        cli = detect_cli(args.llama_cli)
        prompts = parse_prompts(args.prompt_file.expanduser())
    except (OSError, ValueError) as exc:
        print(f"Setup error: {exc}", file=sys.stderr)
        return 2

    if args.model:
        model = Path(os.path.abspath(Path(args.model).expanduser()))
        if not model.is_file() or model.suffix.lower() != ".gguf":
            print(f"Model file not found or not a GGUF: {model}", file=sys.stderr)
            return 2
    else:
        models = find_models()
        if not models:
            print("No GGUF snapshots found in the Hugging Face cache. Use --model /path/to/model.gguf.", file=sys.stderr)
            return 2
        model = choose(models, "Choose a model", model_label, color)

    by_id = {prompt["id"]: prompt for prompt in prompts}
    if args.task:
        task = by_id.get(slug(args.task))
        if not task:
            print("Unknown task. Choose one of: " + ", ".join(by_id), file=sys.stderr)
            return 2
    else:
        task = choose(prompts, "Choose a project prompt", lambda item: item["name"], color)

    timeout_minutes = args.timeout_minutes or TASK_TIMEOUT_MINUTES.get(task["id"], 15)
    if min(args.context, args.threads, args.max_tokens, timeout_minutes) <= 0:
        print("Context, threads, output tokens, and timeout must all be greater than zero.", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    root = args.run_root.expanduser() if args.run_root else DEFAULT_RESULTS / f"local-app-benchmark-python-{stamp}"
    model_meta = metadata_for_model(model)
    model_id = slug(model.stem)
    task_dir = root / model_id / task["id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    if any(task_dir.iterdir()):
        attempt_stamp = stamp
        task_dir = task_dir / f"attempt-{attempt_stamp}"
        suffix = 2
        while task_dir.exists():
            task_dir = task_dir.parent / f"attempt-{attempt_stamp}-{suffix}"
            suffix += 1
        task_dir.mkdir(parents=True, exist_ok=False)

    prompt_path = task_dir / "prompt.txt"
    prompt_path.write_text(task["text"], encoding="utf-8")
    output_path = task_dir / "cli-transcript.txt"
    log_path = task_dir / "run.log"
    timeout_seconds = timeout_minutes * 60

    command = [
        str(cli), "-m", str(model), "-t", str(args.threads), "-ngl", "0",
        "-c", str(args.context), "-n", str(args.max_tokens),
        "--reasoning", args.reasoning,
        "--temp", str(args.temperature), "--seed", str(args.seed),
        "--single-turn", "--simple-io", "--no-display-prompt",
        "--show-timings", "--perf", "-f", str(prompt_path), "-o", str(output_path),
    ]

    print("\n" + paint("LOCAL APP BENCHMARK", "bold", color))
    print("─" * 72)
    print(f"Model       {model_label(model)}")
    print(f"Project     {task['name']}")
    preview = " ".join(task["text"].split())
    if len(preview) > 220:
        preview = preview[:217].rstrip() + "..."
    print(f"Prompt      {preview}")
    print(f"Context     {args.context:,} tokens  ·  prompt estimate ~{prompt_token_estimate(task['text']):,}")
    print(f"Output cap  {args.max_tokens:,} tokens  ·  threads {args.threads}  ·  GPU layers 0")
    print(f"Reasoning   {args.reasoning}  ·  temperature {args.temperature:g}  ·  seed {args.seed}")
    print(f"Time limit  {timeout_minutes} minutes")
    print(f"Save to     {task_dir}")
    print("─" * 72)
    print(paint("The prompt + generated output share the context window. A run that reaches a limit is saved as-is.", "dim", color))
    if not args.yes:
        try:
            answer = input("Start this run? [Y/n] ").strip().lower()
        except EOFError:
            answer = "n"
        if answer not in {"", "y", "yes"}:
            print("Run cancelled. The prompt copy remains in the run folder.")
            return 0

    version_result = subprocess.run([str(cli), "--version"], capture_output=True, text=True, check=False)
    start = dt.datetime.now().astimezone()
    run_started_clock = time.monotonic()
    try:
        exit_code, elapsed, timed_out = run_streamed(command, log_path, timeout_seconds, color)
        interrupted = False
    except KeyboardInterrupt:
        interrupted = True
        timed_out = False
        exit_code = 130
        elapsed = time.monotonic() - run_started_clock
    end = dt.datetime.now().astimezone()

    transcript = output_path.read_text(encoding="utf-8", errors="replace") if output_path.exists() else ""
    if not transcript and log_path.exists():
        transcript = log_path.read_text(encoding="utf-8", errors="replace")
        extraction = "partial-run-log-fallback"
    else:
        extraction = "llama-cli-output-file"
    response, response_extraction = extract_assistant(transcript)
    response_path = task_dir / "response.txt"
    response_path.write_text(response, encoding="utf-8")

    html_status = "not-html"
    trimmed = response.strip()
    html = trimmed
    if trimmed.startswith("```"):
        fence_match = re.fullmatch(r"```(?:html)?\s*\n(.*?)\n```\s*", trimmed, flags=re.I | re.S)
        if fence_match:
            html = fence_match.group(1)
            html_status = "outer-markdown-fences-removed"
    if html.lower().startswith("<!doctype html>"):
        (task_dir / "index.html").write_text(html.rstrip() + "\n", encoding="utf-8")
        if html_status == "not-html":
            html_status = "complete-html-copy"

    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    stats = parse_stats(log_text)
    used = None
    if stats["prompt_tokens"] is not None and stats["generated_tokens"] is not None:
        used = int(stats["prompt_tokens"]) + int(stats["generated_tokens"])
    status = "timed-out" if timed_out else "interrupted" if interrupted else "completed" if exit_code == 0 else "failed"
    metadata = {
        "status": status,
        "exit_code": exit_code,
        "model": model_meta,
        "model_id": model_id,
        "project": task["name"],
        "project_id": task["id"],
        "prompt_file": str(prompt_path),
        "llama_cli": str(cli),
        "llama_cpp_build": version_result.stdout.strip() or version_result.stderr.strip() or None,
        "command": command,
        "settings": {
            "threads": args.threads,
            "gpu_layers": 0,
            "context_tokens": args.context,
            "max_generated_tokens": args.max_tokens,
            "reasoning": args.reasoning,
            "temperature": args.temperature,
            "seed": args.seed,
            "timeout_minutes": timeout_minutes,
        },
        "started_at": start.isoformat(timespec="seconds"),
        "ended_at": end.isoformat(timespec="seconds"),
        "elapsed_seconds": round(elapsed, 2),
        "timings": stats,
        "estimated_context_used_tokens": used,
        "estimated_context_used_percent": round(100 * used / args.context, 2) if used is not None else None,
        "output_capture": extraction,
        "response_extraction": response_extraction,
        "launch_html": html_status,
        "response_file": str(response_path),
        "transcript_file": str(output_path) if output_path.exists() else None,
        "log_file": str(log_path),
    }
    (task_dir / "run-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print("\n" + paint("RUN SUMMARY", "bold", color))
    print(f"Status      {status}  ·  {elapsed / 60:.1f} minutes")
    print(f"Prompt      {stats['prompt_tokens'] if stats['prompt_tokens'] is not None else 'not reported'} tokens")
    print(f"Generated   {stats['generated_tokens'] if stats['generated_tokens'] is not None else 'not reported'} tokens")
    print(f"Prompt rate {stats['prompt_tokens_per_second'] if stats['prompt_tokens_per_second'] is not None else 'not reported'} tokens/s")
    print(f"Gen rate    {stats['generation_tokens_per_second'] if stats['generation_tokens_per_second'] is not None else 'not reported'} tokens/s")
    if used is not None:
        print(f"Context     ~{used:,}/{args.context:,} tokens ({100 * used / args.context:.1f}%)")
    print(f"Saved       {task_dir}")
    print(f"HTML        {html_status}")
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
