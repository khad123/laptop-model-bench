#!/usr/bin/env python3
"""Generate exactly one EvalPlus HumanEval+ sample with bounded HTTP retries."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
import openai
from evalplus.data import get_human_eval_plus
from evalplus.provider.openai import OpenAIChatDecoder
from evalplus.sanitize import sanitize
from benchmark_telemetry import completion_metrics
from external_benchmark_runner import evalplus_solution_is_usable


class BoundedOpenAIChatDecoder(OpenAIChatDecoder):
    def __init__(self, *args, request_timeout: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_timeout = request_timeout
        self.last_metrics = None

    def _codegen_api_batch(self, prompt: str, batch_size: int):
        # EvalPlus' default helper retries selected errors indefinitely. Use the
        # same completion settings, with a finite transport deadline and no retries.
        started = time.perf_counter()
        with httpx.Client(verify=self.verify_certificate, timeout=self.request_timeout) as http_client:
            client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY", "none"),
                base_url=self.base_url,
                http_client=http_client,
                timeout=self.request_timeout,
                max_retries=0,
            )
            result = client.chat.completions.create(
                model=self.name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_new_tokens,
                temperature=self.temperature,
                n=batch_size,
                top_p=0.95,
                extra_body={"timings_per_token": True},
            )
        response = result.model_dump()
        timings = response.get("timings")
        if timings is None:
            timings = getattr(result, "model_extra", None) or {}
            timings = timings.get("timings") if isinstance(timings, dict) else None
        self.last_metrics = completion_metrics("", time.perf_counter() - started, response.get("usage"), timings)
        return [choice.message.content or "" for choice in result.choices]


def append_jsonl(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--raw-samples", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--request-timeout", type=int, required=True)
    args = parser.parse_args()

    tasks = get_human_eval_plus()
    if args.task_id not in tasks:
        raise SystemExit(f"Unknown HumanEval+ task: {args.task_id}")
    task = tasks[args.task_id]
    prompt = task["prompt"].strip() + "\n"
    model = BoundedOpenAIChatDecoder(
        name=args.model,
        base_url=args.base_url,
        batch_size=1,
        temperature=0.0,
        instruction_prefix="",
        request_timeout=args.request_timeout,
    )
    try:
        outputs = model.codegen(prompt, do_sample=False, num_samples=1)
    except (openai.APITimeoutError, httpx.TimeoutException) as exc:
        print(f"Generation request timed out: {exc}", file=sys.stderr, flush=True)
        return 124
    if not outputs:
        print("No completion was returned by llama-server.", file=sys.stderr, flush=True)
        return 1
    solution = outputs[0]
    if not evalplus_solution_is_usable(solution):
        print(
            "llama-server returned empty answer content; recording this task as failed.",
            file=sys.stderr,
            flush=True,
        )
        return 1
    metrics = dict(model.last_metrics or {})
    metrics["task_id"] = args.task_id
    metrics["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    append_jsonl(args.samples, {
        "task_id": args.task_id,
        "solution": sanitize(solution, entrypoint=task["entry_point"]),
    })
    append_jsonl(args.raw_samples, {"task_id": args.task_id, "solution": solution})
    append_jsonl(args.metrics, metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
