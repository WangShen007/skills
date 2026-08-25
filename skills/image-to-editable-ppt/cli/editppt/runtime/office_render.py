#!/usr/bin/env python3
"""Render a page PPTX through a local Office-compatible renderer."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from deck_run_state import sha256_file, write_json


def find_renderer() -> str:
    for candidate in (
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        "/opt/homebrew/bin/soffice",
        "/usr/local/bin/soffice",
    ):
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
    raise SystemExit(
        "Office renderer unavailable: install LibreOffice/soffice or add it to PATH"
    )


def renderer_version(executable: str) -> str:
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else "unknown"


def convert_to_pdf(executable: str, pptx: Path, work_dir: Path, timeout: int) -> Path:
    profile = work_dir / "lo-profile"
    profile.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "--headless",
        f"-env:UserInstallation={profile.as_uri()}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(work_dir),
        str(pptx),
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"Office render timed out after {timeout}s: {pptx}") from exc
    if result.returncode != 0:
        raise SystemExit(
            "Office renderer failed with exit code "
            f"{result.returncode}:\n{result.stdout}{result.stderr}"
        )
    expected = work_dir / f"{pptx.stem}.pdf"
    if expected.is_file():
        return expected
    candidates = sorted(work_dir.glob("*.pdf"))
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit(f"Office renderer did not produce a PDF in {work_dir}")


def requested_fonts(manifest: dict) -> list[str]:
    names: set[str] = set()
    for item in manifest.get("text_boxes", []):
        for key in ("font", "font_name", "font_family", "typeface"):
            value = item.get(key)
            if value:
                names.add(str(value))
        for run in item.get("runs", []):
            for key in ("font", "font_name", "font_family", "typeface"):
                value = run.get(key)
                if value:
                    names.add(str(value))
    return sorted(names)


def font_inventory(manifest: dict) -> dict:
    fonts = requested_fonts(manifest)
    fc_match = shutil.which("fc-match")
    entries = []
    for font in fonts:
        match = None
        match_error = None
        if fc_match:
            try:
                result = subprocess.run(
                    [fc_match, "--format=%{family}\\n", font],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                match = (result.stdout or "").strip() or None
            except (OSError, subprocess.TimeoutExpired) as exc:
                match_error = str(exc)
        available = match is not None if fc_match else None
        matched_families = {
            part.strip().casefold() for part in (match or "").split(",") if part.strip()
        }
        substituted = (
            bool(match) and font.casefold() not in matched_families
            if fc_match
            else None
        )
        entry = {
            "requested": font,
            "system_match": match,
            "available": available,
            "substituted": substituted,
        }
        if match_error:
            entry["error"] = match_error
        entries.append(entry)
    return {
        "requested": fonts,
        "fc_match_available": bool(fc_match),
        "entries": entries,
        "replacement_detection": "soffice does not expose per-run substitutions; compare the Office render and inspect the entries above",
    }


def render_page(page_dir, *, pptx_name="page.pptx", manifest_name="manifest.json", out=None, dpi=144, timeout=120):
    page_dir = Path(page_dir).expanduser().resolve()
    pptx = (page_dir / pptx_name).resolve()
    manifest_path = (page_dir / manifest_name).resolve()
    if not pptx.is_file():
        raise SystemExit(f"page PPTX not found: {pptx}")
    if not manifest_path.is_file():
        raise SystemExit(f"page manifest not found: {manifest_path}")
    if dpi <= 0:
        raise SystemExit("dpi must be greater than 0")
    if timeout <= 0:
        raise SystemExit("timeout must be greater than 0")

    output_dir = Path(out).expanduser().resolve() if out else page_dir / "calibration" / "office-render"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.glob("slide-*.png"):
        if path.is_file():
            path.unlink()
    for name in ("page.pdf", "renderer.json"):
        path = output_dir / name
        if path.is_file():
            path.unlink()

    executable = find_renderer()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"could not read page manifest: {manifest_path}: {exc}") from exc
    with tempfile.TemporaryDirectory(prefix="editppt-office-") as temp_name:
        temp_dir = Path(temp_name)
        pdf = convert_to_pdf(executable, pptx, temp_dir, timeout)
        output_pdf = output_dir / "page.pdf"
        shutil.copy2(pdf, output_pdf)
        try:
            import fitz
        except ImportError as exc:
            raise SystemExit("PyMuPDF (fitz) is required to rasterize the Office PDF") from exc
        document = fitz.open(output_pdf)
        slides = []
        scale = float(dpi) / 72.0
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image_path = output_dir / f"slide-{index}.png"
            pixmap.save(str(image_path))
            slides.append({"page": index, "path": image_path.name, "width_px": pixmap.width, "height_px": pixmap.height})
        page_count = len(document)
        document.close()
    if page_count == 0:
        raise SystemExit(f"Office renderer produced no pages: {pptx}")

    metadata = {
        "schema_version": 1,
        "renderer": "LibreOffice/soffice",
        "executable": executable,
        "version": renderer_version(executable),
        "platform": platform.platform(),
        "input": {
            "pptx": str(pptx),
            "pptx_sha256": sha256_file(pptx),
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
        },
        "output_dir": str(output_dir),
        "pdf": "page.pdf",
        "dpi": dpi,
        "page_count": page_count,
        "slides": slides,
        "font_inventory": font_inventory(manifest),
    }
    renderer_path = output_dir / "renderer.json"
    write_json(renderer_path, metadata)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata


def main():
    parser = argparse.ArgumentParser(description="Render page.pptx with LibreOffice/soffice for calibration.")
    parser.add_argument("page_dir", help="Page directory containing page.pptx and manifest.json.")
    parser.add_argument("--pptx", default="page.pptx", help="PPTX file relative to page_dir.")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest file relative to page_dir.")
    parser.add_argument("--out", help="Output directory; defaults to calibration/office-render.")
    parser.add_argument("--dpi", type=int, default=144, help="PDF rasterization DPI (default: 144).")
    parser.add_argument("--timeout", type=int, default=120, help="Office conversion timeout in seconds.")
    args = parser.parse_args()
    render_page(
        args.page_dir,
        pptx_name=args.pptx,
        manifest_name=args.manifest,
        out=args.out,
        dpi=args.dpi,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
