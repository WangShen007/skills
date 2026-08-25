from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


SKILL_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = SKILL_ROOT / "cli" / "editppt" / "runtime"
sys.path.insert(0, str(RUNTIME_ROOT))

from text_audit import audit_manifest, count_ink_lines, source_box_to_render  # noqa: E402


def manifest_for(*, expected_lines=1, wrap_policy="fixed", font_size=24, size_group="headers"):
    return {
        "slide": {"width": 10, "height": 5},
        "content_box": {"left": 0, "top": 0, "width": 10, "height": 5},
        "source": {"width_px": 1000, "height_px": 500},
        "text_boxes": [
            {
                "id": "heading",
                "box_px": [100, 100, 800, 100],
                "font_size": font_size,
                "color": "#000000",
                "size_group": size_group,
                "expected_lines": expected_lines,
                "wrap_policy": wrap_policy,
            }
        ],
    }


def render_with_lines(line_count: int) -> Image.Image:
    image = Image.new("RGB", (1000, 500), "white")
    draw = ImageDraw.Draw(image)
    for index in range(line_count):
        top = 120 + index * 34
        draw.rectangle((130, top, 520, top + 16), fill="black")
    return image


class TextAuditTests(unittest.TestCase):
    def test_source_box_mapping_and_line_counter(self):
        manifest = manifest_for()
        box = source_box_to_render(manifest, [100, 100, 800, 100], (1000, 500))
        self.assertEqual(box, (100, 100, 900, 200))
        self.assertEqual(count_ink_lines(Image.new("1", (100, 80), 0)), 0)

    def test_fixed_line_audit_passes_for_single_line_ink(self):
        report = audit_manifest(manifest_for(), render_with_lines(1))
        self.assertTrue(report["passed"])
        self.assertFalse(report["errors"])
        self.assertEqual(report["text_boxes"][0]["actual_lines"], 1)

    def test_fixed_line_audit_detects_unexpected_wrap(self):
        report = audit_manifest(manifest_for(), render_with_lines(2))
        self.assertFalse(report["passed"])
        self.assertTrue(any(issue["kind"] == "unexpected_wrapping" for issue in report["errors"]))

    def test_size_group_mismatch_is_a_hard_error(self):
        manifest = manifest_for()
        manifest["text_boxes"].append(
            {
                "id": "second-heading",
                "box_px": [100, 220, 800, 100],
                "font_size": 20,
                "color": "#000000",
                "size_group": "headers",
            }
        )
        report = audit_manifest(manifest, render_with_lines(1))
        self.assertFalse(report["passed"])
        self.assertTrue(any(issue["kind"] == "size_group_mismatch" for issue in report["errors"]))

    def test_edge_crossing_is_reported_as_clipping_risk(self):
        manifest = manifest_for()
        image = Image.new("RGB", (1000, 500), "white")
        ImageDraw.Draw(image).rectangle((90, 120, 920, 135), fill="black")
        report = audit_manifest(manifest, image)
        self.assertFalse(report["passed"])
        self.assertTrue(any(issue["kind"] == "text_box_edge_risk" for issue in report["errors"]))

    def test_target_ink_height_mismatch_is_a_hard_error(self):
        manifest = manifest_for()
        manifest["text_boxes"][0]["target_ink_height_px"] = 25
        report = audit_manifest(manifest, render_with_lines(1))
        self.assertFalse(report["passed"])
        self.assertTrue(
            any(
                issue["kind"] == "ink_size_mismatch" and issue["dimension"] == "height"
                for issue in report["errors"]
            )
        )

    def test_target_font_size_mismatch_is_a_hard_error(self):
        manifest = manifest_for()
        manifest["text_boxes"][0]["target_font_size"] = 30
        report = audit_manifest(manifest, render_with_lines(1))
        self.assertFalse(report["passed"])
        self.assertTrue(any(issue["kind"] == "font_size_mismatch" for issue in report["errors"]))


if __name__ == "__main__":
    unittest.main()
