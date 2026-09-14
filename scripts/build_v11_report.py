#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
V11 = RESULTS / "v11"

SOURCES = {
    "baseline": {
        1: V11 / "phase1-baselines.json",
        2: V11 / "phase2-baselines.json",
        3: V11 / "phase3-baselines.json",
        4: V11 / "phase4-baselines.json",
        5: V11 / "phase5-baselines.json",
        6: V11 / "phase6-baselines.json",
        7: V11 / "phase7-baselines.json",
    },
    "minicpm": {
        1: V11 / "phase1-minicpm.json",
        2: V11 / "phase2-minicpm.json",
        3: V11 / "phase3-minicpm.json",
        4: V11 / "phase4-minicpm.json",
        5: V11 / "phase5-minicpm.json",
        6: V11 / "phase6-minicpm.json",
        7: V11 / "phase7-minicpm.json",
    },
}

EXPECTED = {
    "qwen35-0.8b-q4km",
    "k2-0.9b-q4km",
    "qwen35-2b-q4km",
    "smollm3-3b-iq4xs",
    "minicpm5-1b-q4km",
    "minicpm5-2b-q4km",
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


def load(path: Path):
    if not path.is_file():
        raise SystemExit(f"Missing source: {path}")
    return json.loads(path.read_text())


models = {}

for group, src in SOURCES.items():
    # Phase 1
    d = load(src[1])
    for r in d["results"]:
        mid = r.get("id") or r.get("model_id")
        models.setdefault(mid, {})
        models[mid].update({
            "model_id": mid,
            "model": r.get("model", mid),
            "quant": r.get("quant"),
            "source_group": group,
            "size_gib": float(r["model_size_gib"]),
            "peak_rss_gib": float(r["peak_rss_gib"]),
            "pp_tokens_per_s": float(r["pp_tokens_per_s"]),
            "tg_tokens_per_s": float(r["tg_tokens_per_s"]),
        })

    # Phases 2-6
    for phase in range(2, 7):
        d = load(src[phase])
        key = f"phase{phase}_score"
        for r in d.get("models", []):
            mid = r.get("model_id") or r.get("id")
            if mid:
                models.setdefault(mid, {})
                models[mid][f"phase{phase}"] = float(r[key])

    # Phase 7
    d = load(src[7])
    by_model = {}
    for r in d["results"]:
        by_model.setdefault(r["model_id"], []).append(float(r["task_score"]))

    for mid, vals in by_model.items():
        if len(vals) != 9:
            raise SystemExit(
                f"{mid}: expected 9 Phase 7 tasks, found {len(vals)}"
            )
        models.setdefault(mid, {})
        models[mid]["phase7"] = sum(vals) / len(vals)


if set(models) != EXPECTED:
    raise SystemExit(
        f"Unexpected model set.\nExpected: {sorted(EXPECTED)}\nFound: {sorted(models)}"
    )

for mid, r in models.items():
    required = [
        "size_gib", "peak_rss_gib", "pp_tokens_per_s", "tg_tokens_per_s",
        "phase2", "phase3", "phase4", "phase5", "phase6", "phase7",
    ]
    missing = [k for k in required if k not in r]
    if missing:
        raise SystemExit(f"{mid}: missing {missing}")


pp_best = max(r["pp_tokens_per_s"] for r in models.values())
tg_best = max(r["tg_tokens_per_s"] for r in models.values())
ram_best = min(r["peak_rss_gib"] for r in models.values())
size_best = min(r["size_gib"] for r in models.values())

rows = []

for mid, r in models.items():
    cap = (
        r["phase2"] * CAPABILITY_WEIGHTS["phase2"]
        + r["phase3"] * CAPABILITY_WEIGHTS["phase3"]
        + r["phase4"] * CAPABILITY_WEIGHTS["phase4"]
        + r["phase5"] * CAPABILITY_WEIGHTS["phase5"]
        + r["phase6"] * CAPABILITY_WEIGHTS["phase6"]
        + r["phase7"] * CAPABILITY_WEIGHTS["phase7"]
    ) / sum(CAPABILITY_WEIGHTS.values())

    pp_norm = 100 * r["pp_tokens_per_s"] / pp_best
    tg_norm = 100 * r["tg_tokens_per_s"] / tg_best
    ram_norm = 100 * ram_best / r["peak_rss_gib"]
    size_norm = 100 * size_best / r["size_gib"]

    efficiency = (
        pp_norm * EFFICIENCY_WEIGHTS["pp"]
        + tg_norm * EFFICIENCY_WEIGHTS["tg"]
        + ram_norm * EFFICIENCY_WEIGHTS["ram"]
        + size_norm * EFFICIENCY_WEIGHTS["size"]
    ) / sum(EFFICIENCY_WEIGHTS.values())

    overall = 0.85 * cap + 0.15 * efficiency

    developer = (
        0.30 * r["phase3"]
        + 0.40 * r["phase4"]
        + 0.30 * r["phase6"]
    )

    speed = 0.40 * pp_norm + 0.60 * tg_norm
    quality_per_gib = cap / r["size_gib"]

    row = dict(r)
    row.update({
        "capability_score": round(cap, 2),
        "efficiency_score": round(efficiency, 2),
        "overall_laptop_score": round(overall, 2),
        "developer_score": round(developer, 2),
        "speed_score": round(speed, 2),
        "quality_per_gib": round(quality_per_gib, 2),
    })

    for k in [
        "size_gib", "peak_rss_gib",
        "pp_tokens_per_s", "tg_tokens_per_s",
        "phase2", "phase3", "phase4",
        "phase5", "phase6", "phase7",
    ]:
        row[k] = round(row[k], 2)

    rows.append(row)

rows.sort(key=lambda r: r["overall_laptop_score"], reverse=True)

for i, row in enumerate(rows, 1):
    row["rank"] = i


category_keys = {
    "Reasoning / knowledge": "phase2",
    "Coding": "phase3",
    "MiniSWE": "phase4",
    "Instruction": "phase5",
    "Agents / tools": "phase6",
    "Context": "phase7",
    "Prompt speed": "pp_tokens_per_s",
    "Generation speed": "tg_tokens_per_s",
}

winners = {}
for label, key in category_keys.items():
    best = max(rows, key=lambda r: r[key])
    winners[label] = {
        "model_id": best["model_id"],
        "score": best[key],
    }


V11.mkdir(parents=True, exist_ok=True)

json_out = V11 / "leaderboard.json"
csv_out = V11 / "leaderboard.csv"
md_out = ROOT / "docs" / "V1_1_RESULTS.md"

json_out.write_text(
    json.dumps(
        {
            "version": "v1.1",
            "methodology": {
                "overall": "85% capability + 15% laptop efficiency",
                "capability_weights": CAPABILITY_WEIGHTS,
                "efficiency_weights": EFFICIENCY_WEIGHTS,
                "developer_score": "30% coding + 40% MiniSWE + 30% agents",
                "speed_score": "40% normalized PP + 60% normalized TG",
                "normalization_pool": "six fresh v1.1 models",
            },
            "sources": {
                group: {str(k): str(v.relative_to(ROOT)) for k, v in src.items()}
                for group, src in SOURCES.items()
            },
            "category_winners": winners,
            "leaderboard": rows,
        },
        indent=2,
        sort_keys=True,
    ) + "\n"
)

fields = [
    "rank", "model_id", "model", "quant",
    "overall_laptop_score", "capability_score", "efficiency_score",
    "developer_score", "speed_score", "quality_per_gib",
    "phase2", "phase3", "phase4", "phase5", "phase6", "phase7",
    "pp_tokens_per_s", "tg_tokens_per_s",
    "peak_rss_gib", "size_gib", "source_group",
]

with csv_out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows({k: r.get(k) for k in fields} for r in rows)


lines = [
    "# Laptop Model Bench v1.1 Results",
    "",
    "v1.1 reruns the original v1 benchmark methodology on six current finalists.",
    "The v1.0.0 release remains frozen and unchanged.",
    "",
    "## Overall leaderboard",
    "",
    "| Rank | Model | Overall | Capability | Efficiency | Developer | Speed | Quality/GiB |",
    "|---:|---|---:|---:|---:|---:|---:|---:|",
]

for r in rows:
    lines.append(
        f"| {r['rank']} | `{r['model_id']}` | "
        f"{r['overall_laptop_score']:.2f} | "
        f"{r['capability_score']:.2f} | "
        f"{r['efficiency_score']:.2f} | "
        f"{r['developer_score']:.2f} | "
        f"{r['speed_score']:.2f} | "
        f"{r['quality_per_gib']:.2f} |"
    )

lines += [
    "",
    "## Capability breakdown",
    "",
    "| Model | Reasoning | Coding | MiniSWE | Instruction | Agents | Context |",
    "|---|---:|---:|---:|---:|---:|---:|",
]

for r in rows:
    lines.append(
        f"| `{r['model_id']}` | "
        f"{r['phase2']:.2f} | {r['phase3']:.2f} | "
        f"{r['phase4']:.2f} | {r['phase5']:.2f} | "
        f"{r['phase6']:.2f} | {r['phase7']:.2f} |"
    )

lines += [
    "",
    "## Laptop performance",
    "",
    "| Model | PP tok/s | TG tok/s | Peak RSS GiB | Size GiB |",
    "|---|---:|---:|---:|---:|",
]

for r in rows:
    lines.append(
        f"| `{r['model_id']}` | "
        f"{r['pp_tokens_per_s']:.2f} | "
        f"{r['tg_tokens_per_s']:.2f} | "
        f"{r['peak_rss_gib']:.2f} | "
        f"{r['size_gib']:.2f} |"
    )

lines += [
    "",
    "## Category winners",
    "",
]

for label, item in winners.items():
    lines.append(
        f"- **{label}:** `{item['model_id']}` — {item['score']:.2f}"
    )

lines += [
    "",
    "## Main findings",
    "",
    "- **Qwen3.5-2B Q4_K_M** remains the strongest overall laptop model and the clear agent/tool-use winner.",
    "- **MiniCPM5-2B Q4_K_M** is the strongest coding and MiniSWE model in this six-model run.",
    "- **SmolLM3-3B IQ4_XS** is the context winner.",
    "- **Qwen3.5-0.8B Q4_K_M** remains the strongest balanced lightweight choice.",
    "- **MiniCPM5-1B Q4_K_M** is the raw speed winner, but its capability score is substantially lower.",
    "",
    "## Scoring",
    "",
    "- Overall laptop score: **85% capability + 15% efficiency**.",
    "- Capability weights are unchanged from v1.0.",
    "- Efficiency uses normalized prompt speed, generation speed, peak RSS, and model size.",
    "- Efficiency normalization is relative to the six-model v1.1 pool.",
    "- Developer score: **30% coding + 40% MiniSWE + 30% agents**.",
    "",
    "v1.2 will expand task coverage, context scaling, repeatability, system-resource measurements, and real-world workloads.",
    "",
]

md_out.write_text("\n".join(lines))

print("Generated:")
print(f"  {json_out}")
print(f"  {csv_out}")
print(f"  {md_out}")
print()
print("Leaderboard:")
for r in rows:
    print(
        f"  {r['rank']}. {r['model_id']:25} "
        f"overall={r['overall_laptop_score']:.2f}"
    )
