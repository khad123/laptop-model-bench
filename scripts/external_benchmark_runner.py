#!/usr/bin/env python3
"""Sequential orchestration for the four local-model benchmark tools."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "bench-tools"
RESULTS_DIR = ROOT / "results" / "external-four-suite"
DEFAULT_LLAMA_DIR = Path.home() / "Models/llama.cpp-k2-current/build/bin"
TOOL_NAMES = ("llama-bench", "evalplus", "llm-benchmark", "lm-eval")
TOOL_PATHS = {
    "evalplus": TOOLS_DIR / "evalplus" / ".venv" / "bin" / "evalplus.codegen",
    "llm-benchmark": TOOLS_DIR / "llm-benchmark" / ".venv" / "bin" / "llm-bench",
    "lm-eval": TOOLS_DIR / "lm-evaluation-harness" / ".venv" / "bin" / "lm_eval",
}
EVALPLUS_PYTHON = TOOLS_DIR / "evalplus" / ".venv" / "bin" / "python"
LLM_BENCH_TASKS = (
    "math_001",
    "math_003",
    "reason_001",
    "reason_004",
    "instruct_001",
    "instruct_004",
)
EVALPLUS_TASK_COUNT = 10
LM_EVAL_TASK_LIMIT = 50


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._").lower() or "model"


def find_models() -> list[Path]:
    """Discover only live Hugging Face cache revisions; omit mmproj assets."""
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
            snapshot_dirs = sorted(snapshots.iterdir()) if snapshots.is_dir() else []
        for snapshot in snapshot_dirs:
            for candidate in sorted(snapshot.glob("*.gguf")):
                if candidate.name.lower().startswith("mmproj"):
                    continue
                try:
                    resolved = candidate.resolve(strict=True)
                except (FileNotFoundError, OSError):
                    continue
                if resolved.is_file():
                    models[str(resolved)] = candidate.absolute()
    return sorted(models.values(), key=lambda p: (p.name.lower(), str(p).lower()))


def model_id(path: Path) -> str:
    for parent in path.parents:
        if parent.name.startswith("models--"):
            repo = parent.name.removeprefix("models--").replace("--", "/")
            return slug(f"{Path(repo).name}-{path.name.removesuffix('.gguf')}")
    return slug(path.name.removesuffix(".gguf"))


def build_plan(models: list[Path]) -> list[dict[str, object]]:
    return [
        {"model": model, "model_id": model_id(model), "tool": tool}
        for model in models
        for tool in TOOL_NAMES
    ]


def evenly_spaced_indices(length: int, count: int) -> list[int]:
    if length < 1 or count < 1 or count > length:
        raise ValueError("count must be between 1 and the number of tasks")
    if count == 1:
        return [0]
    return [round(index * (length - 1) / (count - 1)) for index in range(count)]


def result_is_complete(path: Path) -> bool:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "completed"
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def llama_binary(name: str) -> Path:
    return Path(os.environ.get("LLAMA_CPP_BIN", str(DEFAULT_LLAMA_DIR))) / name


def check_setup() -> list[str]:
    missing = []
    for name in TOOL_NAMES:
        binary = llama_binary(name) if name == "llama-bench" else TOOL_PATHS[name]
        if not binary.is_file() or not os.access(binary, os.X_OK):
            missing.append(f"{name}: {binary}")
    if not llama_binary("llama-server").is_file():
        missing.append(f"llama-server: {llama_binary('llama-server')}")
    return missing


def docker_accessible() -> bool:
    if not shutil.which("docker"):
        return False
    probe = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return probe.returncode == 0


def evalplus_task_ids(count: int) -> list[str]:
    env = os.environ.copy()
    env["XDG_CACHE_HOME"] = str(TOOLS_DIR / "cache")
    code = (
        "from evalplus.data import get_human_eval_plus; import json,sys; "
        "keys=list(get_human_eval_plus()); count=int(sys.argv[1]); "
        "indices=[round(i*(len(keys)-1)/(count-1)) for i in range(count)] if count>1 else [0]; "
        "print(json.dumps([keys[i] for i in indices]))"
    )
    result = subprocess.run(
        [str(EVALPLUS_PYTHON), "-c", code, str(count)], env=env,
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def evalplus_image_tag() -> str:
    versions = json.loads((TOOLS_DIR / "tool-versions.json").read_text(encoding="utf-8"))
    revision = versions["evalplus"]["revision"]
    return f"local-lmb-evalplus:{revision[:12]}"


def ensure_evalplus_image(output_root: Path) -> None:
    image = evalplus_image_tag()
    present = subprocess.run(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if present.returncode == 0:
        return
    source = TOOLS_DIR / "repos" / "evalplus"
    command = ["docker", "build", "--tag", image, "--file", str(source / "Dockerfile"), str(source)]
    print(f"Building pinned EvalPlus sandbox image {image} (one-time setup)...", flush=True)
    code = run_logged(command, output_root / "evalplus-image-build.log")
    if code:
        raise RuntimeError(f"Could not build pinned EvalPlus sandbox image (exit {code}). See evalplus-image-build.log")


def reserve_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(port: int, process: subprocess.Popen, timeout: float = 180.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server exited early with code {process.returncode}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.5)
    raise TimeoutError("llama-server did not become healthy within 180 seconds")


def run_logged(command: list[str], log_path: Path, env: dict[str, str] | None = None) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n\n")
        log.flush()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
            log.flush()
        return process.wait()


def write_result(path: Path, status: str, detail: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"status": status, "detail": detail, "finished_at": dt.datetime.now().astimezone().isoformat()}, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@contextlib.contextmanager
def run_server(model: Path, alias: str, port: int, context: int, threads: int, log_path: Path):
    """Start one local llama-server and always stop it when its model batch ends."""
    command = [
        str(llama_binary("llama-server")), "-m", str(model), "-t", str(threads),
        "-ngl", "0", "-c", str(context), "--parallel", "1", "--alias", alias,
        "--host", "127.0.0.1", "--port", str(port), "--temp", "0", "--seed", "42",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("w", encoding="utf-8")
    print(f"Loading {model.name} into llama-server...", flush=True)
    process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, text=True)
    try:
        wait_for_server(port, process)
        yield process, f"http://127.0.0.1:{port}"
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        handle.close()


def llm_bench_config(base_url: str) -> str:
    return f"""backends:\n  llamacpp:\n    enabled: true\n    name: llama.cpp\n    base_url: {base_url}\n    auto_discover: true\nmodels: []\nbenchmark:\n  temperature: 0.0\n  max_tokens: 512\n  timeout: 180\n  runs_per_task: 1\n  resume: true\n  hf_auto_config: false\njudge:\n  enabled: false\n"""


def run_one_tool(tool: str, model: Path, alias: str, base_url: str | None, tool_dir: Path,
                 threads: int, context: int) -> tuple[int, str]:
    """Run one tool's fixed, bounded slice and retain its native artifacts."""
    tool_dir.mkdir(parents=True, exist_ok=True)
    if tool == "llama-bench":
        command = [
            str(llama_binary("llama-bench")), "-m", str(model), "-t", str(threads),
            "-ngl", "0", "-p", "512", "-n", "128", "-r", "3", "-o", "csv",
        ]
        return run_logged(command, tool_dir / "llama-bench.csv"), ""

    if base_url is None:
        return 2, "No llama-server URL was supplied."

    if tool == "evalplus":
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = "local-llama-server"
        env["XDG_CACHE_HOME"] = str(TOOLS_DIR / "cache")
        codegen = (
            "from evalplus.data import get_human_eval_plus; "
            "from evalplus.provider import make_model; "
            "from evalplus.codegen import codegen; "
            "import json,sys; "
            "tasks=get_human_eval_plus(); selected={task_id:tasks[task_id] for task_id in json.loads(sys.argv[3])}; "
            "model=make_model(model=sys.argv[1], backend='openai', dataset='humaneval', "
            "base_url=sys.argv[2], batch_size=1, temperature=0.0); "
            "codegen(target_path=sys.argv[4], model=model, dataset=selected, greedy=True, n_samples=1, resume=True)"
        )
        samples = tool_dir / "generated"
        sample_file = samples / "humaneval" / f"{alias}_openai_temp_0.0.jsonl"
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        codegen_command = [
            str(EVALPLUS_PYTHON), "-c", codegen, alias, f"{base_url}/v1",
            json.dumps(evalplus_task_ids(EVALPLUS_TASK_COUNT)), str(sample_file),
        ]
        code = run_logged(codegen_command, tool_dir / "generate.log", env)
        if code:
            return code, "EvalPlus HumanEval+ sample generation failed."
        if not sample_file.is_file():
            return 2, f"Expected EvalPlus samples not found: {sample_file}"
        if not docker_accessible():
            return 2, "EvalPlus samples were generated, but Docker is unavailable; refusing to execute model-generated code unsandboxed."
        uid, gid = os.getuid(), os.getgid()
        docker_command = [
            "docker", "run", "--rm", "--pull=missing", "--network=none", "--cpus=2",
            "--memory=2g", "--pids-limit=128", "--read-only", "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=256m", "--user", f"{uid}:{gid}",
            "--volume", f"{samples.resolve()}:/results:rw", "--workdir", "/tmp",
            evalplus_image_tag(), "evalplus.evaluate", "--dataset", "humaneval",
            "--samples", f"/results/humaneval/{alias}_openai_temp_0.0.jsonl", "--parallel", "1",
        ]
        return run_logged(docker_command, tool_dir / "score-sandboxed.log"), ""

    if tool == "llm-benchmark":
        config = tool_dir / "llm-benchmark-config.yaml"
        config.write_text(llm_bench_config(base_url), encoding="utf-8")
        command = [
            str(TOOL_PATHS[tool]), "--config", str(config), "--backend", "llamacpp",
            "--model", alias, "--task", *LLM_BENCH_TASKS, "--output", str(tool_dir / "results"),
        ]
        return run_logged(command, tool_dir / "run.log"), ""

    if tool == "lm-eval":
        command = [
            str(TOOL_PATHS[tool]), "run", "--model", "gguf", "--model_args",
            f"base_url={base_url},model={alias},parallel=1,max_length={context},max_gen_toks=128,temperature=0",
            "--tasks", "hellaswag", "--limit", str(LM_EVAL_TASK_LIMIT), "--batch_size", "1",
            "--output_path", str(tool_dir / "results.json"),
        ]
        return run_logged(command, tool_dir / "run.log"), ""

    return 2, f"Unknown tool: {tool}"


def run_model(entry: dict[str, object], output_root: Path, tools: list[str], args) -> dict[str, str]:
    model = Path(entry["model"])
    alias = str(entry["model_id"])
    model_dir = output_root / alias
    model_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model_file": str(model),
        "resolved_file": str(model.resolve()),
        "bytes": model.stat().st_size,
        "sha256": sha256_file(model),
        "llama_cpp_bin": str(llama_binary("llama-server")),
        "llama_cpp_version": subprocess.run(
            [str(llama_binary("llama-server")), "--version"], capture_output=True, text=True, check=False
        ).stdout.strip(),
        "threads": args.threads,
        "context": args.context,
        "gpu_layers": 0,
        "temperature": 0,
        "seed": 42,
    }
    (model_dir / "model.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    statuses: dict[str, str] = {}
    pending = []
    for tool in tools:
        result_path = model_dir / tool / "status.json"
        if args.resume and result_is_complete(result_path):
            statuses[tool] = "skipped (already complete)"
        else:
            pending.append(tool)
    if "llama-bench" in pending:
        print(f"\n[{alias}] llama-bench", flush=True)
        marker = model_dir / "llama-bench" / "status.json"
        try:
            code, detail = run_one_tool("llama-bench", model, alias, None, marker.parent, args.threads, args.context)
        except Exception as exc:
            code, detail = 1, str(exc)
        status = "completed" if code == 0 else "failed"
        write_result(marker, status, detail or f"exit code {code}")
        statuses["llama-bench"] = status

    api_tools = [tool for tool in pending if tool != "llama-bench"]
    if api_tools:
        port = reserve_port()
        try:
            with run_server(model, alias, port, args.context, args.threads, model_dir / "llama-server.log") as (_, base_url):
                for tool in api_tools:
                    print(f"\n[{alias}] {tool}", flush=True)
                    marker = model_dir / tool / "status.json"
                    try:
                        code, detail = run_one_tool(tool, model, alias, base_url, marker.parent, args.threads, args.context)
                    except Exception as exc:
                        code, detail = 1, str(exc)
                    status = "completed" if code == 0 else "failed"
                    write_result(marker, status, detail or f"exit code {code}")
                    statuses[tool] = status
        except Exception as exc:
            for tool in api_tools:
                if tool not in statuses:
                    marker = model_dir / tool / "status.json"
                    write_result(marker, "failed", str(exc))
                    statuses[tool] = "failed"
    return statuses


def main() -> int:
    global EVALPLUS_TASK_COUNT, LM_EVAL_TASK_LIMIT
    parser = argparse.ArgumentParser(description="Run four local-model benchmark tools sequentially.")
    parser.add_argument("--list-models", action="store_true", help="show live GGUF models discovered in the Hugging Face cache")
    parser.add_argument("--dry-run", action="store_true", help="show the run plan without loading models")
    parser.add_argument("--yes", action="store_true", help="skip the start confirmation")
    parser.add_argument("--resume", action="store_true", help="skip tool/model results already marked completed")
    parser.add_argument("--model", action="append", default=[], help="select a model by exact filename or generated model id; repeatable")
    parser.add_argument("--tool", action="append", choices=TOOL_NAMES, default=[], help="select benchmark tool(s); repeatable")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--evalplus-tasks", type=int, default=10, help="number of HumanEval+ tasks, selected by a fixed task-ID range")
    parser.add_argument("--hellaswag-limit", type=int, default=LM_EVAL_TASK_LIMIT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    models = find_models()
    if args.list_models:
        for index, path in enumerate(models, 1):
            print(f"{index}. {path.name} [{model_id(path)}]")
        return 0
    if args.model:
        selected = set(args.model)
        models = [p for p in models if p.name in selected or model_id(p) in selected]
        missing = selected - {p.name for p in models} - {model_id(p) for p in models}
        if missing:
            parser.error("Unknown model selection(s): " + ", ".join(sorted(missing)))
    if not models:
        parser.error("No installed standalone GGUF models were found in HF_HUB_CACHE.")

    tools = args.tool or list(TOOL_NAMES)
    if args.evalplus_tasks < 1 or args.evalplus_tasks > 164:
        parser.error("--evalplus-tasks must be between 1 and 164")
    if args.hellaswag_limit < 1:
        parser.error("--hellaswag-limit must be positive")
    EVALPLUS_TASK_COUNT = args.evalplus_tasks
    LM_EVAL_TASK_LIMIT = args.hellaswag_limit
    plan = [{"model": p, "model_id": model_id(p), "tool": name} for p in models for name in tools]
    output_root = (args.output or RESULTS_DIR / dt.datetime.now().strftime("%Y%m%dT%H%M%S")).expanduser()
    print(f"Models: {len(models)} | Tools: {', '.join(tools)} | Planned model/tool runs: {len(plan)}")
    print(f"Settings: threads={args.threads}, context={args.context}, GPU layers=0")
    print(f"Results: {output_root}")
    for entry in plan:
        print(f"  {entry['model_id']}  ·  {entry['tool']}")
    if args.dry_run:
        return 0

    missing = check_setup()
    if missing:
        print("Benchmark tools are not completely set up:", file=sys.stderr)
        print("\n".join(f"  {item}" for item in missing), file=sys.stderr)
        print("Run scripts/setup_external_benchmarks.sh first.", file=sys.stderr)
        return 2
    if "evalplus" in tools and not docker_accessible():
        print("Docker is required for safe EvalPlus execution of generated code, but the Docker daemon is not accessible.", file=sys.stderr)
        print("Start Docker and confirm your account can use it, then rerun this command.", file=sys.stderr)
        return 2
    if not args.yes and input("Start the sequential all-model benchmark? [y/N] ").strip().lower() not in {"y", "yes"}:
        print("Cancelled; nothing was run.")
        return 0

    output_root.mkdir(parents=True, exist_ok=True)
    versions_path = TOOLS_DIR / "tool-versions.json"
    try:
        versions = json.loads(versions_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        versions = {}
    metadata = {
        "started_at": dt.datetime.now().astimezone().isoformat(),
        "tools": tools,
        "source_revisions": versions,
        "models": [str(p) for p in models],
        "threads": args.threads,
        "context": args.context,
        "llama_cpp_dir": str(llama_binary("llama-server").parent),
        "evalplus_humaneval_plus_tasks": args.evalplus_tasks,
        "evalplus_sampling": "evenly spaced task IDs across HumanEval+",
        "lm_eval_hellaswag_limit": args.hellaswag_limit,
        "llm_benchmark_task_ids": list(LLM_BENCH_TASKS),
    }
    if "evalplus" in tools:
        metadata["evalplus_task_ids"] = evalplus_task_ids(args.evalplus_tasks)
    (output_root / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    if "evalplus" in tools:
        try:
            ensure_evalplus_image(output_root)
        except Exception as exc:
            print(f"EvalPlus sandbox setup failed: {exc}", file=sys.stderr)
            return 2
    summaries: dict[str, dict[str, str]] = {}
    for model in models:
        entry = {"model": model, "model_id": model_id(model)}
        summaries[model_id(model)] = run_model(entry, output_root, tools, args)
    summary_path = output_root / "summary.json"
    summary_path.write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    print(f"\nAll requested models processed. Summary: {summary_path}")
    return 0 if all(status == "completed" or status.startswith("skipped") for row in summaries.values() for status in row.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
