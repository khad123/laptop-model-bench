#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

SOURCES = {
    "phase1": RESULTS / "phase1-20260912T125525Z.json",
    "phase2": RESULTS / "phase2-20260912T163441Z.json",
    "phase3": RESULTS / "phase3-20260912T172204Z.json",
    "phase4": RESULTS / "phase4-20260912T185826Z.json",
    "phase5": RESULTS / "phase5-20260912T233610Z.json",
    "phase6": RESULTS / "phase6-20260913T001137Z.json",
    "phase7": RESULTS / "phase7-20260913T135829Z.json",
    "phase7_correction": RESULTS / "phase7-20260913T171609Z.json",
}

CAPABILITY_WEIGHTS = {
    "phase2": 12.0,
    "phase3": 15.0,
    "phase4": 20.0,
    "phase5": 10.0,
    "phase6": 20.0,
    "phase7": 8.0,
}
EFFICIENCY_WEIGHTS = {
    "pp": 4.0,
    "tg": 5.0,
    "ram": 4.0,
    "size": 2.0,
}

RECOMMENDED_IDS = {
    "k2-0.9b-q4km",
    "qwen35-0.8b-q4km",
    "qwen35-2b-q4km",
    "lfm25-1.2b-q4km",
    "smollm3-3b-iq4xs",
    "gemma3-1b-q4km",
    "llama32-1b-q4km",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"Missing frozen result file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def summary_map(payload: dict[str, Any], score_key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in payload.get("models", []):
        model_id = row.get("model_id") or row.get("id")
        score = row.get(score_key)
        if model_id is not None and score is not None:
            out[str(model_id)] = float(score)
    return out


def corrected_phase7(full: dict[str, Any], correction: dict[str, Any]) -> dict[str, float]:
    rows = list(full.get("results", []))
    target = "smollm3-3b-iq4xs"
    rows = [r for r in rows if not (r.get("model_id") == target and r.get("bucket") == "4k")]
    replacement = [
        r for r in correction.get("results", [])
        if r.get("model_id") == target and r.get("bucket") == "4k"
    ]
    if len(replacement) != 3:
        raise SystemExit(f"Expected 3 SmolLM3 IQ4 4K correction rows, found {len(replacement)}")
    rows.extend(replacement)

    by_model: dict[str, list[float]] = {}
    for row in rows:
        model_id = row.get("model_id")
        score = row.get("task_score")
        if model_id is None or score is None:
            continue
        by_model.setdefault(str(model_id), []).append(float(score))

    out = {}
    for model_id, scores in by_model.items():
        if scores:
            out[model_id] = round(sum(scores) / len(scores), 2)
    return out


def ratio_high(value: float, best: float) -> float:
    return 100.0 * value / best if best > 0 else 0.0


def ratio_low(value: float, best_low: float) -> float:
    return 100.0 * best_low / value if value > 0 else 0.0


def fmt(v: Any, digits: int = 2) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, (int, float)):
        return f"{float(v):.{digits}f}"
    return str(v)


def md_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int | None = None) -> str:
    view = rows if limit is None else rows[:limit]
    head = "| " + " | ".join(label for _, label in columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    body = []
    for row in view:
        body.append("| " + " | ".join(fmt(row.get(key)) for key, _ in columns) + " |")
    return "\n".join([head, sep, *body])


def ranked(rows: list[dict[str, Any]], key: str, reverse: bool = True) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: float(r.get(key, -1e9)), reverse=reverse)


def main() -> None:
    payloads = {name: load_json(path) for name, path in SOURCES.items()}

    p1_rows = payloads["phase1"].get("results", [])
    p1 = {}
    for row in p1_rows:
        model_id = row.get("id") or row.get("model_id")
        if model_id:
            p1[str(model_id)] = row

    scores = {
        "phase2": summary_map(payloads["phase2"], "phase2_score"),
        "phase3": summary_map(payloads["phase3"], "phase3_score"),
        "phase4": summary_map(payloads["phase4"], "phase4_score"),
        "phase5": summary_map(payloads["phase5"], "phase5_score"),
        "phase6": summary_map(payloads["phase6"], "phase6_score"),
        "phase7": corrected_phase7(payloads["phase7"], payloads["phase7_correction"]),
    }

    ids = sorted(p1)
    missing = {
        phase: sorted(set(ids) - set(phase_scores))
        for phase, phase_scores in scores.items()
        if set(ids) - set(phase_scores)
    }
    if missing:
        raise SystemExit(f"Missing model scores in frozen data: {missing}")

    pp_best = max(float(p1[i]["pp_tokens_per_s"]) for i in ids)
    tg_best = max(float(p1[i]["tg_tokens_per_s"]) for i in ids)
    ram_best = min(float(p1[i]["peak_rss_gib"]) for i in ids)
    size_best = min(float(p1[i]["model_size_gib"]) for i in ids)

    rows: list[dict[str, Any]] = []
    capability_weight_total = sum(CAPABILITY_WEIGHTS.values())
    efficiency_weight_total = sum(EFFICIENCY_WEIGHTS.values())

    for model_id in ids:
        r1 = p1[model_id]
        pp = float(r1["pp_tokens_per_s"])
        tg = float(r1["tg_tokens_per_s"])
        ram = float(r1["peak_rss_gib"])
        size = float(r1["model_size_gib"])

        p2 = scores["phase2"][model_id]
        p3 = scores["phase3"][model_id]
        p4 = scores["phase4"][model_id]
        p5 = scores["phase5"][model_id]
        p6 = scores["phase6"][model_id]
        p7 = scores["phase7"][model_id]

        capability_points = (
            p2 * CAPABILITY_WEIGHTS["phase2"]
            + p3 * CAPABILITY_WEIGHTS["phase3"]
            + p4 * CAPABILITY_WEIGHTS["phase4"]
            + p5 * CAPABILITY_WEIGHTS["phase5"]
            + p6 * CAPABILITY_WEIGHTS["phase6"]
            + p7 * CAPABILITY_WEIGHTS["phase7"]
        )
        capability_score = capability_points / capability_weight_total

        pp_norm = ratio_high(pp, pp_best)
        tg_norm = ratio_high(tg, tg_best)
        ram_norm = ratio_low(ram, ram_best)
        size_norm = ratio_low(size, size_best)
        efficiency_points = (
            pp_norm * EFFICIENCY_WEIGHTS["pp"]
            + tg_norm * EFFICIENCY_WEIGHTS["tg"]
            + ram_norm * EFFICIENCY_WEIGHTS["ram"]
            + size_norm * EFFICIENCY_WEIGHTS["size"]
        )
        efficiency_score = efficiency_points / efficiency_weight_total
        overall = 0.85 * capability_score + 0.15 * efficiency_score
        developer = 0.30 * p3 + 0.40 * p4 + 0.30 * p6
        speed = 0.40 * pp_norm + 0.60 * tg_norm
        quality_per_gib = capability_score / size

        rows.append({
            "model_id": model_id,
            "model": r1.get("model"),
            "quant": r1.get("quant"),
            "group": r1.get("group"),
            "recommended_quant_view": model_id in RECOMMENDED_IDS,
            "size_gib": round(size, 4),
            "peak_rss_gib": round(ram, 4),
            "pp_tokens_per_s": round(pp, 2),
            "tg_tokens_per_s": round(tg, 2),
            "phase2": round(p2, 2),
            "phase3": round(p3, 2),
            "phase4": round(p4, 2),
            "phase5": round(p5, 2),
            "phase6": round(p6, 2),
            "phase7": round(p7, 2),
            "developer_score": round(developer, 2),
            "speed_score": round(speed, 2),
            "capability_score": round(capability_score, 2),
            "efficiency_score": round(efficiency_score, 2),
            "overall_laptop_score": round(overall, 2),
            "quality_per_gib": round(quality_per_gib, 2),
        })

    overall_all = ranked(rows, "overall_laptop_score")
    recommended = ranked([r for r in rows if r["recommended_quant_view"]], "overall_laptop_score")

    out_json = RESULTS / "phase9-consolidated.json"
    out_csv = RESULTS / "phase9-consolidated.csv"
    out_md = RESULTS / "phase9-report.md"

    payload = {
        "schema_version": "phase9.v0.1-provisional",
        "status": "provisional-scoring-review",
        "sources": {k: str(v.relative_to(ROOT)) for k, v in SOURCES.items()},
        "phase7_correction": "Replace only smollm3-3b-iq4xs 4K timeout rows with 20260913T171609Z rows.",
        "weights": {
            "capability": CAPABILITY_WEIGHTS,
            "efficiency": EFFICIENCY_WEIGHTS,
            "capability_total": capability_weight_total,
            "efficiency_total": efficiency_weight_total,
        },
        "models": rows,
        "rankings": {
            "overall_all_entries": [r["model_id"] for r in overall_all],
            "overall_recommended_quants": [r["model_id"] for r in recommended],
            "smartest": [r["model_id"] for r in ranked(rows, "phase2")],
            "isolated_coding": [r["model_id"] for r in ranked(rows, "phase3")],
            "miniswe": [r["model_id"] for r in ranked(rows, "phase4")],
            "instruction": [r["model_id"] for r in ranked(rows, "phase5")],
            "agent": [r["model_id"] for r in ranked(rows, "phase6")],
            "context": [r["model_id"] for r in ranked(rows, "phase7")],
            "developer": [r["model_id"] for r in ranked(rows, "developer_score")],
            "fastest": [r["model_id"] for r in ranked(rows, "speed_score")],
            "quality_per_gib": [r["model_id"] for r in ranked(rows, "quality_per_gib")],
        },
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fields = list(rows[0].keys())
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    report = [
        "# Phase 9 provisional report",
        "",
        "> Overall weighting is provisional until reviewed. Category leaderboards remain authoritative standalone views.",
        "",
        "## Overall laptop score — all 12 model+quant entries",
        "",
        md_table(overall_all, [
            ("model_id", "Model ID"),
            ("overall_laptop_score", "Overall"),
            ("capability_score", "Capability"),
            ("efficiency_score", "Efficiency"),
            ("developer_score", "Developer"),
        ]),
        "",
        "## Overall laptop score — recommended quant per base model",
        "",
        md_table(recommended, [
            ("model_id", "Model ID"),
            ("overall_laptop_score", "Overall"),
            ("capability_score", "Capability"),
            ("efficiency_score", "Efficiency"),
            ("developer_score", "Developer"),
        ]),
        "",
        "## Category leaders",
        "",
        "### Smartest / reasoning + knowledge",
        "",
        md_table(ranked(rows, "phase2"), [("model_id", "Model ID"), ("phase2", "P2")], 5),
        "",
        "### Developer score",
        "",
        md_table(ranked(rows, "developer_score"), [
            ("model_id", "Model ID"), ("developer_score", "Developer"),
            ("phase3", "Coding"), ("phase4", "MiniSWE"), ("phase6", "Agent")
        ], 5),
        "",
        "### Fastest",
        "",
        md_table(ranked(rows, "speed_score"), [
            ("model_id", "Model ID"), ("speed_score", "Speed"),
            ("pp_tokens_per_s", "PP tok/s"), ("tg_tokens_per_s", "TG tok/s")
        ], 5),
        "",
        "### Quality per GiB",
        "",
        md_table(ranked(rows, "quality_per_gib"), [
            ("model_id", "Model ID"), ("quality_per_gib", "Capability/GiB"),
            ("capability_score", "Capability"), ("size_gib", "Size GiB")
        ], 5),
        "",
        "## Full consolidated table",
        "",
        md_table(overall_all, [
            ("model_id", "Model ID"), ("phase2", "P2"), ("phase3", "P3"),
            ("phase4", "P4"), ("phase5", "P5"), ("phase6", "P6"), ("phase7", "P7"),
            ("pp_tokens_per_s", "PP"), ("tg_tokens_per_s", "TG"),
            ("peak_rss_gib", "RAM GiB"), ("size_gib", "Size GiB"),
            ("overall_laptop_score", "Overall")
        ]),
        "",
    ]
    out_md.write_text("\n".join(report), encoding="utf-8")

    print("Phase 9 provisional consolidation complete.")
    print(f"JSON: {out_json}")
    print(f"CSV:  {out_csv}")
    print(f"MD:   {out_md}")
    print("\nOVERALL — RECOMMENDED QUANTS")
    for idx, row in enumerate(recommended, 1):
        print(
            f"{idx:2d}. {row['model_id']:<28} overall={row['overall_laptop_score']:6.2f} "
            f"cap={row['capability_score']:6.2f} eff={row['efficiency_score']:6.2f} dev={row['developer_score']:6.2f}"
        )
    print("\nTOP CATEGORY LEADERS")
    for label, key in [
        ("Smartest", "phase2"),
        ("Developer", "developer_score"),
        ("MiniSWE", "phase4"),
        ("Agent", "phase6"),
        ("Instruction", "phase5"),
        ("Context", "phase7"),
        ("Fastest", "speed_score"),
        ("Quality/GiB", "quality_per_gib"),
    ]:
        top = ranked(rows, key)[0]
        print(f"{label:<12}: {top['model_id']:<28} {key}={top[key]:.2f}")


if __name__ == "__main__":
    main()
