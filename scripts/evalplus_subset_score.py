#!/usr/bin/env python3
"""Score a saved, possibly sampled HumanEval+ set with EvalPlus checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def load_subset_samples(sample_path: Path, available_task_ids: set[str]) -> list[dict[str, Any]]:
    """Read one valid model solution per known task, preserving file order."""
    samples: list[dict[str, Any]] = []
    seen: set[str] = set()
    with sample_path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                sample = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on sample line {line_number}: {exc}") from exc
            if not isinstance(sample, dict):
                raise ValueError(f"Sample line {line_number} must contain a JSON object")
            task_id = sample.get("task_id")
            if task_id not in available_task_ids:
                raise ValueError(f"Unknown HumanEval task ID on line {line_number}: {task_id!r}")
            if task_id in seen:
                raise ValueError(f"Duplicate sample for {task_id}")
            if not isinstance(sample.get("solution"), str) and not isinstance(
                sample.get("completion"), str
            ):
                raise ValueError(f"Sample for {task_id} must contain solution or completion text")
            seen.add(task_id)
            samples.append(sample)
    if not samples:
        raise ValueError("The sample file contains no solutions")
    return samples


def score_samples(sample_path: Path, output_path: Path) -> dict[str, Any]:
    # Import EvalPlus only inside the scoring container, where its pinned package
    # and the pre-mounted dataset are available.
    from evalplus.data import get_human_eval_plus, get_human_eval_plus_hash
    from evalplus.evaluate import check_correctness, get_groundtruth
    from evalplus.eval import PASS

    all_problems = get_human_eval_plus()
    samples = load_subset_samples(sample_path, set(all_problems))
    selected_ids = [sample["task_id"] for sample in samples]
    problems = {task_id: all_problems[task_id] for task_id in selected_ids}
    subset_hash = hashlib.sha256(
        (get_human_eval_plus_hash() + "\0" + "\n".join(selected_ids)).encode("utf-8")
    ).hexdigest()
    expected = get_groundtruth(problems, subset_hash, [])

    task_results = []
    for sample in samples:
        task_id = sample["task_id"]
        solution = sample.get("solution")
        if solution is None:
            solution = problems[task_id]["prompt"] + sample["completion"]
        checked = check_correctness(
            dataset="humaneval",
            completion_id=0,
            problem=problems[task_id],
            solution=solution,
            expected_output=expected[task_id],
            base_only=False,
            fast_check=True,
            identifier=task_id,
        )
        base_status, _ = checked["base"]
        plus_status, _ = checked["plus"]
        task_results.append(
            {
                "task_id": task_id,
                "base_status": base_status,
                "plus_status": plus_status,
                "base_pass": base_status == PASS,
                "plus_pass": base_status == PASS and plus_status == PASS,
            }
        )

    count = len(task_results)
    base_passed = sum(result["base_pass"] for result in task_results)
    plus_passed = sum(result["plus_pass"] for result in task_results)
    result = {
        "benchmark": "EvalPlus HumanEval+ sampled subset",
        "dataset": "humaneval",
        "task_count": count,
        "base_passed": base_passed,
        "plus_passed": plus_passed,
        "pass_at_1": {
            "base": base_passed / count,
            "plus": plus_passed / count,
        },
        "results": task_results,
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"HumanEval base: {base_passed}/{count} ({100 * base_passed / count:.1f}%)")
    print(f"HumanEval+ : {plus_passed}/{count} ({100 * plus_passed / count:.1f}%)")
    print(f"Subset results: {output_path}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        score_samples(args.samples, args.output)
    except Exception as exc:
        print(f"EvalPlus subset scoring failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
