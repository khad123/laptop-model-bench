"""Small, dependency-free helpers for readable benchmark timing and token metrics."""

from __future__ import annotations

import datetime as dt
from statistics import fmean
from typing import Any


def _value(source: Any, key: str, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def completion_metrics(task_id: str, elapsed_seconds: float, usage=None, timings=None) -> dict:
    """Normalize OpenAI usage and llama.cpp timings into a stable JSON record."""
    prompt_tokens = _number(_value(usage, "prompt_tokens"))
    completion_tokens = _number(_value(usage, "completion_tokens"))
    total_tokens = _number(_value(usage, "total_tokens"))
    prompt_n = _number(_value(timings, "prompt_n"))
    cache_n = _number(_value(timings, "cache_n", 0)) or 0
    predicted_n = _number(_value(timings, "predicted_n"))
    if prompt_tokens is None and prompt_n is not None:
        prompt_tokens = prompt_n + cache_n
    if completion_tokens is None and predicted_n is not None:
        completion_tokens = predicted_n
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    result = {
        "task_id": task_id,
        "request_elapsed_seconds": round(max(0.0, elapsed_seconds), 3),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "context_tokens": (
            prompt_n + cache_n + predicted_n
            if prompt_n is not None and predicted_n is not None else None
        ),
        "prompt_tokens_per_second": _number(_value(timings, "prompt_per_second")),
        "generation_tokens_per_second": _number(_value(timings, "predicted_per_second")),
    }
    return result


def estimate_remaining_seconds(durations: list[float], remaining_tasks: int) -> float | None:
    usable = [value for value in durations if isinstance(value, (int, float)) and value > 0]
    if remaining_tasks <= 0:
        return 0.0
    return fmean(usable) * remaining_tasks if usable else None


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def progress_line(task_id: str, completed: int, total: int, elapsed: float,
                  metrics: dict | None, eta: float | None, outcome: str = "done") -> str:
    line = f"[{completed}/{total}] {task_id}: {outcome} in {format_duration(elapsed)}"
    metrics = metrics or {}
    token_counts = metrics.get("prompt_tokens"), metrics.get("completion_tokens")
    if all(isinstance(value, (int, float)) for value in token_counts):
        line += f" · {int(token_counts[0])} prompt / {int(token_counts[1])} output tokens"
    prompt_rate = metrics.get("prompt_tokens_per_second")
    generation_rate = metrics.get("generation_tokens_per_second")
    rates = []
    if isinstance(prompt_rate, (int, float)):
        rates.append(f"prompt {prompt_rate:.1f} tok/s")
    if isinstance(generation_rate, (int, float)):
        rates.append(f"generation {generation_rate:.1f} tok/s")
    if rates:
        line += " · " + ", ".join(rates)
    line += f" · ETA {format_duration(eta)}"
    return line


def summarize_task_metrics(records: list[dict], failures: list[dict], total_tasks: int) -> dict:
    prompt_tokens = [item["prompt_tokens"] for item in records if isinstance(item.get("prompt_tokens"), int)]
    output_tokens = [item["completion_tokens"] for item in records if isinstance(item.get("completion_tokens"), int)]
    prompt_rates = [item["prompt_tokens_per_second"] for item in records
                    if isinstance(item.get("prompt_tokens_per_second"), (int, float))]
    generation_rates = [item["generation_tokens_per_second"] for item in records
                        if isinstance(item.get("generation_tokens_per_second"), (int, float))]
    context_sizes = [item["context_tokens"] for item in records
                     if isinstance(item.get("context_tokens"), int)]
    return {
        "tasks_total": total_tasks,
        "tasks_generated": len(records),
        "tasks_failed_or_skipped": len(failures),
        "prompt_tokens_total": sum(prompt_tokens) if prompt_tokens else None,
        "output_tokens_total": sum(output_tokens) if output_tokens else None,
        "max_context_tokens_used": max(context_sizes) if context_sizes else None,
        "prompt_tokens_per_second_average": round(fmean(prompt_rates), 2) if prompt_rates else None,
        "generation_tokens_per_second_average": round(fmean(generation_rates), 2) if generation_rates else None,
        "request_elapsed_seconds_total": round(sum(
            item.get("request_elapsed_seconds", 0) for item in records
            if isinstance(item.get("request_elapsed_seconds"), (int, float))
        ), 3),
        "failed_task_ids": [item.get("task_id") for item in failures],
    }


def finalize_run_timing(metadata: dict, invocation_seconds: float,
                        finished_at: dt.datetime) -> dict:
    """Accumulate active time across resumes and wall time across pauses."""
    sessions = metadata.get("sessions", [])
    if sessions:
        sessions[-1]["finished_at"] = finished_at.isoformat()
        sessions[-1]["elapsed_seconds"] = round(max(0.0, invocation_seconds), 3)
    previous_active = metadata.get("active_elapsed_seconds", 0.0)
    if not isinstance(previous_active, (int, float)):
        previous_active = 0.0
    metadata["active_elapsed_seconds"] = round(previous_active + max(0.0, invocation_seconds), 3)
    metadata["finished_at"] = finished_at.isoformat()
    try:
        started_at = dt.datetime.fromisoformat(metadata["started_at"])
        metadata["total_elapsed_seconds"] = round((finished_at - started_at).total_seconds(), 3)
    except (KeyError, TypeError, ValueError):
        metadata["total_elapsed_seconds"] = None
    return metadata
