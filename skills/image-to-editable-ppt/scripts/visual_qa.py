#!/usr/bin/env python3
"""Create reproducible source-vs-render visual QA artifacts for one slide.

This tool is a comparison aid, not an automatic visual-fidelity judge.  It
aligns the source to the rendered slide canvas, writes an overlay and an
amplified diff, and produces region crops plus diagnostic metrics.  The
metrics never replace an inspected reviewer decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFont, ImageOps, ImageStat


Region = tuple[float, float, float, float]
FIT_MODES = ("auto", "stretch", "contain", "crop")
DEFAULT_FIT = "auto"
ASPECT_RATIO_TOLERANCE = 0.01
REGION_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$")
MAX_REGION_NAME_LENGTH = 64
REVIEW_STATUS_VALUES = ("needs_review", "pass", "fail")
REVIEW_CHECK_KEYS = (
    "global_canvas",
    "structural_completeness",
    "text_scale_and_wrapping",
    "routing_and_layering",
    "style_and_detail",
)
REVIEW_CHECK_VALUES = ("pass", "fail")

# These regions are deliberately page-agnostic.  Applications with meaningful
# semantic regions should pass them explicitly for that comparison.
DEFAULT_REGIONS: dict[str, Region] = {
    "full_slide": (0.00, 0.00, 1.00, 1.00),
    "top_band": (0.00, 0.00, 1.00, 0.20),
    "middle_band": (0.00, 0.20, 1.00, 0.60),
    "bottom_band": (0.00, 0.80, 1.00, 0.20),
}


def _region_error(message: str) -> ValueError:
    return ValueError(f"invalid region: {message}")


def validate_region(name: str, region: Sequence[float]) -> Region:
    """Validate and return a normalized ``x, y, width, height`` region."""

    if not isinstance(name, str) or not name:
        raise _region_error("name is required")
    if len(name) > MAX_REGION_NAME_LENGTH or not REGION_NAME_PATTERN.fullmatch(name):
        raise _region_error(
            "name must be a lowercase slug (letters, digits, '-' or '_'), "
            "starting with a letter and no longer than 64 characters"
        )

    if len(region) != 4:
        raise _region_error("coordinates must use x,y,width,height")
    try:
        values = tuple(float(value) for value in region)
    except (TypeError, ValueError) as exc:
        raise _region_error("coordinates must be numeric") from exc
    if not all(math.isfinite(value) for value in values):
        raise _region_error("coordinates must be finite numbers")

    x, y, width, height = values
    if x < 0 or y < 0:
        raise _region_error("x and y must be at least 0")
    if width <= 0 or height <= 0:
        raise _region_error("width and height must be greater than 0")
    if x + width > 1 or y + height > 1:
        raise _region_error("x+width and y+height must be at most 1")
    return x, y, width, height


def validate_regions(regions: Mapping[str, Sequence[float]]) -> dict[str, Region]:
    """Validate every region before any output artifact is written."""

    validated: dict[str, Region] = {}
    for name, region in regions.items():
        if name in validated:
            raise _region_error(f"duplicate name {name!r}")
        validated[name] = validate_region(name, region)
    if not validated:
        raise _region_error("at least one region is required")
    return validated


def parse_region(spec: str) -> tuple[str, Region]:
    """Parse ``name=x,y,width,height`` in normalized 0..1 coordinates."""

    try:
        name, raw_values = spec.split("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "region must use name=x,y,width,height"
        ) from exc

    values = raw_values.split(",")
    if len(values) != 4:
        raise argparse.ArgumentTypeError(
            "region must use name=x,y,width,height"
        )
    try:
        numeric_values = tuple(float(value.strip()) for value in values)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "region coordinates must be numeric"
        ) from exc
    try:
        return name, validate_region(name, numeric_values)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def select_regions(
    custom_regions: Sequence[tuple[str, Region]],
    *,
    include_defaults: bool = False,
) -> dict[str, Region]:
    """Select built-in or explicitly supplied regions.

    Explicit regions are custom-only by default.  ``include_defaults`` is an
    opt-in escape hatch for callers that want generic defaults plus custom
    regions; it never adds application-specific regions.
    """

    regions: dict[str, Region] = dict(DEFAULT_REGIONS) if include_defaults or not custom_regions else {}
    seen_custom: set[str] = set()
    for name, region in custom_regions:
        if name in seen_custom:
            raise _region_error(f"duplicate name {name!r}")
        if name in regions:
            raise _region_error(
                f"duplicate name {name!r}; it is already a selected built-in region"
            )
        seen_custom.add(name)
        regions[name] = validate_region(name, region)
    return validate_regions(regions)


def _size_aspect_ratio(size: tuple[int, int]) -> float:
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"image dimensions must be positive, got {size!r}")
    return width / height


def alignment_metadata(
    requested_fit: str,
    source_size: tuple[int, int],
    render_size: tuple[int, int],
    *,
    tolerance: float = ASPECT_RATIO_TOLERANCE,
) -> dict[str, object]:
    """Resolve alignment and return reproducible aspect-ratio evidence."""

    if requested_fit not in FIT_MODES:
        raise ValueError(f"fit must be one of {', '.join(FIT_MODES)}")
    if tolerance < 0 or not math.isfinite(tolerance):
        raise ValueError("aspect-ratio tolerance must be a finite non-negative number")

    source_ratio = _size_aspect_ratio(source_size)
    render_ratio = _size_aspect_ratio(render_size)
    delta = source_ratio - render_ratio
    absolute_delta = abs(delta)
    relative_delta = absolute_delta / render_ratio
    material_mismatch = relative_delta > tolerance

    if requested_fit == "auto":
        resolved_fit = "contain" if material_mismatch else "stretch"
    else:
        resolved_fit = requested_fit

    warning: str | None = None
    if material_mismatch and requested_fit == "auto":
        warning = (
            "source/render aspect ratios differ materially; auto resolved to "
            "contain so source geometry is not silently stretched"
        )
    elif material_mismatch and requested_fit == "stretch":
        warning = (
            "source/render aspect ratios differ materially and explicit stretch "
            "may hide canvas distortion"
        )
    elif material_mismatch and requested_fit == "crop":
        warning = (
            "source/render aspect ratios differ materially and explicit crop "
            "may discard source content"
        )

    return {
        "requested_fit": requested_fit,
        "resolved_fit": resolved_fit,
        "source_size": list(source_size),
        "render_size": list(render_size),
        "source_aspect_ratio": round(source_ratio, 6),
        "render_aspect_ratio": round(render_ratio, 6),
        "aspect_ratio_delta": round(delta, 6),
        "aspect_ratio_delta_abs": round(absolute_delta, 6),
        "aspect_ratio_relative_delta": round(relative_delta, 6),
        "aspect_ratio_delta_pct": round(relative_delta * 100, 3),
        "aspect_ratio_tolerance": tolerance,
        "material_mismatch": material_mismatch,
        "warning": warning,
    }


def resolve_fit(
    fit: str,
    source_size: tuple[int, int],
    render_size: tuple[int, int],
    *,
    tolerance: float = ASPECT_RATIO_TOLERANCE,
) -> str:
    """Return the concrete alignment policy for a requested fit mode."""

    return str(alignment_metadata(fit, source_size, render_size, tolerance=tolerance)["resolved_fit"])


def align_source(source: Image.Image, size: tuple[int, int], fit: str = DEFAULT_FIT) -> Image.Image:
    """Map the source onto the render canvas without changing the render."""

    resolved_fit = resolve_fit(fit, source.size, size)
    if source.size == size:
        return source.copy()
    if resolved_fit == "stretch":
        return source.resize(size, Image.Resampling.LANCZOS)
    if resolved_fit == "crop":
        return ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)

    contained = ImageOps.contain(source, size, method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
    canvas.paste(contained, offset)
    return canvas


def load_rgb_image(path: Path) -> Image.Image:
    """Load an image with EXIF orientation applied before RGB conversion."""

    try:
        with Image.open(path) as opened:
            oriented = ImageOps.exif_transpose(opened)
            return oriented.convert("RGB")
    except (OSError, ValueError) as exc:
        raise SystemExit(f"could not read image {path}: {exc}") from exc


def region_box(region: Region, size: tuple[int, int]) -> tuple[int, int, int, int]:
    """Convert normalized ``x,y,width,height`` to a pixel crop box."""

    validate_region("region", region)
    if size[0] <= 0 or size[1] <= 0:
        raise ValueError(f"image dimensions must be positive, got {size!r}")
    x, y, width, height = region
    left = max(0, min(size[0] - 1, round(x * size[0])))
    top = max(0, min(size[1] - 1, round(y * size[1])))
    right = max(left + 1, min(size[0], round((x + width) * size[0])))
    bottom = max(top + 1, min(size[1], round((y + height) * size[1])))
    return left, top, right, bottom


def diff_metrics(
    source: Image.Image,
    render: Image.Image,
    box: tuple[int, int, int, int],
    threshold: int,
) -> dict[str, object]:
    """Return simple diagnostic metrics for one aligned region."""

    source_crop = source.crop(box)
    render_crop = render.crop(box)
    raw_diff = ImageChops.difference(source_crop, render_crop)
    channel_means = ImageStat.Stat(raw_diff).mean
    gray = raw_diff.convert("L")
    changed = sum(1 for value in gray.tobytes() if value >= threshold)
    total = gray.width * gray.height
    return {
        "box_px": list(box),
        "mean_abs_rgb": round(sum(channel_means) / len(channel_means), 3),
        "pixels_over_threshold": changed,
        "pixels_over_threshold_pct": round(100 * changed / max(1, total), 3),
        "threshold": threshold,
    }


def labeled_region_panel(
    name: str,
    source: Image.Image,
    render: Image.Image,
    diff: Image.Image,
    box: tuple[int, int, int, int],
) -> Image.Image:
    """Build a three-column crop for one named region."""

    crops = [
        ("source", source.crop(box)),
        ("render", render.crop(box)),
        ("diff", diff.crop(box)),
    ]
    thumbs: list[tuple[str, Image.Image]] = []
    for label, crop in crops:
        thumb = crop.copy()
        thumb.thumbnail((520, 320), Image.Resampling.LANCZOS)
        thumbs.append((label, thumb))

    gap = 12
    label_height = 28
    width = sum(image.width for _, image in thumbs) + gap * (len(thumbs) + 1)
    height = label_height + max(image.height for _, image in thumbs) + gap * 2
    panel = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    draw.text((gap, 6), name, fill="black", font=font)
    cursor = gap
    for label, image in thumbs:
        draw.text((cursor, label_height + 2), label, fill="black", font=font)
        panel.paste(image, (cursor, label_height + 18))
        cursor += image.width + gap
    return panel


def make_contact_sheet(panels: Iterable[Image.Image], out_path: Path) -> None:
    """Arrange region panels in a readable two-column contact sheet."""

    panel_list = list(panels)
    if not panel_list:
        return
    columns = 2
    rows = (len(panel_list) + columns - 1) // columns
    cell_width = max(panel.width for panel in panel_list)
    cell_height = max(panel.height for panel in panel_list)
    sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "#eeeeee")
    for index, panel in enumerate(panel_list):
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height
        sheet.paste(panel, (x, y))
    sheet.save(out_path)


def parse_review_check(spec: str) -> tuple[str, str]:
    """Parse one inspected checklist item as ``name=pass|fail``."""

    try:
        name, status = (part.strip() for part in spec.split("=", 1))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "review check must use name=pass|fail"
        ) from exc
    if name not in REVIEW_CHECK_KEYS:
        allowed = ", ".join(REVIEW_CHECK_KEYS)
        raise argparse.ArgumentTypeError(
            f"review check name must be one of: {allowed}"
        )
    if status not in REVIEW_CHECK_VALUES:
        raise argparse.ArgumentTypeError(
            "review check status must be pass or fail"
        )
    return name, status


def validate_review_checklist(
    review_status: str,
    checklist: Mapping[str, str],
) -> dict[str, str]:
    """Validate reviewer-owned status/checklist consistency before writing."""

    if review_status not in REVIEW_STATUS_VALUES:
        raise ValueError(
            f"invalid review status; expected one of {', '.join(REVIEW_STATUS_VALUES)}"
        )

    normalized = {name: "unreviewed" for name in REVIEW_CHECK_KEYS}
    for name, status in checklist.items():
        if name not in REVIEW_CHECK_KEYS:
            raise ValueError(f"invalid review checklist item {name!r}")
        if status not in (*REVIEW_CHECK_VALUES, "unreviewed"):
            raise ValueError(
                f"invalid review checklist status {status!r} for {name!r}"
            )
        normalized[name] = status

    if review_status != "needs_review":
        missing = [name for name, status in normalized.items() if status == "unreviewed"]
        if missing:
            raise ValueError(
                f"review_status={review_status} requires an explicit result for every "
                f"checklist item; missing: {', '.join(missing)}"
            )
        if review_status == "pass" and any(
            status != "pass" for status in normalized.values()
        ):
            raise ValueError(
                "review_status=pass requires every checklist item to be pass"
            )
        if review_status == "fail" and not any(
            status == "fail" for status in normalized.values()
        ):
            raise ValueError(
                "review_status=fail requires at least one failed checklist item"
            )
    return normalized


def build_review_checklist(
    review_status: str,
    checks: Sequence[tuple[str, str]],
) -> dict[str, str]:
    """Build a complete checklist and reject duplicate command-line entries."""

    checklist: dict[str, str] = {}
    for name, status in checks:
        if name in checklist:
            raise ValueError(f"duplicate review checklist item {name!r}")
        checklist[name] = status
    return validate_review_checklist(review_status, checklist)


GENERATED_OUTPUT_NAMES = (
    "source_aligned.png",
    "overlay.png",
    "diff.png",
    "regions_contact.png",
    "metrics.json",
    "review_summary.json",
)


def clear_generated_output(out_dir: Path) -> None:
    """Remove artifacts generated by an earlier run in this QA directory."""

    for name in GENERATED_OUTPUT_NAMES:
        path = out_dir / name
        if path.exists() and not path.is_file() and not path.is_symlink():
            raise OSError(f"generated artifact path is not a file: {path}")
        if path.is_file() or path.is_symlink():
            path.unlink()
    for path in out_dir.glob("region_*.png"):
        if path.exists() and not path.is_file() and not path.is_symlink():
            raise OSError(f"generated region path is not a file: {path}")
        if path.is_file() or path.is_symlink():
            path.unlink()


def resolve_output_dir(out: Path | None, run: Path | None, page: str) -> Path:
    """Resolve the stable run-local default output directory."""

    if out is not None:
        return out.expanduser().resolve()
    if run is None:
        raise ValueError("provide --run for the stable default or an explicit --out directory")
    if not page or not REGION_NAME_PATTERN.fullmatch(page):
        raise ValueError("page must be a safe lowercase slug such as page_001")
    return (run.expanduser() / "final" / "visual_qa" / page).resolve()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_candidate_context(run: Path | None) -> dict[str, object] | None:
    """Attach current-candidate identity to run-local review evidence."""

    if run is None:
        return None
    deck_path = run.expanduser().resolve() / "deck_manifest.json"
    if not deck_path.is_file():
        return None
    try:
        deck = json.loads(deck_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    candidate = deck.get("current_candidate")
    if not isinstance(candidate, dict) or not candidate.get("candidate_id"):
        return None
    raw_path = Path(str(candidate.get("pptx", "")))
    pptx_path = raw_path if raw_path.is_absolute() else deck_path.parent / raw_path
    if not pptx_path.is_file():
        return {
            "candidate_id": candidate.get("candidate_id"),
            "pptx": str(pptx_path),
            "pptx_sha256": candidate.get("pptx_sha256"),
            "manifest_sha256": candidate.get("manifest_sha256"),
            "hash_verified": False,
        }
    actual_hash = file_sha256(pptx_path)
    return {
        "candidate_id": candidate.get("candidate_id"),
        "pptx": str(pptx_path),
        "pptx_sha256": actual_hash,
        "manifest_sha256": candidate.get("manifest_sha256"),
        "hash_verified": actual_hash == candidate.get("pptx_sha256"),
    }


def review_summary(
    *,
    metrics: Mapping[str, object],
    artifacts: Mapping[str, object],
    review_status: str,
    reviewer: str | None,
    notes: str,
    checklist: Mapping[str, str] | None = None,
    candidate: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Create a durable reviewer-owned conclusion separate from metrics."""

    normalized_checklist = validate_review_checklist(
        review_status,
        checklist or {},
    )
    decision = None if review_status == "needs_review" else review_status
    summary = {
        "schema_version": 1,
        "metrics": {
            "file": "metrics.json",
            "diagnostic_only": True,
            "automatic_acceptance": False,
        },
        "review": {
            "status": review_status,
            "decision": decision,
            "reviewer": reviewer,
            "notes": notes,
            "checklist": normalized_checklist,
            "checklist_complete": all(
                status != "unreviewed" for status in normalized_checklist.values()
            ),
        },
        "review_status": review_status,
        "metrics_are_diagnostic": True,
        "alignment_warnings": list(metrics.get("warnings", [])),
        "regions": list(metrics.get("regions", {}).keys()),
        "artifacts": dict(artifacts),
    }
    if candidate is not None:
        summary["candidate"] = dict(candidate)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare an original slide image with a rendered editable slide."
    )
    parser.add_argument("--source", required=True, type=Path, help="original page image")
    parser.add_argument("--render", required=True, type=Path, help="rendered final slide image")
    parser.add_argument(
        "--out",
        type=Path,
        help="explicit QA artifact directory (overrides the --run default)",
    )
    parser.add_argument(
        "--run",
        type=Path,
        help="prepared run directory; defaults output to final/visual_qa/<page>",
    )
    parser.add_argument(
        "--page",
        default="page_001",
        help="page slug used below --run (default: page_001)",
    )
    parser.add_argument(
        "--fit",
        choices=FIT_MODES,
        default=DEFAULT_FIT,
        help="source-to-render alignment policy (default: auto)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=30,
        help="grayscale diff threshold for triage metrics (default: 30)",
    )
    parser.add_argument(
        "--region",
        action="append",
        type=parse_region,
        default=[],
        metavar="NAME=X,Y,W,H",
        help="select a custom normalized region; repeat for multiple regions",
    )
    parser.add_argument(
        "--include-default-regions",
        action="store_true",
        help="with --region, also include the generic built-in regions",
    )
    parser.add_argument(
        "--review-status",
        choices=REVIEW_STATUS_VALUES,
        default="needs_review",
        help=(
            "reviewer conclusion to record; pass/fail require one --review-check "
            "for every checklist item"
        ),
    )
    parser.add_argument(
        "--review-check",
        action="append",
        type=parse_review_check,
        default=[],
        metavar="NAME=PASS|FAIL",
        help="record an inspected checklist item; repeat for each item",
    )
    parser.add_argument("--reviewer", help="optional reviewer identity for the summary")
    parser.add_argument("--review-notes", default="", help="optional reviewer notes")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source.is_file():
        raise SystemExit(f"source image not found: {args.source}")
    if not args.render.is_file():
        raise SystemExit(f"render image not found: {args.render}")
    if not 0 <= args.threshold <= 255:
        raise SystemExit("threshold must be between 0 and 255")

    try:
        regions = select_regions(
            args.region,
            include_defaults=args.include_default_regions,
        )
        checklist = build_review_checklist(args.review_status, args.review_check)
        out_dir = resolve_output_dir(args.out, args.run, args.page)
    except ValueError as exc:
        # This happens before mkdir or any region image is written.
        raise SystemExit(str(exc)) from exc

    source = load_rgb_image(args.source)
    render = load_rgb_image(args.render)
    alignment = alignment_metadata(args.fit, source.size, render.size)
    aligned = align_source(source, render.size, str(alignment["resolved_fit"]))

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        clear_generated_output(out_dir)
    except OSError as exc:
        raise SystemExit(f"could not prepare QA output directory {out_dir}: {exc}") from exc
    artifact_paths: dict[str, object] = {
        "source_aligned": "source_aligned.png",
        "overlay": "overlay.png",
        "diff": "diff.png",
        "regions_contact": "regions_contact.png",
        "metrics": "metrics.json",
        "review_summary": "review_summary.json",
        "regions": {},
    }
    aligned.save(out_dir / "source_aligned.png")

    overlay = Image.blend(aligned, render, 0.5)
    overlay.save(out_dir / "overlay.png")
    raw_diff = ImageChops.difference(aligned, render)
    amplified_diff = ImageEnhance.Contrast(raw_diff).enhance(4.0)
    amplified_diff.save(out_dir / "diff.png")

    warnings = [alignment["warning"]] if alignment["warning"] else []
    metrics: dict[str, object] = {
        "schema_version": 2,
        "source_size": list(source.size),
        "render_size": list(render.size),
        "aligned_size": list(aligned.size),
        "source_aspect_ratio": alignment["source_aspect_ratio"],
        "render_aspect_ratio": alignment["render_aspect_ratio"],
        "aspect_ratio_delta": alignment["aspect_ratio_delta"],
        "aspect_ratio_relative_delta": alignment["aspect_ratio_relative_delta"],
        "alignment": alignment,
        # These aliases keep the essential policy obvious to simple consumers.
        "alignment_requested": alignment["requested_fit"],
        "alignment_resolved": alignment["resolved_fit"],
        "threshold": args.threshold,
        "regions_contract": "normalized x,y,width,height; positive and contained in 0..1",
        "warnings": warnings,
        "regions": {},
        "output_dir": str(out_dir),
    }
    region_panels: list[Image.Image] = []
    for name, normalized_region in regions.items():
        box = region_box(normalized_region, render.size)
        region_metrics = diff_metrics(aligned, render, box, args.threshold)
        region_metrics["normalized"] = list(normalized_region)
        metrics["regions"][name] = region_metrics  # type: ignore[index]
        panel = labeled_region_panel(name, aligned, render, amplified_diff, box)
        region_filename = f"region_{name}.png"
        panel.save(out_dir / region_filename)
        artifact_paths["regions"][name] = region_filename  # type: ignore[index]
        region_panels.append(panel)

    full_box = (0, 0, render.width, render.height)
    metrics["full"] = diff_metrics(aligned, render, full_box, args.threshold)
    make_contact_sheet(region_panels, out_dir / "regions_contact.png")
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = review_summary(
        metrics=metrics,
        artifacts=artifact_paths,
        review_status=args.review_status,
        reviewer=args.reviewer,
        notes=args.review_notes,
        checklist=checklist,
        candidate=load_candidate_context(args.run),
    )
    (out_dir / "review_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
