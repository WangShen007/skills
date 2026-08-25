from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw


SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


visual_qa = load_module("visual_qa_under_test", SKILL_ROOT / "scripts" / "visual_qa.py")
runtime_env = load_module(
    "runtime_env_under_test",
    SKILL_ROOT / "cli" / "editppt" / "runtime" / "runtime_env.py",
)


class VisualQaContractTests(unittest.TestCase):
    def test_region_contract_and_pixel_conversion(self):
        parsed = visual_qa.parse_region("content_center=0.2,0.1,0.3,0.4")
        self.assertEqual(parsed, ("content_center", (0.2, 0.1, 0.3, 0.4)))
        self.assertEqual(
            visual_qa.region_box(parsed[1], (100, 100)),
            (20, 10, 50, 50),
        )

    def test_invalid_region_name_dimensions_and_bounds(self):
        invalid_specs = (
            "bad/name=0,0,1,1",
            "BadName=0,0,1,1",
            "zero=0,0,0,1",
            "negative=0,0.1,-0.1,0.2",
            "overflow=0.8,0,0.3,1",
            "nan=nan,0,1,1",
        )
        for spec in invalid_specs:
            with self.subTest(spec=spec):
                with self.assertRaises(visual_qa.argparse.ArgumentTypeError):
                    visual_qa.parse_region(spec)

    def test_defaults_are_generic_and_custom_regions_are_custom_only(self):
        defaults = visual_qa.select_regions([])
        self.assertEqual(set(defaults), {"full_slide", "top_band", "middle_band", "bottom_band"})
        self.assertNotIn("representation", defaults)
        self.assertNotIn("transformer", defaults)
        self.assertNotIn("sscl", defaults)

        custom = visual_qa.select_regions([("focus_area", (0.1, 0.1, 0.2, 0.2))])
        self.assertEqual(set(custom), {"focus_area"})

        with_defaults = visual_qa.select_regions(
            [("focus_area", (0.1, 0.1, 0.2, 0.2))],
            include_defaults=True,
        )
        self.assertIn("focus_area", with_defaults)
        self.assertIn("full_slide", with_defaults)

        with self.assertRaisesRegex(ValueError, "already a selected built-in"):
            visual_qa.select_regions(
                [("full_slide", (0.1, 0.1, 0.2, 0.2))],
                include_defaults=True,
            )

        with self.assertRaisesRegex(ValueError, "duplicate name"):
            visual_qa.select_regions(
                [
                    ("focus_area", (0.1, 0.1, 0.2, 0.2)),
                    ("focus_area", (0.2, 0.2, 0.2, 0.2)),
                ]
            )

    def test_auto_alignment_preserves_material_aspect_difference(self):
        near = visual_qa.alignment_metadata("auto", (1600, 900), (1599, 900))
        self.assertEqual(near["resolved_fit"], "stretch")
        self.assertFalse(near["material_mismatch"])

        different = visual_qa.alignment_metadata("auto", (4, 3), (16, 9))
        self.assertEqual(visual_qa.resolve_fit("auto", (4, 3), (16, 9)), "contain")
        self.assertEqual(different["resolved_fit"], "contain")
        self.assertGreater(different["aspect_ratio_relative_delta"], 0.2)
        self.assertIn("contain", str(different["warning"]))

        for explicit_fit in ("stretch", "contain", "crop"):
            with self.subTest(explicit_fit=explicit_fit):
                self.assertEqual(
                    visual_qa.resolve_fit(explicit_fit, (4, 3), (16, 9)),
                    explicit_fit,
                )

    def test_invalid_regions_fail_before_output_directory_is_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.png"
            render = root / "render.png"
            Image.new("RGB", (40, 30), "white").save(source)
            Image.new("RGB", (40, 30), "white").save(render)
            output = root / "qa"
            with contextlib.redirect_stdout(io.StringIO()):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        visual_qa.main(
                            [
                                "--source",
                                str(source),
                                "--render",
                                str(render),
                                "--out",
                                str(output),
                                "--region",
                                "zero=0,0,0,1",
                            ]
                        )
            self.assertFalse(output.exists())

    def test_metrics_artifacts_and_review_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.png"
            render = root / "render.png"
            source_image = Image.new("RGB", (40, 30), "#eeeeee")
            ImageDraw.Draw(source_image).rectangle((12, 8, 20, 18), fill="#2764a5")
            source_image.save(source)
            render_image = Image.new("RGB", (64, 36), "#eeeeee")
            ImageDraw.Draw(render_image).rectangle((32, 8, 45, 22), fill="#d34a4a")
            render_image.save(render)

            run_dir = root / "prepared-run"
            output = run_dir / "final" / "visual_qa" / "page_001"
            with contextlib.redirect_stdout(io.StringIO()):
                result = visual_qa.main(
                    [
                        "--source",
                        str(source),
                        "--render",
                        str(render),
                        "--run",
                        str(run_dir),
                        "--page",
                        "page_001",
                        "--region",
                        "changed_area=0.4,0.1,0.35,0.7",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertTrue((output / "regions_contact.png").is_file())
            self.assertTrue((output / "overlay.png").is_file())
            self.assertTrue((output / "diff.png").is_file())

            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["alignment_requested"], "auto")
            self.assertEqual(metrics["alignment_resolved"], "contain")
            self.assertEqual(set(metrics["regions"]), {"changed_area"})
            self.assertEqual(metrics["regions"]["changed_area"]["normalized"], [0.4, 0.1, 0.35, 0.7])
            self.assertGreater(metrics["regions"]["changed_area"]["pixels_over_threshold"], 0)
            self.assertIn("source_aspect_ratio", metrics)
            self.assertIn("render_aspect_ratio", metrics)
            self.assertIn("aspect_ratio_delta", metrics)
            self.assertTrue(metrics["warnings"])

            summary = json.loads((output / "review_summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["metrics"]["diagnostic_only"])
            self.assertFalse(summary["metrics"]["automatic_acceptance"])
            self.assertEqual(summary["review"]["status"], "needs_review")
            self.assertIsNone(summary["review"]["decision"])
            self.assertFalse(summary["review"]["checklist_complete"])
            self.assertEqual(summary["regions"], ["changed_area"])

    def test_review_pass_requires_complete_inspected_checklist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.png"
            render = root / "render.png"
            Image.new("RGB", (40, 30), "white").save(source)
            Image.new("RGB", (40, 30), "white").save(render)
            output = root / "qa"

            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(SystemExit, "requires an explicit result"):
                    visual_qa.main(
                        [
                            "--source",
                            str(source),
                            "--render",
                            str(render),
                            "--out",
                            str(output),
                            "--review-status",
                            "pass",
                        ]
                    )
            self.assertFalse(output.exists())

            checks = [
                "global_canvas=pass",
                "structural_completeness=pass",
                "text_scale_and_wrapping=pass",
                "routing_and_layering=pass",
                "style_and_detail=pass",
            ]
            args = [
                "--source",
                str(source),
                "--render",
                str(render),
                "--out",
                str(output),
                "--review-status",
                "pass",
            ]
            for check in checks:
                args.extend(("--review-check", check))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(visual_qa.main(args), 0)
            summary = json.loads((output / "review_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["review"]["decision"], "pass")
            self.assertTrue(summary["review"]["checklist_complete"])
            self.assertEqual(
                set(summary["review"]["checklist"].values()),
                {"pass"},
            )

    def test_rerun_clears_stale_region_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.png"
            render = root / "render.png"
            Image.new("RGB", (40, 30), "white").save(source)
            Image.new("RGB", (40, 30), "white").save(render)
            output = root / "qa"

            def run_with_region(name: str):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        visual_qa.main(
                            [
                                "--source",
                                str(source),
                                "--render",
                                str(render),
                                "--out",
                                str(output),
                                "--region",
                                f"{name}=0,0,0.5,0.5",
                            ]
                        ),
                        0,
                    )

            run_with_region("first_area")
            self.assertTrue((output / "region_first_area.png").is_file())
            run_with_region("second_area")
            self.assertFalse((output / "region_first_area.png").exists())
            self.assertTrue((output / "region_second_area.png").is_file())
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(set(metrics["regions"]), {"second_area"})


class RendererStatusTests(unittest.TestCase):
    def test_renderer_status_reports_actionable_unavailable_state(self):
        with patch.object(runtime_env.shutil, "which", return_value=None):
            status = runtime_env.office_renderer_status()
        self.assertFalse(status["ready"])
        self.assertIsNone(status["executable"])
        self.assertIn("install", status["next"])
        self.assertIn("visual QA", status["next"])

    def test_current_renderer_status_has_expected_shape(self):
        status = runtime_env.office_renderer_status()
        self.assertIn("ready", status)
        self.assertIn("executable", status)
        self.assertIn("reason", status)
        self.assertIn("next", status)

    def test_unavailable_renderer_does_not_fail_unrelated_doctor_health(self):
        with patch.object(runtime_env.shutil, "which", return_value=None):
            with patch.object(runtime_env, "current_python_has_module", return_value=True):
                status = runtime_env.collect_status(check_api=False)
        self.assertTrue(status["ok"])
        self.assertFalse(status["office_renderer"]["ready"])


if __name__ == "__main__":
    unittest.main()
