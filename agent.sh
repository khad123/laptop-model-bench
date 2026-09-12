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
MAX_TOKENS = 192
MAX_ACTIONS = 4
SERVER_START_TIMEOUT = 180
REQUEST_TIMEOUT = 180

TOOL_CATALOG = {
    "weather_lookup": {
        "description": "Get the mock current Celsius temperature for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    },
    "calculator_add": {
        "description": "Add two numbers.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    },
    "calculator_multiply": {
        "description": "Multiply two numbers.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    },
    "order_lookup": {
        "description": "Look up an order by its exact order ID.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
    "customer_lookup_by_email": {
        "description": "Look up a customer using an exact email address.",
        "parameters": {
            "type": "object",
            "properties": {"email": {"type": "string"}},
            "required": ["email"],
            "additionalProperties": False,
        },
    },
    "customer_lookup_by_id": {
        "description": "Look up a customer using an exact customer ID.",
        "parameters": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    },
    "inventory_by_sku": {
        "description": "Look up one inventory item by its exact SKU.",
        "parameters": {
            "type": "object",
            "properties": {"sku": {"type": "string"}},
            "required": ["sku"],
            "additionalProperties": False,
        },
    },
    "inventory_search_name": {
        "description": "Search inventory by a product-name text query, not by SKU.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    "exchange_rate": {
        "description": "Return only the exchange rate between two currencies; it does not convert an amount.",
        "parameters": {
            "type": "object",
            "properties": {"base": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["base", "quote"],
            "additionalProperties": False,
        },
    },
    "currency_convert": {
        "description": "Convert a numeric amount from one currency to another.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "from_currency": {"type": "string"},
                "to_currency": {"type": "string"},
            },
            "required": ["amount", "from_currency", "to_currency"],
            "additionalProperties": False,
        },
    },
    "orders_by_customer": {
        "description": "List order IDs for a customer, filtered by status.",
        "parameters": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}, "status": {"type": "string"}},
            "required": ["customer_id", "status"],
            "additionalProperties": False,
        },
    },
}

WEATHER = {"Rabat": 24, "Casablanca": 26, "Fez": 29}
ORDERS = {
    "A104": {"order_id": "A104", "status": "shipped"},
    "A105": {"order_id": "A105", "status": "processing"},
}
CUSTOMERS_BY_EMAIL = {
    "ada@example.test": {"customer_id": "C7", "name": "Ada", "email": "ada@example.test"},
    "lin@example.test": {"customer_id": "C8", "name": "Lin", "email": "lin@example.test"},
}
INVENTORY = {
    "P100": {"sku": "P100", "name": "Widget", "unit_price": 7.5, "stock": 12},
    "P200": {"sku": "P200", "name": "Cable", "unit_price": 3.25, "stock": 40},
}
OPEN_ORDERS = {"C7": ["O12", "O19"], "C8": ["O21"]}
RATES = {("USD", "EUR"): 0.9, ("EUR", "USD"): 1.1}


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


def semantic_equal(actual, expected) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return float(actual) == float(expected)
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(semantic_equal(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, dict):
        return set(actual.keys()) == set(expected.keys()) and all(semantic_equal(actual[k], expected[k]) for k in expected)
    return actual == expected


def load_tasks(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise RuntimeError("task file must contain a non-empty tasks array")
    seen = set()
    valid_categories = {"single_tool", "disambiguation", "missing_argument", "multi_step"}
    for task in tasks:
        for field in ("id", "category", "prompt", "tools", "expected_steps"):
            if field not in task:
                raise RuntimeError(f"task missing {field}: {task.get('id', '<unknown>')}")
        if task["id"] in seen:
            raise RuntimeError(f"duplicate task ID: {task['id']}")
        seen.add(task["id"])
        if task["category"] not in valid_categories:
            raise RuntimeError(f"unknown category in {task['id']}: {task['category']}")
        if not isinstance(task["tools"], list) or not task["tools"]:
            raise RuntimeError(f"task has no tools: {task['id']}")
        unknown_tools = sorted(set(task["tools"]) - set(TOOL_CATALOG))
        if unknown_tools:
            raise RuntimeError(f"unknown tools in {task['id']}: {', '.join(unknown_tools)}")
        if not isinstance(task["expected_steps"], list) or not task["expected_steps"]:
            raise RuntimeError(f"task has no expected steps: {task['id']}")
        if len(task["expected_steps"]) > MAX_ACTIONS:
            raise RuntimeError(f"task exceeds MAX_ACTIONS: {task['id']}")
        for step in task["expected_steps"]:
            action = step.get("action")
            if action == "tool":
                if step.get("name") not in task["tools"] or not isinstance(step.get("arguments"), dict):
                    raise RuntimeError(f"invalid expected tool step in {task['id']}")
            elif action == "ask":
                if not isinstance(step.get("field"), str):
                    raise RuntimeError(f"invalid expected ask step in {task['id']}")
            elif action == "final":
                if "answer" not in step:
                    raise RuntimeError(f"invalid expected final step in {task['id']}")
            else:
                raise RuntimeError(f"invalid expected action in {task['id']}: {action}")
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


def validate_arguments(tool_name: str, arguments: dict) -> tuple[bool, str]:
    schema = TOOL_CATALOG[tool_name]["parameters"]
    properties = schema["properties"]
    required = set(schema["required"])
    if set(arguments.keys()) != required:
        return False, "argument_keys"
    for key, spec in properties.items():
        value = arguments[key]
        expected = spec["type"]
        if expected == "string" and not isinstance(value, str):
            return False, f"argument_type:{key}"
        if expected == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
            return False, f"argument_type:{key}"
    return True, "ok"


def validate_action(parsed) -> tuple[bool, str]:
    if not isinstance(parsed, dict):
        return False, "action_not_object"
    action = parsed.get("action")
    if action == "tool":
        if set(parsed.keys()) != {"action", "name", "arguments"}:
            return False, "tool_action_keys"
        if not isinstance(parsed.get("name"), str) or not isinstance(parsed.get("arguments"), dict):
            return False, "tool_action_types"
        return True, "ok"
    if action == "ask":
        if set(parsed.keys()) != {"action", "field"} or not isinstance(parsed.get("field"), str):
            return False, "ask_action_shape"
        return True, "ok"
    if action == "final":
        if set(parsed.keys()) != {"action", "answer"}:
            return False, "final_action_shape"
        return True, "ok"
    return False, "unknown_action"


def parse_action(content: str) -> dict:
    text = normalize_output(content)
    try:
        parsed = json.loads(text)
        valid_json = True
        json_error = ""
    except Exception as exc:
        parsed = None
        valid_json = False
        json_error = f"{type(exc).__name__}: {exc}"
    schema_valid = False
    schema_error = "not_json"
    if valid_json:
        schema_valid, schema_error = validate_action(parsed)
    return {
        "raw": content,
        "normalized": text,
        "parsed": parsed,
        "valid_json": valid_json,
        "json_error": json_error,
        "schema_valid": schema_valid,
        "schema_error": schema_error,
    }


def execute_tool(tool_name: str, arguments: dict) -> dict:
    if tool_name not in TOOL_CATALOG:
        return {"error": "unknown_tool"}
    valid, reason = validate_arguments(tool_name, arguments)
    if not valid:
        return {"error": reason}

    if tool_name == "weather_lookup":
        city = arguments["city"]
        if city not in WEATHER:
            return {"error": "city_not_found", "city": city}
        return {"city": city, "temperature_c": WEATHER[city]}
    if tool_name == "calculator_add":
        return {"result": arguments["a"] + arguments["b"]}
    if tool_name == "calculator_multiply":
        return {"result": arguments["a"] * arguments["b"]}
    if tool_name == "order_lookup":
        order_id = arguments["order_id"]
        return ORDERS.get(order_id, {"error": "order_not_found", "order_id": order_id})
    if tool_name == "customer_lookup_by_email":
        email = arguments["email"]
        return CUSTOMERS_BY_EMAIL.get(email, {"error": "customer_not_found", "email": email})
    if tool_name == "customer_lookup_by_id":
        customer_id = arguments["customer_id"]
        for customer in CUSTOMERS_BY_EMAIL.values():
            if customer["customer_id"] == customer_id:
                return customer
        return {"error": "customer_not_found", "customer_id": customer_id}
    if tool_name == "inventory_by_sku":
        sku = arguments["sku"]
        return INVENTORY.get(sku, {"error": "sku_not_found", "sku": sku})
    if tool_name == "inventory_search_name":
        query = arguments["query"].casefold()
        matches = [item for item in INVENTORY.values() if query in item["name"].casefold()]
        return {"matches": matches}
    if tool_name == "exchange_rate":
        key = (arguments["base"], arguments["quote"])
        if key not in RATES:
            return {"error": "rate_not_found", "base": key[0], "quote": key[1]}
        return {"base": key[0], "quote": key[1], "rate": RATES[key]}
    if tool_name == "currency_convert":
        key = (arguments["from_currency"], arguments["to_currency"])
        if key not in RATES:
            return {"error": "rate_not_found", "from_currency": key[0], "to_currency": key[1]}
        amount = arguments["amount"]
        return {"amount": amount, "converted": amount * RATES[key], "currency": key[1]}
    if tool_name == "orders_by_customer":
        customer_id = arguments["customer_id"]
        status = arguments["status"]
        if status != "open":
            return {"customer_id": customer_id, "status": status, "orders": []}
        return {"customer_id": customer_id, "status": status, "orders": OPEN_ORDERS.get(customer_id, [])}
    return {"error": "unimplemented_tool"}


def render_user_prompt(task: dict) -> str:
    tools = []
    for name in task["tools"]:
        spec = TOOL_CATALOG[name]
        tools.append({"name": name, "description": spec["description"], "parameters": spec["parameters"]})
    return task["prompt"] + "\n\nAVAILABLE TOOLS:\n" + json.dumps(tools, indent=2, sort_keys=True) + "\n\nBegin now."


def run_agent_task(port: int, model_id: str, system_prompt: str, task: dict, artifact_dir: Path, request_timeout: int) -> tuple[list[dict], float, int, int]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": render_user_prompt(task)},
    ]
    actions = []
    total_generation = 0.0
    prompt_tokens = 0
    completion_tokens = 0

    for step_index in range(1, MAX_ACTIONS + 1):
        request_body = {
            "model": model_id,
            "messages": messages,
            "temperature": TEMPERATURE,
            "seed": SEED,
            "max_tokens": MAX_TOKENS,
            "stream": False,
            "cache_prompt": False,
            "reasoning_effort": "none",
        }
        started = time.monotonic()
        status, response = http_json(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            request_body,
            timeout=request_timeout,
        )
        elapsed = time.monotonic() - started
        total_generation += elapsed
        (artifact_dir / f"response-step-{step_index}.json").write_text(
            json.dumps({"request": request_body, "http_status": status, "response": response, "generation_seconds": elapsed}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if status != 200:
            raise RuntimeError(f"HTTP {status}: {response}")

        usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
        prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens += int(usage.get("completion_tokens", 0) or 0)
        content = response_content(response)
        action = parse_action(content)
        action["step"] = step_index
        actions.append(action)
        (artifact_dir / f"model-output-step-{step_index}.txt").write_text(content, encoding="utf-8")

        if not action["valid_json"] or not action["schema_valid"]:
            break

        parsed = action["parsed"]
        messages.append({"role": "assistant", "content": content})
        kind = parsed["action"]
        if kind == "tool":
            tool_name = parsed["name"]
            if tool_name not in task["tools"]:
                result = {"error": "tool_not_available", "name": tool_name}
            else:
                result = execute_tool(tool_name, parsed["arguments"])
            action["tool_result"] = result
            messages.append({
                "role": "user",
                "content": "TOOL RESULT for " + tool_name + ": " + json.dumps(result, sort_keys=True) + "\nReturn the next JSON action only.",
            })
            continue
        if kind in {"ask", "final"}:
            break

    (artifact_dir / "transcript.json").write_text(
        json.dumps({"task": task, "actions": actions}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return actions, total_generation, prompt_tokens, completion_tokens


def score_task(task: dict, actions: list[dict]) -> dict:
    checks = []

    def add(metric: str, passed: bool, step: int | None = None):
        checks.append({"metric": metric, "passed": bool(passed), "step": step})

    for idx, expected in enumerate(task["expected_steps"], 1):
        actual = actions[idx - 1] if idx - 1 < len(actions) else None
        parsed = actual.get("parsed") if actual else None
        add("structured_valid_json", bool(actual and actual.get("valid_json")), idx)
        add("structured_schema", bool(actual and actual.get("schema_valid")), idx)
        action_match = bool(actual and actual.get("schema_valid") and parsed.get("action") == expected["action"])
        add("sequence_action", action_match, idx)

        if expected["action"] == "tool":
            add("tool_choice", bool(action_match and parsed.get("name") == expected["name"]), idx)
            add("arguments", bool(action_match and semantic_equal(parsed.get("arguments"), expected["arguments"])), idx)
        elif expected["action"] == "ask":
            add("outcome", bool(action_match and parsed.get("field") == expected["field"]), idx)
        elif expected["action"] == "final":
            add("outcome", bool(action_match and semantic_equal(parsed.get("answer"), expected["answer"])), idx)

    add("sequence_length", len(actions) == len(task["expected_steps"]), None)
    passed = sum(int(c["passed"]) for c in checks)
    total = len(checks)

    metric_groups = {
        "structured": {"structured_valid_json", "structured_schema"},
        "sequence": {"sequence_action", "sequence_length"},
        "tool_choice": {"tool_choice"},
        "arguments": {"arguments"},
        "outcome": {"outcome"},
    }
    metrics = {}
    for group, names in metric_groups.items():
        subset = [c for c in checks if c["metric"] in names]
        metrics[group] = {
            "passed": sum(int(c["passed"]) for c in subset),
            "total": len(subset),
        }

    return {
        "passed": passed,
        "total": total,
        "task_score": round(passed / total * 100, 2) if total else 0.0,
        "solved": bool(total and passed == total),
        "checks": checks,
        "metrics": metrics,
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

        metric_totals = defaultdict(lambda: [0, 0])
        for row in rs:
            for metric, vals in row.get("metrics", {}).items():
                metric_totals[metric][0] += int(vals.get("passed", 0))
                metric_totals[metric][1] += int(vals.get("total", 0))
        metrics = {
            metric: round(passed / total * 100, 2) if total else None
            for metric, (passed, total) in metric_totals.items()
        }
        out.append({
            "model_id": entry["id"],
            "model": entry["model"],
            "quant": entry["quant"],
            "tasks": len(rs),
            "solved": sum(bool(r.get("solved")) for r in rs),
            "phase6_score": round(sum(scores) / len(scores), 2) if scores else None,
            "categories": categories,
            "metrics": metrics,
        })
    return out


def write_outputs(results_dir: Path, run_id: str, meta: dict, rows: list[dict], summaries: list[dict]):
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / f"phase6-{run_id}.json"
    csv_path = results_dir / f"phase6-{run_id}.csv"
    payload = {"schema_version": "phase6.v0.1", "run": meta, "models": summaries, "results": rows}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    json_path.write_text(text, encoding="utf-8")
    (results_dir / "phase6-latest.json").write_text(text, encoding="utf-8")
    fields = [
        "run_id", "model_id", "model", "quant", "task_id", "category", "status", "solved",
        "passed_checks", "total_checks", "task_score", "action_count", "generation_seconds",
        "prompt_tokens", "completion_tokens", "artifact_dir", "error",
    ]
    for out in (csv_path, results_dir / "phase6-latest.csv"):
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6 deterministic mini tool/agent benchmark")
    parser.add_argument("--registry", default=str(ROOT / "docs" / "MODEL_REGISTRY.md"))
    parser.add_argument("--tasks", default=str(ROOT / "tasks" / "phase6_v0.1.json"))
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
    raw_root = results_dir / "raw" / "phase6" / run_id
    raw_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": run_id,
        "started_at_utc": now_utc(),
        "benchmark_version": task_payload.get("benchmark_version", "phase6-v0.1"),
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
            "max_tokens_per_action": MAX_TOKENS,
            "max_actions": MAX_ACTIONS,
            "cache_prompt": False,
            "reasoning_effort": "none",
            "tool_protocol": "runtime-neutral-json-action-loop",
        },
    }

    print(f"Phase 6 run: {run_id}")
    print(f"Benchmark version: {meta['benchmark_version']}")
    print(f"Models: {len(entries)}")
    print(f"Tasks per model: {len(tasks)}")
    print(f"HF cache: {hf_cache}")
    if not args.dry_run:
        print(f"llama-server: {server}")
        print(f"Settings: threads={THREADS}, ngl=0, ctx={CONTEXT}, temp={TEMPERATURE}, seed={SEED}, reasoning=none, max_tokens/action={MAX_TOKENS}, max_actions={MAX_ACTIONS}")

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
        print(f"Preflight complete: {len(resolved)}/{len(entries)} models resolved, {len(tasks)} agent tasks selected.")
        counts = defaultdict(int)
        for task in tasks:
            counts[task["category"]] += 1
        for category in sorted(counts):
            print(f"  {category}: {counts[category]}")
        return 2 if preflight_failed else 0
    if preflight_failed:
        print("Preflight failed; fix missing/ambiguous models before Phase 6 testing.", file=sys.stderr)
        return 2

    system_prompt = task_payload.get("system_prompt", "Use the tools and output one JSON action at a time.")
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
            env = os.environ.copy()
            env["HF_HUB_OFFLINE"] = "1"
            env["TRANSFORMERS_OFFLINE"] = "1"
            log_handle = server_log.open("wb")
            started = time.monotonic()
            proc = subprocess.Popen(cmd, stdout=log_handle, stderr=subprocess.STDOUT, env=env)
            wait_for_server(port, proc, args.server_timeout)
            print(f"  ready in {time.monotonic() - started:.2f}s")

            for task_index, task in enumerate(tasks, 1):
                artifact_dir = model_raw / task["id"]
                artifact_dir.mkdir(parents=True, exist_ok=True)
                row = {
                    "run_id": run_id,
                    "model_id": model_id,
                    "model": entry["model"],
                    "quant": entry["quant"],
                    "task_id": task["id"],
                    "category": task["category"],
                    "status": "pending",
                    "solved": False,
                    "passed_checks": 0,
                    "total_checks": 0,
                    "task_score": 0.0,
                    "action_count": 0,
                    "generation_seconds": "",
                    "prompt_tokens": "",
                    "completion_tokens": "",
                    "artifact_dir": str(artifact_dir.relative_to(ROOT)) if artifact_dir.is_relative_to(ROOT) else str(artifact_dir),
                    "error": "",
                }
                try:
                    actions, generation_seconds, prompt_tokens, completion_tokens = run_agent_task(
                        port, model_id, system_prompt, task, artifact_dir, args.request_timeout
                    )
                    scored = score_task(task, actions)
                    row.update({
                        "status": "ok",
                        "solved": scored["solved"],
                        "passed_checks": scored["passed"],
                        "total_checks": scored["total"],
                        "task_score": scored["task_score"],
                        "action_count": len(actions),
                        "generation_seconds": round(generation_seconds, 6),
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "checks": scored["checks"],
                        "metrics": scored["metrics"],
                    })
                    (artifact_dir / "score.json").write_text(json.dumps(scored, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
                    "passed_checks": 0, "total_checks": 0, "task_score": 0.0, "action_count": 0,
                    "generation_seconds": "", "prompt_tokens": "", "completion_tokens": "", "artifact_dir": "",
                    "error": f"server_start: {exc}", "metrics": {},
                })
        finally:
            stop_server(proc)
            if log_handle is not None:
                log_handle.close()

        summaries = summarize(rows, resolved)
        current = next((s for s in summaries if s["model_id"] == model_id), None)
        if current:
            m = current["metrics"]
            print(
                f"  agent score: {current['phase6_score']:.2f}% solved={current['solved']}/{current['tasks']} "
                f"structured={m.get('structured')}% tool_choice={m.get('tool_choice')}% "
                f"arguments={m.get('arguments')}% outcome={m.get('outcome')}%"
            )
        write_outputs(results_dir, run_id, meta, rows, summaries)

    meta["finished_at_utc"] = now_utc()
    summaries = summarize(rows, resolved)
    json_path, csv_path = write_outputs(results_dir, run_id, meta, rows, summaries)
    print("\nPhase 6 complete.")
    print(f"JSON summary: {json_path}")
    print(f"CSV task results: {csv_path}")
    print(f"Raw outputs: {raw_root}")
    print("\nMODEL SUMMARY")
    for s in sorted(summaries, key=lambda x: (x["phase6_score"] if x["phase6_score"] is not None else -1), reverse=True):
        m = s["metrics"]
        print(
            f"{s['model_id']:24} agent={s['phase6_score']:6.2f}% solved={s['solved']:2}/{s['tasks']:2} "
            f"structured={str(m.get('structured')):>6} tool={str(m.get('tool_choice')):>6} "
            f"args={str(m.get('arguments')):>6} outcome={str(m.get('outcome')):>6}"
        )
    if infrastructure_failed:
        print("One or more infrastructure executions failed; successful outputs were retained.", file=sys.stderr)
        return 2
    return 0

raise SystemExit(main())
PY
