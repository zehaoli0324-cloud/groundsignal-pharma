#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import xml.etree.ElementTree as ET

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SVG_DIR = ROOT / "svg"
PNG_DIR = ROOT / "output" / "png"
PNG_DIR.mkdir(parents=True, exist_ok=True)

issues: list[dict] = []
records: list[dict] = []
svgs = sorted(SVG_DIR.glob("*.svg"))
if len(svgs) != 7:
    issues.append({"rule": "SVG_COUNT", "expected": 7, "actual": len(svgs)})

for path in svgs:
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        issues.append({"file": path.name, "rule": "XML_PARSE", "error": str(exc)})
        continue
    viewbox = [float(x) for x in root.attrib["viewBox"].split()]
    width, height = viewbox[2], viewbox[3]
    ids: list[str] = []
    min_font = 999.0
    for element in root.iter():
        if "id" in element.attrib:
            ids.append(element.attrib["id"])
        if element.tag.endswith("text"):
            size = float(element.attrib.get("font-size", 0))
            min_font = min(min_font, size)
            x = float(element.attrib.get("x", 0))
            y = float(element.attrib.get("y", 0))
            if not (0 <= x <= width and 0 <= y <= height):
                issues.append({"file": path.name, "rule": "TEXT_OUT_OF_BOUNDS", "x": x, "y": y})
        if element.tag.endswith("rect"):
            x = float(element.attrib.get("x", 0))
            y = float(element.attrib.get("y", 0))
            w = float(element.attrib.get("width", 0))
            h = float(element.attrib.get("height", 0))
            if x < 0 or y < 0 or x + w > width or y + h > height:
                issues.append({"file": path.name, "rule": "RECT_OUT_OF_BOUNDS", "rect": [x, y, w, h]})
    duplicates = sorted(k for k, v in Counter(ids).items() if v > 1)
    if duplicates:
        issues.append({"file": path.name, "rule": "DUPLICATE_IDS", "ids": duplicates})
    if min_font < 15:
        issues.append({"file": path.name, "rule": "FONT_TOO_SMALL", "min_font": min_font})

    png = PNG_DIR / f"{path.stem}.png"
    cairosvg.svg2png(url=str(path), write_to=str(png), output_width=1800)
    with Image.open(png) as image:
        if image.getbbox() is None:
            issues.append({"file": path.name, "rule": "BLANK_RENDER"})
        size = image.size
    records.append({"file": path.name, "viewBox": viewbox, "min_font": min_font, "png": str(png.relative_to(ROOT)), "png_size": size})

result = {"status": "PASS" if not issues else "FAIL", "svg_count": len(svgs), "records": records, "issues": issues}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if not issues else 1)
