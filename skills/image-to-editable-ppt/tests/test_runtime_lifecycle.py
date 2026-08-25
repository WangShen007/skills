from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = SKILL_ROOT / "cli" / "editppt" / "runtime"
sys.path.insert(0, str(RUNTIME_ROOT))

from candidate_lifecycle import (  # noqa: E402
    CandidateAcceptanceError,
    REQUIRED_REVIEW_CHECKS,
    manifest_digest,
    validate_candidate_manifest,
    validate_review_summary,
)
from deck_run_state import (  # noqa: E402
    load_deck,
    save_jobs,
    update_jobs_run_status,
    write_json,
)
from main import cmd_next  # noqa: E402


def full_checklist():
    return {key: "pass" for key in REQUIRED_REVIEW_CHECKS}


class RuntimeLifecycleTests(unittest.TestCase):
    def test_save_jobs_synchronizes_deck_page_projection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            deck = {
                "run_id": "fixture",
                "pages": [{"page_id": "page_001", "status": "pending", "result": None}],
            }
            jobs = {
                "run_id": "fixture",
                "run_status": "pages_recorded",
                "pages": [
                    {
                        "page_id": "page_001",
                        "status": "recorded",
                        "agent_status": "recorded",
                        "result": {"validation_passed": True},
                        "accepted": False,
                        "candidate_id": None,
                        "candidate_sha256": None,
                    }
                ],
            }
            write_json(run_dir / "deck_manifest.json", deck)
            update_jobs_run_status(jobs)
            save_jobs(run_dir, jobs)

            projected = load_deck(run_dir)["pages"][0]
            self.assertEqual(projected["status"], "recorded")
            self.assertEqual(projected["agent_status"], "recorded")
            self.assertEqual(projected["result"], {"validation_passed": True})
            self.assertEqual(load_deck(run_dir)["run_status"], "pages_recorded")

    def test_acceptance_evidence_must_name_current_candidate_hash(self):
        candidate = {
            "candidate_id": "candidate-001",
            "pptx_sha256": "current-pptx-hash",
            "manifest_sha256": "current-manifest-hash",
        }
        summary = {
            "candidate": {
                "candidate_id": "candidate-001",
                "pptx_sha256": "current-pptx-hash",
                "manifest_sha256": "current-manifest-hash",
            },
            "review_status": "pass",
            "review": {
                "status": "pass",
                "decision": "pass",
                "checklist_complete": True,
                "checklist": full_checklist(),
            },
        }
        validate_review_summary(summary, candidate)

        stale = json.loads(json.dumps(summary))
        stale["candidate"]["pptx_sha256"] = "old-pptx-hash"
        with self.assertRaisesRegex(CandidateAcceptanceError, "current candidate pptx_sha256"):
            validate_review_summary(stale, candidate)

    def test_acceptance_rejects_unresolved_medium_finding(self):
        candidate = {"candidate_id": "candidate-001", "pptx_sha256": "hash"}
        summary = {
            "candidate": {"candidate_id": "candidate-001", "pptx_sha256": "hash"},
            "review": {
                "status": "pass",
                "decision": "pass",
                "checklist_complete": True,
                "checklist": full_checklist(),
            },
            "findings": [{"severity": "medium", "status": "open"}],
        }
        with self.assertRaisesRegex(CandidateAcceptanceError, "unresolved high/medium"):
            validate_review_summary(summary, candidate)

    def test_acceptance_rejects_incomplete_visual_checklist(self):
        candidate = {"candidate_id": "candidate-001", "pptx_sha256": "hash"}
        summary = {
            "candidate": {"candidate_id": "candidate-001", "pptx_sha256": "hash"},
            "review": {
                "status": "pass",
                "decision": "pass",
                "checklist_complete": True,
                "checklist": {"global_canvas": "pass"},
            },
        }
        with self.assertRaisesRegex(CandidateAcceptanceError, "missing required item"):
            validate_review_summary(summary, candidate)

    def test_acceptance_rejects_unresolved_finding_nested_in_review(self):
        candidate = {"candidate_id": "candidate-001", "pptx_sha256": "hash"}
        summary = {
            "candidate": {"candidate_id": "candidate-001", "pptx_sha256": "hash"},
            "review": {
                "status": "pass",
                "decision": "pass",
                "checklist_complete": True,
                "checklist": full_checklist(),
                "findings": [{"severity": "high", "status": "open"}],
            },
        }
        with self.assertRaisesRegex(CandidateAcceptanceError, "unresolved high/medium"):
            validate_review_summary(summary, candidate)

    def test_candidate_rejects_changed_page_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            manifest_path = run_dir / "pages" / "page_001" / "manifest.json"
            write_json(manifest_path, {"version": 1})
            deck = {
                "pages": [{"page_id": "page_001", "manifest": "pages/page_001/manifest.json"}],
            }
            digest, page_hashes = manifest_digest(run_dir, deck)
            candidate = {
                "candidate_id": "candidate-001",
                "manifest_sha256": digest,
                "page_manifests": page_hashes,
            }
            validate_candidate_manifest(run_dir, deck, candidate)
            write_json(manifest_path, {"version": 2})
            with self.assertRaisesRegex(CandidateAcceptanceError, "no longer match"):
                validate_candidate_manifest(run_dir, deck, candidate)

    def test_run_next_reports_complete_for_accepted_legacy_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            page = {
                "page_id": "page_001",
                "status": "accepted",
                "accepted": True,
            }
            write_json(
                run_dir / "deck_manifest.json",
                {"image_backend": {"backend_id": "test"}, "pages": [dict(page)]},
            )
            write_json(run_dir / "page_jobs.json", {"pages": [page]})
            write_json(run_dir / "run_state.json", {"status": "complete", "history": []})
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    cmd_next(argparse.Namespace(run=str(run_dir), json=True)),
                    0,
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["stage"], "complete")
            self.assertIsNone(payload["next_command"])


if __name__ == "__main__":
    unittest.main()
