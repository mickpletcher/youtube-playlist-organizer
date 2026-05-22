from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def pick_color(rate: float) -> str:
    if rate >= 0.9:
        return "#2e8b57"
    if rate >= 0.8:
        return "#4c9f38"
    if rate >= 0.7:
        return "#a4a61d"
    if rate >= 0.6:
        return "#dfb317"
    return "#e05d44"


def render_svg(label: str, value: str, color: str) -> str:
    label_width = 78
    value_width = max(52, 10 * len(value))
    width = label_width + value_width
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{label}: {value}">
<linearGradient id="b" x2="0" y2="100%">
  <stop offset="0" stop-color="#fff" stop-opacity=".7"/>
  <stop offset=".1" stop-color="#aaa" stop-opacity=".1"/>
  <stop offset=".9" stop-opacity=".3"/>
  <stop offset="1" stop-opacity=".5"/>
</linearGradient>
<mask id="a">
  <rect width="{width}" height="20" rx="3" fill="#fff"/>
</mask>
<g mask="url(#a)">
  <rect width="{label_width}" height="20" fill="#555"/>
  <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
  <rect width="{width}" height="20" fill="url(#b)"/>
</g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
  <text x="{label_width / 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
  <text x="{label_width / 2}" y="14">{label}</text>
  <text x="{label_width + value_width / 2}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
  <text x="{label_width + value_width / 2}" y="14">{value}</text>
</g>
</svg>
"""


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/generate_coverage_badge.py <coverage.xml> <output.svg>")
        return 1

    coverage_xml = Path(sys.argv[1])
    output_svg = Path(sys.argv[2])

    root = ET.fromstring(coverage_xml.read_text(encoding="utf-8"))
    line_rate = float(root.attrib.get("line-rate", "0"))
    percentage = round(line_rate * 100)
    svg = render_svg("coverage", f"{percentage}%", pick_color(line_rate))

    output_svg.parent.mkdir(parents=True, exist_ok=True)
    output_svg.write_text(svg, encoding="utf-8")
    print(f"Wrote {output_svg} with coverage {percentage}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
