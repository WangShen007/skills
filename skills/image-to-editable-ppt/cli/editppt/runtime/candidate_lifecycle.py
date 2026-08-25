"""Candidate build and acceptance contracts for editppt runs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from deck_run_state import (
    read_json,
    rel_to_run,
    resolve_inside,
    sha256_file,
    sha256_text,
)


class CandidateAcceptanceError(ValueError):
    """Raised when review evidence cannot authorize the current candidate."""


REQUIRED_REVIEW_CHECKS = frozenset(
    {
        "global_canvas",
        "structural_completeness",
        "text_scale_and_wrapping",
        "routing_and_layering",
        "style_and_detail",
    }
)


def next_candidate_id(run_dir, deck) -> str:
    """Return a monotonic candidate id without inspecting unrelated files."""

    existing = deck.get("candidates") or []
    numbers = []
    for entry in existing:
        value = str(entry.get("candidate_id", "")) if isinstance(entry, Mapping) else ""
        if value.startswith("candidate-"):
            try:
                numbers.append(int(value.split("-", 1)[1]))
            except ValueError:
                continue
    candidate_root = Path(run_dir) / "final" / "candidates"
    if candidate_root.exists():
        for path in candidate_root.glob("candidate-*"):
            if path.is_dir():
                try:
                    numbers.append(int(path.name.split("-", 1)[1]))
                except ValueError:
                    continue
    return f"candidate-{max(numbers, default=0) + 1:03d}"


def manifest_digest(run_dir, deck) -> tuple[str, dict[str, dict[str, str]]]:
    """Hash the exact page manifests used by a candidate build."""

    run_dir = Path(run_dir).resolve()
    page_hashes: dict[str, dict[str, str]] = {}
    for page in deck.get("pages", []):
        page_id = str(page.get("page_id"))
        manifest_path = resolve_inside(run_dir, page["manifest"])
        page_hashes[page_id] = {
            "path": rel_to_run(run_dir, manifest_path),
            "sha256": sha256_file(manifest_path),
        }
    digest = sha256_text(json.dumps(page_hashes, ensure_ascii=False, sort_keys=True))
    return digest, page_hashes


def candidate_path(run_dir, candidate) -> Path:
    value = candidate.get("pptx")
    if not value:
        raise CandidateAcceptanceError("current candidate is missing its pptx path")
    return resolve_inside(run_dir, value)


def current_candidate(deck) -> Mapping[str, object]:
    candidate = deck.get("current_candidate")
    if not isinstance(candidate, Mapping):
        raise CandidateAcceptanceError("run has no current candidate; build one with `run finalize --defer-accept`")
    return candidate


def validate_candidate_file(run_dir, candidate) -> Path:
    path = candidate_path(run_dir, candidate)
    if not path.is_file():
        raise CandidateAcceptanceError(f"current candidate pptx is missing: {path}")
    actual_hash = sha256_file(path)
    expected_hash = candidate.get("pptx_sha256")
    if not expected_hash or actual_hash != expected_hash:
        raise CandidateAcceptanceError(
            "current candidate hash does not match its recorded evidence: "
            f"expected={expected_hash} actual={actual_hash}"
        )
    return path


def validate_candidate_manifest(run_dir, deck, candidate) -> None:
    """Reject acceptance when page manifests changed after candidate build."""

    expected_digest = candidate.get("manifest_sha256")
    expected_pages = candidate.get("page_manifests")
    if not expected_digest or not isinstance(expected_pages, Mapping):
        raise CandidateAcceptanceError("current candidate is missing page-manifest hash evidence")
    try:
        actual_digest, actual_pages = manifest_digest(run_dir, deck)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        raise CandidateAcceptanceError(
            f"could not verify current page-manifest hashes: {exc}"
        ) from exc
    if expected_digest != actual_digest or dict(expected_pages) != actual_pages:
        raise CandidateAcceptanceError(
            "current page manifests no longer match the candidate; build a new candidate"
        )


def _candidate_evidence(summary: Mapping[str, object]) -> Mapping[str, object]:
    evidence = summary.get("candidate")
    if isinstance(evidence, Mapping):
        return evidence
    # A top-level field is accepted as a small compatibility convenience for
    # independently-authored summaries, but the preferred contract is the
    # structured candidate object emitted by visual_qa.py.
    candidate_hash = summary.get("candidate_sha256")
    if candidate_hash:
        return {"pptx_sha256": candidate_hash}
    return {}


def _unresolved_findings(value):
    if isinstance(value, Mapping):
        severity = str(value.get("severity", "")).strip().lower()
        if severity in {"high", "medium"}:
            state = str(
                value.get("resolution")
                or value.get("status")
                or value.get("state")
                or "unresolved"
            ).strip().lower()
            if state not in {"resolved", "closed", "fixed", "accepted"}:
                yield value
        for child in value.values():
            yield from _unresolved_findings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _unresolved_findings(child)


def validate_review_summary(summary, candidate) -> None:
    """Require a complete, pass review that names the current candidate hash."""

    if not isinstance(summary, Mapping):
        raise CandidateAcceptanceError("review summary must be a JSON object")
    evidence = _candidate_evidence(summary)
    expected_hash = candidate.get("pptx_sha256")
    if evidence.get("candidate_id") and evidence.get("candidate_id") != candidate.get("candidate_id"):
        raise CandidateAcceptanceError("review summary points to a different candidate id")
    if evidence.get("pptx_sha256") != expected_hash:
        raise CandidateAcceptanceError(
            "review summary must name the current candidate pptx_sha256"
        )
    if "hash_verified" in evidence and evidence.get("hash_verified") is not True:
        raise CandidateAcceptanceError("review summary candidate hash verification failed")
    if evidence.get("manifest_sha256") and evidence.get("manifest_sha256") != candidate.get("manifest_sha256"):
        raise CandidateAcceptanceError(
            "review summary manifest_sha256 does not match the current candidate"
        )

    review = summary.get("review")
    if not isinstance(review, Mapping):
        review = {}
    status = review.get("status") or summary.get("review_status")
    decision = review.get("decision")
    if status != "pass" or decision != "pass":
        raise CandidateAcceptanceError("review summary must have review status and decision `pass`")
    if review.get("checklist_complete") is not True:
        raise CandidateAcceptanceError("review summary checklist is incomplete")
    checklist = review.get("checklist")
    if not isinstance(checklist, Mapping) or not checklist:
        raise CandidateAcceptanceError("review summary must include a complete checklist")
    missing_checks = REQUIRED_REVIEW_CHECKS.difference(checklist)
    if missing_checks:
        missing = ", ".join(sorted(missing_checks))
        raise CandidateAcceptanceError(f"review summary checklist is missing required item(s): {missing}")
    if any(value != "pass" for value in checklist.values()):
        raise CandidateAcceptanceError("review summary checklist contains a non-pass item")

    unresolved = list(
        _unresolved_findings(summary.get("findings", []))
    )
    if isinstance(review.get("findings"), (Mapping, list, tuple)):
        unresolved.extend(_unresolved_findings(review["findings"]))
    if unresolved:
        raise CandidateAcceptanceError(
            f"review summary has {len(unresolved)} unresolved high/medium finding(s)"
        )


def load_review_summary(path) -> dict:
    summary_path = Path(path).expanduser().resolve()
    if not summary_path.is_file():
        raise CandidateAcceptanceError(f"review summary not found: {summary_path}")
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CandidateAcceptanceError(f"review summary is not valid JSON: {summary_path}") from exc
    if not isinstance(summary, dict):
        raise CandidateAcceptanceError("review summary must be a JSON object")
    return summary
