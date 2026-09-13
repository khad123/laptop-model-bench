#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SOURCE = RESULTS / "phase9-consolidated.json"
OUT = RESULTS / "charts"


def load() -> dict[str, Any]:
    if not SOURCE.is_file():
        raise SystemExit(
            f"Missing {SOURCE}. Run `python3 scripts/build_phase9_report.py` first."
        )
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def label(row: dict[str, Any]) -> str:
    model = str(row.get("model") or row["model_id"])
    quant = str(row.get("quant") or "")
    return f"{model} {quant}".strip()


def horizontal_bar_chart(
    rows: list[dict[str, Any]],
    key: str,
    title: str,
    subtitle: str,
    filename: str,
    suffix: str = "",
) -> Path:
    ranked = sorted(rows, key=lambda r: float(r[key]), reverse=True)
    width = 1160
    left = 350
    right = 120
    top = 115
    row_h = 48
    bottom = 55
    height = top + len(ranked) * row_h + bottom
    plot_w = width - left - right
    best = max(float(r[key]) for r in ranked) or 1.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(title)}</title>',
        f'<desc id="desc">{esc(subtitle)}</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>',
        'text{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#171717}',
        '.title{font-size:26px;font-weight:700}',
        '.sub{font-size:14px;fill:#555}',
        '.label{font-size:14px}',
        '.value{font-size:14px;font-weight:600}',
        '.track{fill:#eeeeee}',
        '.bar{fill:#2563eb}',
        '</style>',
        f'<text class="title" x="32" y="42">{esc(title)}</text>',
        f'<text class="sub" x="32" y="70">{esc(subtitle)}</text>',
    ]

    for i, row in enumerate(ranked):
        value = float(row[key])
        y = top + i * row_h
        bar_w = max(1.0, plot_w * value / best)
        parts.extend(
            [
                f'<text class="label" x="32" y="{y + 21}">{esc(label(row))}</text>',
                f'<rect class="track" x="{left}" y="{y + 5}" width="{plot_w}" height="22" rx="4"/>',
                f'<rect class="bar" x="{left}" y="{y + 5}" width="{bar_w:.1f}" height="22" rx="4"/>',
                f'<text class="value" x="{left + plot_w + 12}" y="{y + 21}">{value:.2f}{esc(suffix)}</text>',
            ]
        )

    parts.append('</svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / filename
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return path


def main() -> None:
    payload = load()
    all_rows = list(payload.get("models", []))
    rows = [r for r in all_rows if r.get("recommended_quant_view")]
    if not rows:
        raise SystemExit("No recommended-quant rows found in Phase 9 consolidated data.")

    charts = [
        horizontal_bar_chart(
            rows,
            "overall_laptop_score",
            "Best overall laptop model",
            "Frozen v1 overall score — recommended quant per base model",
            "overall-laptop-score.svg",
        ),
        horizontal_bar_chart(
            rows,
            "capability_score",
            "Capability score",
            "Frozen weighted capability subtotal across Phases 2–7",
            "capability-score.svg",
        ),
        horizontal_bar_chart(
            rows,
            "developer_score",
            "Developer score",
            "30% isolated coding + 40% MiniSWE + 30% tool/agent score",
            "developer-score.svg",
        ),
        horizontal_bar_chart(
            rows,
            "speed_score",
            "Speed score",
            "40% normalized prompt processing + 60% normalized generation speed",
            "speed-score.svg",
        ),
        horizontal_bar_chart(
            rows,
            "quality_per_gib",
            "Quality per GiB",
            "Capability score divided by model size in GiB",
            "quality-per-gib.svg",
        ),
    ]

    print("Phase 10 charts generated:")
    for path in charts:
        print(path)


if __name__ == "__main__":
    main()
