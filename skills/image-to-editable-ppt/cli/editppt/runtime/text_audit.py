#!/usr/bin/env python3
"""Conservative, deterministic text-layout diagnostics for Office renders."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageStat

from deck_run_state import write_json


def content_box_for_manifest(manifest: dict) -> dict[str, float]:
    slide = manifest.get("slide", {})
    slide_width = float(slide.get("width", 13.333))
    slide_height = float(slide.get("height", 7.5))
    content = manifest.get("content_box")
    if content:
        return {key: float(content.get(key, 0)) for key in ("left", "top", "width", "height")}
    source = manifest.get("source", {})
    source_width = float(source.get("width_px", 1))
    source_height = float(source.get("height_px", 1))
    source_aspect = source_width / source_height
    slide_aspect = slide_width / slide_height
    if source_aspect >= slide_aspect:
        width = slide_width
        height = width / source_aspect
        left = 0.0
        top = (slide_height - height) / 2
    else:
        height = slide_height
        width = height * source_aspect
        left = (slide_width - width) / 2
        top = 0.0
    return {"left": left, "top": top, "width": width, "height": height}


def source_box_to_render(manifest: dict, box_px: Iterable[float], render_size: tuple[int, int]) -> tuple[int, int, int, int]:
    """Map a source-pixel box into a full-slide Office-render pixel box."""

    source = manifest.get("source", {})
    source_width = float(source.get("width_px", 0))
    source_height = float(source.get("height_px", 0))
    if source_width <= 0 or source_height <= 0:
        raise ValueError("manifest.source.width_px/height_px are required for text audit")
    slide = manifest.get("slide", {})
    slide_width = float(slide.get("width", 13.333))
    slide_height = float(slide.get("height", 7.5))
    content = content_box_for_manifest(manifest)
    x, y, width, height = (float(value) for value in box_px)
    render_width, render_height = render_size

    def point(px, py):
        slide_x = content["left"] + px / source_width * content["width"]
        slide_y = content["top"] + py / source_height * content["height"]
        return slide_x / slide_width * render_width, slide_y / slide_height * render_height

    left, top = point(x, y)
    right, bottom = point(x + width, y + height)
    return (
        max(0, min(render_width - 1, round(left))),
        max(0, min(render_height - 1, round(top))),
        max(1, min(render_width, round(right))),
        max(1, min(render_height, round(bottom))),
    )


def _parse_color(value, default=(17, 17, 17)) -> tuple[int, int, int]:
    if not value or str(value).strip().lower() in {"none", "transparent"}:
        return default
    try:
        return tuple(ImageColor.getrgb(str(value)))[:3]
    except ValueError:
        return default


def text_colors(item: dict) -> list[tuple[int, int, int]]:
    values = []
    for key in ("color", "fill", "text_color"):
        if item.get(key):
            values.append(_parse_color(item[key]))
    for run in item.get("runs", []):
        for key in ("color", "fill", "text_color"):
            if run.get(key):
                values.append(_parse_color(run[key]))
    return values or [(17, 17, 17)]


def _border_mean(image: Image.Image) -> tuple[float, float, float]:
    if image.width < 3 or image.height < 3:
        return ImageStat.Stat(image).mean[:3]
    strips = [
        image.crop((0, 0, image.width, 1)),
        image.crop((0, image.height - 1, image.width, image.height)),
        image.crop((0, 0, 1, image.height)),
        image.crop((image.width - 1, 0, image.width, image.height)),
    ]
    values = [pixel for strip in strips for pixel in _pixels(strip)]
    if not values:
        return (255.0, 255.0, 255.0)
    return tuple(sum(pixel[channel] for pixel in values) / len(values) for channel in range(3))


def _distance(left, right) -> float:
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))


def _pixels(image: Image.Image):
    getter = getattr(image, "get_flattened_data", None)
    if getter is not None:
        return getter()
    return image.getdata()


def ink_mask(image: Image.Image, colors: list[tuple[int, int, int]], threshold: int = 16):
    """Return a 1-bit mask for pixels likely belonging to declared text ink."""

    background = _border_mean(image)
    mask = Image.new("1", image.size, 0)
    output = []
    for pixel in _pixels(image.convert("RGB")):
        contrast = _distance(pixel, background)
        declared_match = min(_distance(pixel, color) for color in colors)
        output.append(1 if (declared_match <= 190 and contrast >= threshold) else 0)
    mask.putdata(output)
    return mask


def mask_bounds(mask: Image.Image) -> tuple[int, int, int, int] | None:
    return mask.getbbox()


def count_ink_lines(mask: Image.Image, gap_tolerance: int = 2) -> int:
    rows = []
    for y in range(mask.height):
        rows.append(any(mask.getpixel((x, y)) for x in range(mask.width)))
    groups = 0
    gap = gap_tolerance + 1
    for occupied in rows:
        if occupied:
            if gap > gap_tolerance:
                groups += 1
            gap = 0
        else:
            gap += 1
    return groups


def _edge_crossing(mask: Image.Image, box: tuple[int, int, int, int], margin: int) -> bool:
    """Detect ink continuing across a text-box edge, not nearby decoration."""

    left, top, right, bottom = box
    local_left = left
    local_top = top
    local_right = right
    local_bottom = bottom
    band = max(2, min(right - left, bottom - top) // 40)

    def any_pixels(x0, y0, x1, y1):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(mask.width, x1)
        y1 = min(mask.height, y1)
        return any(mask.getpixel((x, y)) for y in range(y0, y1) for x in range(x0, x1))

    crossings = (
        any_pixels(local_left, local_top, local_left + band, local_bottom)
        and any_pixels(local_left - margin, local_top, local_left, local_bottom),
        any_pixels(local_right - band, local_top, local_right, local_bottom)
        and any_pixels(local_right, local_top, local_right + margin, local_bottom),
        any_pixels(local_left, local_top, local_right, local_top + band)
        and any_pixels(local_left, local_top - margin, local_right, local_top),
        any_pixels(local_left, local_bottom - band, local_right, local_bottom)
        and any_pixels(local_left, local_bottom, local_right, local_bottom + margin),
    )
    return any(crossings)


def _ink_source_size(manifest: dict, render_size: tuple[int, int], width: int, height: int) -> tuple[float, float]:
    source = manifest["source"]
    content = content_box_for_manifest(manifest)
    slide = manifest.get("slide", {})
    scale_x = (content["width"] / float(slide.get("width", 13.333))) * render_size[0] / float(source["width_px"])
    scale_y = (content["height"] / float(slide.get("height", 7.5))) * render_size[1] / float(source["height_px"])
    return width / max(scale_x, 1e-9), height / max(scale_y, 1e-9)


def _effective_font_sizes(item: dict) -> list[float]:
    values = []
    if item.get("font_size") not in (None, ""):
        values.append(float(item["font_size"]))
    for run in item.get("runs", []):
        if run.get("font_size") not in (None, ""):
            values.append(float(run["font_size"]))
    return values


def audit_size_groups(text_boxes: list[dict], tolerance: float = 0.01) -> list[dict]:
    groups: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for index, item in enumerate(text_boxes):
        group = item.get("size_group")
        if not group:
            continue
        for value in _effective_font_sizes(item):
            groups[str(group)].append((str(item.get("id", f"text_{index}")), value))
    issues = []
    for group, values in groups.items():
        sizes = [value for _item_id, value in values]
        if max(sizes) - min(sizes) > tolerance:
            issues.append(
                {
                    "kind": "size_group_mismatch",
                    "severity": "error",
                    "size_group": group,
                    "values": [{"id": item_id, "font_size": value} for item_id, value in values],
                    "message": f"size_group {group!r} has inconsistent requested font sizes",
                }
            )
    return issues


def audit_manifest(manifest: dict, render: Image.Image, *, ink_threshold: int = 16) -> dict:
    text_boxes = manifest.get("text_boxes", [])
    errors = audit_size_groups(text_boxes, float(manifest.get("font_size_group_tolerance", 0.01)))
    warnings = []
    entries = []
    render_size = render.size

    for index, item in enumerate(text_boxes):
        if not item.get("box_px"):
            continue
        item_id = str(item.get("id", f"text_{index}"))
        box = source_box_to_render(manifest, item["box_px"], render_size)
        margin = max(2, int(item.get("audit_margin_px", 4)))
        expanded = (
            max(0, box[0] - margin),
            max(0, box[1] - margin),
            min(render.width, box[2] + margin),
            min(render.height, box[3] + margin),
        )
        crop = render.crop(expanded)
        mask = ink_mask(crop, text_colors(item), threshold=ink_threshold)
        bounds = mask_bounds(mask)
        entry = {
            "id": item_id,
            "box_px": list(item["box_px"]),
            "render_box_px": list(box),
            "status": "ok",
            "ink_bounds_render_px": None,
            "actual_lines": None,
            "expected_lines": item.get("expected_lines"),
        }
        if bounds is None:
            entry["status"] = "unresolved"
            warnings.append(
                {
                    "kind": "ink_unresolved",
                    "severity": "warning",
                    "id": item_id,
                    "message": "No declared-color ink was isolated in the Office render; inspect this box manually.",
                }
            )
            entries.append(entry)
            continue

        inside_box = (box[0] - expanded[0], box[1] - expanded[1], box[2] - expanded[0], box[3] - expanded[1])
        inside_mask = mask.crop(inside_box)
        inside_bounds = mask_bounds(inside_mask)
        if inside_bounds is None:
            entry["status"] = "unresolved"
            warnings.append(
                {
                    "kind": "ink_unresolved",
                    "severity": "warning",
                    "id": item_id,
                    "message": "Declared-color ink was found only outside the configured text box; inspect this box manually.",
                }
            )
            entries.append(entry)
            continue
        absolute_bounds = (
            inside_bounds[0] + box[0],
            inside_bounds[1] + box[1],
            inside_bounds[2] + box[0],
            inside_bounds[3] + box[1],
        )
        entry["ink_bounds_render_px"] = list(absolute_bounds)
        actual_lines = count_ink_lines(inside_mask)
        entry["actual_lines"] = actual_lines
        ink_width_source, ink_height_source = _ink_source_size(
            manifest,
            render_size,
            absolute_bounds[2] - absolute_bounds[0],
            absolute_bounds[3] - absolute_bounds[1],
        )
        entry["ink_size_source_px"] = {
            "width": round(ink_width_source, 2),
            "height": round(ink_height_source, 2),
        }

        outside = _edge_crossing(mask, inside_box, margin)
        touches = (
            absolute_bounds[0] <= box[0] + 1
            or absolute_bounds[1] <= box[1] + 1
            or absolute_bounds[2] >= box[2] - 1
            or absolute_bounds[3] >= box[3] - 1
        )
        edge_is_configured = item.get("edge_policy") == "strict" or any(
            key in item
            for key in (
                "expected_lines",
                "wrap_policy",
                "target_ink_width_px",
                "target_ink_height_px",
                "target_font_size",
                "size_group",
            )
        )
        if outside or (touches and item.get("edge_policy") == "strict"):
            issue = {
                "kind": "text_box_edge_risk",
                "severity": "error" if edge_is_configured else "warning",
                "id": item_id,
                "outside_box": outside,
                "touching_box_edge": touches,
                "message": "Rendered ink reaches or crosses the configured text-box edge.",
            }
            (errors if issue["severity"] == "error" else warnings).append(issue)

        expected_lines = item.get("expected_lines")
        if expected_lines not in (None, ""):
            expected_lines = int(expected_lines)
            if actual_lines != expected_lines:
                issue = {
                    "kind": "unexpected_wrapping",
                    "severity": "error" if item.get("wrap_policy") == "fixed" else "warning",
                    "id": item_id,
                    "expected_lines": expected_lines,
                    "actual_lines": actual_lines,
                    "message": f"Expected {expected_lines} rendered line(s), detected {actual_lines}.",
                }
                (errors if issue["severity"] == "error" else warnings).append(issue)

        for field, dimension, tolerance_field in (
            ("target_ink_width_px", "width", "ink_width_tolerance"),
            ("target_ink_height_px", "height", "ink_height_tolerance"),
        ):
            target = item.get(field)
            if target in (None, "") or target == 0:
                continue
            tolerance = float(item.get(tolerance_field, 0.12 if dimension == "height" else 0.18))
            actual = entry["ink_size_source_px"][dimension]
            relative_error = abs(actual - float(target)) / max(abs(float(target)), 1e-9)
            entry[f"{dimension}_relative_error"] = round(relative_error, 4)
            if relative_error > tolerance:
                errors.append(
                    {
                        "kind": "ink_size_mismatch",
                        "severity": "error",
                        "id": item_id,
                        "dimension": dimension,
                        "target": float(target),
                        "actual": actual,
                        "tolerance": tolerance,
                        "message": f"Rendered ink {dimension} is outside the configured tolerance.",
                    }
                )

        target_font_size = item.get("target_font_size")
        if target_font_size not in (None, ""):
            actual_font_size = _effective_font_sizes(item)
            if actual_font_size:
                tolerance = float(item.get("font_size_tolerance", 0.01))
                if abs(actual_font_size[0] - float(target_font_size)) > tolerance:
                    errors.append(
                        {
                            "kind": "font_size_mismatch",
                            "severity": "error",
                            "id": item_id,
                            "target": float(target_font_size),
                            "actual": actual_font_size[0],
                            "message": "Requested font size differs from the configured target.",
                        }
                    )
        entries.append(entry)

    return {
        "schema_version": 1,
        "passed": not errors,
        "diagnostic_only": True,
        "automatic_visual_acceptance": False,
        "errors": errors,
        "warnings": warnings,
        "text_boxes": entries,
    }


def main():
    parser = argparse.ArgumentParser(description="Audit configured text boxes against an Office-rendered page.")
    parser.add_argument("page_dir", help="Page directory containing manifest.json.")
    parser.add_argument("--render", required=True, help="Office-rendered PNG, usually calibration/office-render/slide-1.png.")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest file relative to page_dir.")
    parser.add_argument("--out", help="Report path; defaults to calibration/text-audit.json.")
    parser.add_argument("--ink-threshold", type=int, default=16, help="Minimum RGB contrast from the local background.")
    args = parser.parse_args()
    page_dir = Path(args.page_dir).expanduser().resolve()
    manifest_path = (page_dir / args.manifest).resolve()
    render_path = Path(args.render).expanduser().resolve()
    if not manifest_path.is_file():
        raise SystemExit(f"manifest not found: {manifest_path}")
    if not render_path.is_file():
        raise SystemExit(f"render not found: {render_path}")
    if not 0 <= args.ink_threshold <= 255:
        raise SystemExit("--ink-threshold must be between 0 and 255")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"could not read manifest: {manifest_path}: {exc}") from exc
    try:
        with Image.open(render_path) as opened:
            render = opened.convert("RGB")
    except (OSError, ValueError) as exc:
        raise SystemExit(f"could not read render image: {render_path}: {exc}") from exc
    report = audit_manifest(manifest, render, ink_threshold=args.ink_threshold)
    report["manifest"] = str(manifest_path)
    report["render"] = str(render_path)
    report_path = Path(args.out).expanduser().resolve() if args.out else page_dir / "calibration" / "text-audit.json"
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
