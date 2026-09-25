#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from phase1_perf import (
    free_port,
    hf_cache_default,
    parse_registry,
    resolve_model,
    wait_for_server,
)

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_REGISTRY = ROOT / "docs" / "MODEL_REGISTRY_V12.md"
DEFAULT_TASKS = ROOT / "tasks" / "v12" / "phase2_reasoning.json"
DEFAULT_RESULTS = ROOT / "results" / "v12" / "phase2"

THREADS = 4
CONTEXT = 4096
TEMPERATURE = 0.0
SEED = 42
MAX_TOKENS = 512
REASONING_BUDGET = 256
REASONING_BUDGET_MESSAGE = "Stop reasoning now. Do not explain. Output only the requested FINAL: A, FINAL: B, FINAL: C, or FINAL: D."


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_tasks(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))

    tasks = data.get("tasks")

    if not isinstance(tasks, list) or not tasks:
        raise RuntimeError("tasks array is missing or empty")

    required = {
        "id",
        "domain",
        "category",
        "difficulty",
        "question",
        "choices",
        "answer",
    }

    seen = set()

    for task in tasks:
        missing = required - set(task)

        if missing:
            raise RuntimeError(
                f"{task.get('id', '<unknown>')}: missing {sorted(missing)}"
            )

        if task["id"] in seen:
            raise RuntimeError(f"duplicate task ID: {task['id']}")

        seen.add(task["id"])

        if set(task["choices"]) != {"A", "B", "C", "D"}:
            raise RuntimeError(
                f"{task['id']}: choices must be A/B/C/D"
            )

        if task["answer"] not in {"A", "B", "C", "D"}:
            raise RuntimeError(
                f"{task['id']}: invalid answer {task['answer']}"
            )

        if task["difficulty"] not in {"easy", "medium", "hard"}:
            raise RuntimeError(
                f"{task['id']}: invalid difficulty"
            )

    return data


def format_question(task: dict) -> str:
    c = task["choices"]

    return (
        f"Question: {task['question']}\n\n"
        f"A. {c['A']}\n"
        f"B. {c['B']}\n"
        f"C. {c['C']}\n"
        f"D. {c['D']}\n\n"
        "Choose the best answer. "
        "You may reason internally, but after reasoning finishes, "
        "do not provide an explanation. "
        "Your entire visible final answer must be exactly one of: "
        "FINAL: A, FINAL: B, FINAL: C, or FINAL: D."
    )


def post_json(
    url: str,
    payload: dict,
    timeout: float,
) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=timeout,
        ) as response:
            body = response.read().decode(
                "utf-8",
                errors="replace",
            )

            return (
                int(response.status),
                json.loads(body) if body.strip() else {},
            )

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}

        return int(exc.code), parsed


def response_text(response: dict) -> str:
    choices = response.get("choices")

    if not isinstance(choices, list) or not choices:
        raise RuntimeError("response has no choices")

    first = choices[0]
    message = first.get("message")

    if isinstance(message, dict):
        content = message.get("content")

        if isinstance(content, str):
            return content

    text = first.get("text")

    if isinstance(text, str):
        return text

    raise RuntimeError("response contained no text")


def extract_answer(text: str) -> str | None:
    import re

    cleaned = text.strip().upper()

    # Preferred v1.2 format: FINAL: A
    matches = re.findall(
        r"FINAL\s*:\s*([ABCD])",
        cleaned,
    )
    if matches:
        return matches[-1]

    # Bare answer.
    if re.fullmatch(r"[ABCD][\s.!)]*", cleaned):
        return cleaned[0]

    # Conservative final-line fallback.
    lines = [
        line.strip()
        for line in cleaned.splitlines()
        if line.strip()
    ]

    if lines:
        m = re.fullmatch(
            r"(?:ANSWER\s*:\s*)?([ABCD])[.!)]?",
            lines[-1],
        )
        if m:
            return m.group(1)

    return None

def stop_server(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return

    proc.send_signal(signal.SIGTERM)

    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def score_breakdown(
    rows: list[dict],
    field: str,
) -> dict:
    result = {}

    values = sorted({r[field] for r in rows})

    for value in values:
        subset = [
            r for r in rows
            if r[field] == value
        ]

        total = len(subset)
        correct = sum(
            int(r.get("correct", 0))
            for r in subset
            if r["status"] == "ok"
        )

        result[value] = {
            "correct": correct,
            "total": total,
            "accuracy": (
                round(correct / total * 100, 2)
                if total else None
            ),
        }

    return result


def summarize(
    rows: list[dict],
    entries: list[dict],
) -> list[dict]:
    by_model = defaultdict(list)

    for row in rows:
        by_model[row["model_id"]].append(row)

    result = []

    for entry in entries:
        rs = by_model[entry["id"]]

        total = len(rs)
        ok = [r for r in rs if r["status"] == "ok"]

        correct = sum(int(r["correct"]) for r in ok)

        parsed = sum(
            r.get("extracted_answer")
            in {"A", "B", "C", "D"}
            for r in ok
        )

        domains = score_breakdown(rs, "domain")
        difficulties = score_breakdown(rs, "difficulty")
        categories = score_breakdown(rs, "category")

        domain_scores = [
            x["accuracy"]
            for x in domains.values()
            if x["accuracy"] is not None
        ]

        phase2_score = (
            round(
                sum(domain_scores) / len(domain_scores),
                2,
            )
            if domain_scores else None
        )

        elapsed = [
            float(r["elapsed_seconds"])
            for r in ok
            if r.get("elapsed_seconds") is not None
        ]

        result.append(
            {
                "model_id": entry["id"],
                "model": entry["model"],
                "quant": entry["quant"],

                "correct": correct,
                "total": total,

                "accuracy": (
                    round(correct / total * 100, 2)
                    if total else None
                ),

                "phase2_score": phase2_score,

                "parsed": parsed,
                "parse_rate": (
                    round(parsed / total * 100, 2)
                    if total else None
                ),

                "failures": sum(
                    r["status"] != "ok"
                    for r in rs
                ),

                "elapsed_total_seconds": (
                    round(sum(elapsed), 3)
                    if elapsed else None
                ),

                "elapsed_mean_seconds": (
                    round(sum(elapsed) / len(elapsed), 3)
                    if elapsed else None
                ),

                "domains": domains,
                "difficulties": difficulties,
                "categories": categories,
            }
        )

    return result


def write_outputs(
    results_dir: Path,
    run_id: str,
    meta: dict,
    rows: list[dict],
    summaries: list[dict],
) -> tuple[Path, Path]:
    results_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        results_dir
        / f"phase2-v12-{run_id}.json"
    )

    csv_path = (
        results_dir
        / f"phase2-v12-{run_id}.csv"
    )

    payload = {
        "schema_version": "phase2.v12-dev",
        "run": meta,
        "models": summaries,
        "results": rows,
    }

    text = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    json_path.write_text(
        text,
        encoding="utf-8",
    )

    (
        results_dir
        / "phase2-v12-latest.json"
    ).write_text(
        text,
        encoding="utf-8",
    )

    fields = [
        "run_id",
        "model_id",
        "model",
        "quant",
        "task_id",
        "domain",
        "category",
        "difficulty",
        "status",
        "expected_answer",
        "extracted_answer",
        "correct",
        "response_text",
        "http_status",
        "elapsed_seconds",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "error",
    ]

    for path in (
        csv_path,
        results_dir / "phase2-v12-latest.csv",
    ):
        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fields,
                extrasaction="ignore",
                lineterminator="\n",
            )

            writer.writeheader()
            writer.writerows(rows)

    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Laptop Model Bench v1.2 "
            "Phase 2 reasoning/knowledge runner"
        )
    )

    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
    )

    parser.add_argument(
        "--tasks",
        default=str(DEFAULT_TASKS),
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
            llama_cpp
            / "build"
            / "bin"
            / "llama-server"
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
        "--only",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--task",
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
        "--server-timeout",
        type=float,
        default=180.0,
    )

    parser.add_argument(
        "--request-timeout",
        type=float,
        default=180.0,
    )

    args = parser.parse_args()

    registry = Path(args.registry).resolve()
    task_file = Path(args.tasks).resolve()
    server = Path(
        args.llama_server
    ).expanduser().resolve()
    hf_cache = Path(
        args.hf_cache
    ).expanduser().resolve()
    results_dir = Path(
        args.results_dir
    ).resolve()

    task_data = load_tasks(task_file)
    tasks = task_data["tasks"]

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
                "unknown models: "
                + ", ".join(sorted(missing))
            )

        entries = [
            e for e in entries
            if e["id"] in wanted
        ]

    if args.task:
        wanted_tasks = set(args.task)
        known_tasks = {t["id"] for t in tasks}

        missing = wanted_tasks - known_tasks

        if missing:
            parser.error(
                "unknown tasks: "
                + ", ".join(sorted(missing))
            )

        tasks = [
            t for t in tasks
            if t["id"] in wanted_tasks
        ]

    resolved = []

    for entry in entries:
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

    print("v1.2 Phase 2")
    print(f"Models: {len(resolved)}")
    print(f"Tasks:  {len(tasks)}")
    print(
        f"Requests: {len(resolved) * len(tasks)}"
    )
    print()

    for entry in resolved:
        print(
            f"[resolved] {entry['id']} "
            f"({entry['model_size_gib']:.3f} GiB)"
        )

    if args.dry_run:
        print()
        print("DRY RUN PASS")
        return 0

    if not (
        server.is_file()
        and os.access(server, os.X_OK)
    ):
        parser.error(
            f"llama-server not executable: {server}"
        )

    run_id = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    raw_dir = (
        results_dir
        / "raw"
        / run_id
    )

    raw_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    meta = {
        "run_id": run_id,
        "started_at_utc": now_utc(),
        "task_file": str(task_file),
        "task_version": task_data.get(
            "benchmark_version"
        ),
        "models": len(resolved),
        "task_count": len(tasks),
        "threads": THREADS,
        "context": CONTEXT,
        "temperature": TEMPERATURE,
        "seed": SEED,
        "max_tokens": MAX_TOKENS,
        "reasoning_policy": "native/model-template reasoning with fixed budget",
        "reasoning_budget_tokens": REASONING_BUDGET,
        "reasoning_budget_message": REASONING_BUDGET_MESSAGE,
    }

    rows = []

    system_prompt = (
        "You are taking a deterministic multiple-choice benchmark. "
        "Do not use tools or external access. "
        "You may use internal reasoning. "
        "After internal reasoning is finished, the visible answer must contain "
        "only FINAL: followed by one uppercase letter A, B, C, or D. "
        "Do not include an explanation in the visible final answer."
    )

    for model_num, entry in enumerate(
        resolved,
        1,
    ):
        print()
        print(
            f"=== [{model_num}/{len(resolved)}] "
            f"{entry['id']} ==="
        )

        port = free_port()

        stdout_path = (
            raw_dir
            / f"{entry['id']}.server.stdout.log"
        )
        stderr_path = (
            raw_dir
            / f"{entry['id']}.server.stderr.log"
        )

        out = stdout_path.open("wb")
        err = stderr_path.open("wb")

        command = [
            str(server),
            "-m",
            entry["model_path"],
            "-t",
            str(THREADS),
            "-ngl",
            "0",
            "-c",
            str(CONTEXT),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--reasoning-budget",
            str(REASONING_BUDGET),
            "--reasoning-budget-message",
            REASONING_BUDGET_MESSAGE,
        ]

        proc = subprocess.Popen(
            command,
            stdout=out,
            stderr=err,
            env={
                **os.environ,
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "LC_ALL": "C",
            },
        )

        try:
            wait_for_server(
                proc,
                port,
                args.server_timeout,
            )

            print("Server ready.")

            for index, task in enumerate(
                tasks,
                1,
            ):
                row = {
                    "run_id": run_id,
                    "model_id": entry["id"],
                    "model": entry["model"],
                    "quant": entry["quant"],
                    "task_id": task["id"],
                    "domain": task["domain"],
                    "category": task["category"],
                    "difficulty": task[
                        "difficulty"
                    ],
                    "expected_answer": task[
                        "answer"
                    ],
                    "status": "pending",
                    "error": "",
                }

                payload = {
                    "model": "local",
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": format_question(
                                task
                            ),
                        },
                    ],
                    "temperature": TEMPERATURE,
                    "seed": SEED,
                    "max_tokens": MAX_TOKENS,
                    "stream": False,
                }

                started = time.perf_counter()

                try:
                    status, response = post_json(
                        (
                            f"http://127.0.0.1:"
                            f"{port}/v1/chat/completions"
                        ),
                        payload,
                        args.request_timeout,
                    )

                    elapsed = (
                        time.perf_counter()
                        - started
                    )

                    text = response_text(
                        response
                    )

                    answer = extract_answer(
                        text
                    )

                    usage = response.get(
                        "usage",
                        {},
                    )

                    row.update(
                        {
                            "http_status": status,
                            "elapsed_seconds": round(
                                elapsed,
                                6,
                            ),
                            "response_text": text,
                            "extracted_answer":
                                answer,
                            "correct": int(
                                answer
                                == task["answer"]
                            ),
                            "prompt_tokens":
                                usage.get(
                                    "prompt_tokens"
                                ),
                            "completion_tokens":
                                usage.get(
                                    "completion_tokens"
                                ),
                            "total_tokens":
                                usage.get(
                                    "total_tokens"
                                ),
                        }
                    )

                    if status == 200:
                        row["status"] = "ok"
                    else:
                        row["status"] = "failed"
                        row["error"] = (
                            f"HTTP {status}"
                        )

                    raw_path = (
                        raw_dir
                        / (
                            f"{entry['id']}."
                            f"{task['id']}.json"
                        )
                    )

                    raw_path.write_text(
                        json.dumps(
                            {
                                "task": task,
                                "request": payload,
                                "response":
                                    response,
                                "result": row,
                            },
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n"
                    )

                except Exception as exc:
                    row.update(
                        {
                            "status": "failed",
                            "correct": 0,
                            "elapsed_seconds":
                                round(
                                    time.perf_counter()
                                    - started,
                                    6,
                                ),
                            "error": (
                                f"{type(exc).__name__}: "
                                f"{exc}"
                            ),
                        }
                    )

                rows.append(row)

                symbol = (
                    "✓"
                    if row.get("correct") else "✗"
                )

                print(
                    f"  [{index:02d}/{len(tasks):02d}] "
                    f"{task['id']:12} "
                    f"{symbol} "
                    f"got={row.get('extracted_answer')} "
                    f"expected={task['answer']} "
                    f"{row.get('elapsed_seconds', 0):.2f}s"
                )

        finally:
            stop_server(proc)
            out.close()
            err.close()

        summaries = summarize(
            rows,
            resolved,
        )

        write_outputs(
            results_dir,
            run_id,
            meta,
            rows,
            summaries,
        )

    meta["finished_at_utc"] = now_utc()

    summaries = summarize(
        rows,
        resolved,
    )

    json_path, csv_path = write_outputs(
        results_dir,
        run_id,
        meta,
        rows,
        summaries,
    )

    print()
    print("=== PHASE 2 SUMMARY ===")

    for model in summaries:
        print(
            f"{model['model_id']:25} "
            f"{model['correct']:2}/{model['total']:2} "
            f"score={model['phase2_score']:.2f}% "
            f"parse={model['parse_rate']:.2f}%"
        )

    print()
    print("JSON:", json_path)
    print("CSV: ", csv_path)

    failures = [
        r for r in rows
        if r["status"] != "ok"
    ]

    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
