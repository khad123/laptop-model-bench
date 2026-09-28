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
DEFAULT_ECC_DIR = Path.home() / "Models/ECC"
ECC_SKILL_PATHS = (
    Path("skills/frontend-design-direction/SKILL.md"),
    Path("skills/accessibility/SKILL.md"),
)
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
BACK = object()


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


def load_ecc_guidance(ecc_dir: Path) -> tuple[str, dict[str, object]]:
    """Load the small ECC skill set used for self-contained web app prompts."""
    ecc_dir = ecc_dir.expanduser().resolve()
    skill_docs: list[tuple[str, str, str]] = []
    for relative_path in ECC_SKILL_PATHS:
        skill_path = ecc_dir / relative_path
        if not skill_path.is_file():
            raise FileNotFoundError(
                f"ECC skill is missing: {skill_path}. Update the ECC checkout or pass --ecc-dir."
            )
        skill_docs.append(
            (relative_path.parent.name, str(relative_path), skill_path.read_text(encoding="utf-8"))
        )

    revision_result = subprocess.run(
        ["git", "-C", str(ecc_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    revision = revision_result.stdout.strip() if revision_result.returncode == 0 else "unversioned"
    sections = [
        "ECC-GUIDED GENERATION\n"
        "Apply the ECC skill guidance below while producing the requested project. "
        "This is a single-response generation run: do not call tools, create a plan "
        "outside the requested deliverable, or describe your process. The project "
        "prompt remains authoritative for the deliverable and final output format.\n"
    ]
    for name, relative_path, content in skill_docs:
        sections.append(f"\n--- ECC SKILL: {name} ({relative_path}) ---\n{content.rstrip()}\n")
    metadata: dict[str, object] = {
        "repository": "https://github.com/affaan-m/ECC",
        "directory": str(ecc_dir),
        "revision": revision,
        "skills": [
            {"name": name, "path": relative_path, "characters": len(content)}
            for name, relative_path, content in skill_docs
        ],
    }
    return "\n".join(sections), metadata


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


def choose(items: list, title: str, describe, color: bool, allow_back: bool = False) -> object:
    print(paint(f"\n{title}", "bold", color))
    for index, item in enumerate(items, 1):
        print(f"  {paint(str(index), 'cyan', color)}. {describe(item)}")
    if allow_back:
        print(f"  {paint('0', 'cyan', color)}. Back to previous menu")
    while True:
        prompt = "Choose a number (0 to go back, or q to quit): " if allow_back else "Choose a number (or q to quit): "
        raw = input(prompt).strip().lower()
        if raw in {"q", "quit", "exit"}:
            raise SystemExit(0)
        if raw == "0" and allow_back:
            return BACK
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1]
        print("Please enter one of the listed numbers" + (", 0 to go back," if allow_back else "") + " or q to quit.")


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


def html_artifact(response: str) -> tuple[str, str, bool]:
    """Normalize HTML-like output and classify it as complete, partial, or absent."""
    source = response.strip().lstrip("\ufeff").strip()
    fences_removed = False
    opening_fence = re.match(r"```(?:html)?[ \t]*\r?\n", source, flags=re.I)
    if opening_fence:
        source = source[opening_fence.end():]
        fences_removed = True
        closing_fence = re.search(r"\n```[ \t]*$", source)
        if closing_fence:
            source = source[:closing_fence.start()]

    source = source.strip()
    starts_as_html = re.match(
        r"(?:<!doctype\s+html\b|<html(?:[\s>/]|$))", source, flags=re.I
    )
    if not starts_as_html:
        return "", "not-html", fences_removed

    has_closing_html = bool(re.search(r"</html\s*>\s*$", source, flags=re.I))
    status = "complete-html-copy" if has_closing_html else "partial-html-copy"
    return source, status, fences_removed


def artifact_model_slug(model_stem: str) -> str:
    """Create a readable, filesystem-safe model segment for HTML filenames."""
    result = re.sub(r"[^a-zA-Z0-9]+", "-", model_stem.strip()).strip("-")
    return result.lower() or "model"


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
    parser.add_argument("--mode", choices=("normal", "ecc"), help="Run mode; otherwise choose interactively")
    parser.add_argument(
        "--ecc-dir",
        type=Path,
        default=Path(os.environ.get("ECC_DIR", DEFAULT_ECC_DIR)),
        help=f"ECC checkout used in ECC mode (default: {os.environ.get('ECC_DIR', DEFAULT_ECC_DIR)})",
    )
    parser.add_argument("--prompt-file", type=Path, default=PROMPT_FILE, help="Markdown source containing prompt blocks")
    parser.add_argument("--llama-cli", help="Path to llama-cli; can also use LLAMA_CLI")
    parser.add_argument("--run-root", type=Path, help="Shared run folder for organizing multiple model/task results")
    parser.add_argument("--context", type=int, default=32768, help="Context window (default: 32768)")
    parser.add_argument("--threads", type=int, default=4, help="CPU threads (default: 4)")
    parser.add_argument("--gpu-layers", default="0", help="GPU layers to offload: 0, a number, auto, or all (default: 0)")
    parser.add_argument("--max-tokens", type=int, default=8192, help="Maximum generated tokens (default: 8192)")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature (default: 0)")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed (default: 42)")
    parser.add_argument("--dry-multiplier", type=float, default=0.0, help="DRY repetition penalty strength (default: 0, disabled)")
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

    mode = args.mode
    model = None
    task = None
    menu_steps = []
    if mode is None and sys.stdin.isatty():
        menu_steps.append((
            "mode",
            ["normal", "ecc"],
            "Choose a run mode",
            lambda item: "Normal — prompt-only baseline" if item == "normal" else "ECC — add selected skill guidance",
        ))
    elif mode is None:
        # Preserve prompt-only behavior for existing non-interactive calls.
        mode = "normal"

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
        menu_steps.append(("model", models, "Choose a model", model_label))

    by_id = {prompt["id"]: prompt for prompt in prompts}
    if args.task:
        task = by_id.get(slug(args.task))
        if not task:
            print("Unknown task. Choose one of: " + ", ".join(by_id), file=sys.stderr)
            return 2
    else:
        menu_steps.append(("task", prompts, "Choose a project prompt", lambda item: item["name"]))

    selections = {"mode": mode, "model": model, "task": task}
    menu_index = 0
    while menu_index < len(menu_steps):
        key, items, title, describe = menu_steps[menu_index]
        selected = choose(items, title, describe, color, allow_back=menu_index > 0)
        if selected is BACK:
            menu_index -= 1
            continue
        selections[key] = selected
        menu_index += 1

    mode = selections["mode"]
    model = selections["model"]
    task = selections["task"]
    if mode is None or model is None or task is None:
        print("Could not complete the run selections.", file=sys.stderr)
        return 2

    ecc_guidance = ""
    ecc_metadata = None
    if mode == "ecc":
        try:
            ecc_guidance, ecc_metadata = load_ecc_guidance(args.ecc_dir)
        except (OSError, ValueError) as exc:
            print(f"ECC setup error: {exc}", file=sys.stderr)
            return 2

    timeout_minutes = args.timeout_minutes or TASK_TIMEOUT_MINUTES.get(task["id"], 15)
    gpu_layers = str(args.gpu_layers).lower()
    if gpu_layers not in {"auto", "all"}:
        try:
            if int(gpu_layers) < 0:
                raise ValueError
        except ValueError:
            print("GPU layers must be 0, a positive integer, auto, or all.", file=sys.stderr)
            return 2
    if min(args.context, args.threads, args.max_tokens, timeout_minutes) <= 0 or args.dry_multiplier < 0:
        print("Context, threads, output tokens, and timeout must be positive; DRY multiplier cannot be negative.", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    default_run_prefix = "local-app-benchmark-python" if mode == "normal" else "local-app-benchmark-ecc"
    root = args.run_root.expanduser() if args.run_root else DEFAULT_RESULTS / f"{default_run_prefix}-{stamp}"
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
    effective_prompt = f"{ecc_guidance}\n\nPROJECT PROMPT\n\n{task['text']}" if mode == "ecc" else task["text"]
    prompt_path.write_text(effective_prompt, encoding="utf-8")
    if mode == "ecc":
        (task_dir / "project-prompt.txt").write_text(task["text"], encoding="utf-8")
    output_path = task_dir / "cli-transcript.txt"
    log_path = task_dir / "run.log"
    timeout_seconds = timeout_minutes * 60

    command = [
        str(cli), "-m", str(model), "-t", str(args.threads), "-ngl", gpu_layers,
        "-c", str(args.context), "-n", str(args.max_tokens),
        "--reasoning", args.reasoning,
        "--temp", str(args.temperature), "--seed", str(args.seed),
        "--single-turn", "--simple-io", "--no-display-prompt",
        "--show-timings", "--perf", "-f", str(prompt_path), "-o", str(output_path),
    ]
    if args.dry_multiplier > 0:
        command.extend(["--dry-multiplier", str(args.dry_multiplier)])

    print("\n" + paint("LOCAL APP BENCHMARK", "bold", color))
    print("─" * 72)
    print(f"Mode        {'Normal — prompt-only' if mode == 'normal' else 'ECC-guided one-shot'}")
    print(f"Model       {model_label(model)}")
    print(f"Project     {task['name']}")
    if ecc_metadata:
        print("ECC skills  " + ", ".join(skill["name"] for skill in ecc_metadata["skills"]))
        print(f"ECC commit  {ecc_metadata['revision']}")
    preview = " ".join(task["text"].split())
    if len(preview) > 220:
        preview = preview[:217].rstrip() + "..."
    print(f"Prompt      {preview}")
    print(f"Context     {args.context:,} tokens  ·  prompt estimate ~{prompt_token_estimate(effective_prompt):,}")
    print(f"Output cap  {args.max_tokens:,} tokens  ·  threads {args.threads}  ·  GPU layers {gpu_layers}")
    print(f"Reasoning   {args.reasoning}  ·  temperature {args.temperature:g}  ·  seed {args.seed}  ·  DRY {args.dry_multiplier:g}")
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

    html, html_status, html_fences_removed = html_artifact(response)
    named_html_path = None
    index_html_path = None
    if html_status != "not-html":
        named_html_path = task_dir / (
            f"{task['id']}--{artifact_model_slug(model.stem)}--{mode}.html"
        )
        named_html_path.write_text(html.rstrip() + "\n", encoding="utf-8")
        if html_status == "complete-html-copy":
            index_html_path = task_dir / "index.html"
            index_html_path.write_text(html.rstrip() + "\n", encoding="utf-8")

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
        "mode": mode,
        "ecc_guidance": ecc_metadata,
        "prompt_file": str(prompt_path),
        "llama_cli": str(cli),
        "llama_cpp_build": version_result.stdout.strip() or version_result.stderr.strip() or None,
        "command": command,
        "settings": {
            "threads": args.threads,
            "gpu_layers": gpu_layers,
            "context_tokens": args.context,
            "max_generated_tokens": args.max_tokens,
            "reasoning": args.reasoning,
            "dry_multiplier": args.dry_multiplier,
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
        "html_markdown_fences_removed": html_fences_removed,
        "named_html_file": str(named_html_path) if named_html_path else None,
        "index_html_file": str(index_html_path) if index_html_path else None,
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
    if named_html_path:
        print(f"HTML file   {named_html_path}")
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
