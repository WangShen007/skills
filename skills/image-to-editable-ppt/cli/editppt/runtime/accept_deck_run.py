#!/usr/bin/env python3
"""Freeze the current candidate after reviewer-owned evidence passes."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from candidate_lifecycle import (
    CandidateAcceptanceError,
    current_candidate,
    load_review_summary,
    validate_candidate_manifest,
    validate_candidate_file,
    validate_review_summary,
)
from deck_run_state import (
    CANDIDATE_PAGE_STATUSES,
    load_deck,
    load_jobs,
    now_iso,
    rel_to_run,
    run_dir_from_target,
    save_deck,
    save_jobs,
    set_run_status,
    sha256_file,
    update_jobs_run_status,
    write_json,
)


def final_output_path(run_dir, deck):
    output = Path(deck.get("output", "final/deck_edited.pptx"))
    return output if output.is_absolute() else Path(run_dir) / output


def main():
    parser = argparse.ArgumentParser(description="Accept the current candidate after visual review.")
    parser.add_argument("run", help="Run directory or deck_manifest.json")
    parser.add_argument("--review-summary", required=True, metavar="FILE", help="Reviewer-owned JSON summary for the current candidate.")
    args = parser.parse_args()

    run_dir = run_dir_from_target(args.run)
    deck = load_deck(run_dir)
    jobs = load_jobs(run_dir)
    if any(page.get("status") == "accepted" for page in jobs.get("pages", [])):
        raise SystemExit("Accepted runs are immutable.")
    if not jobs.get("pages") or any(page.get("status") not in CANDIDATE_PAGE_STATUSES for page in jobs["pages"]):
        raise SystemExit("All pages must be in candidate_built or visual_review_passed before accept.")

    try:
        candidate = current_candidate(deck)
        candidate_path = validate_candidate_file(run_dir, candidate)
        validate_candidate_manifest(run_dir, deck, candidate)
        review_path = Path(args.review_summary).expanduser().resolve()
        summary = load_review_summary(review_path)
        validate_review_summary(summary, candidate)
    except (CandidateAcceptanceError, FileNotFoundError, KeyError, ValueError) as exc:
        raise SystemExit(f"Candidate acceptance failed: {exc}") from exc

    output = final_output_path(run_dir, deck)
    output.parent.mkdir(parents=True, exist_ok=True)
    if candidate_path.resolve() != output.resolve():
        shutil.copy2(candidate_path, output)
    if sha256_file(output) != candidate.get("pptx_sha256"):
        raise SystemExit("Candidate copy changed bytes; acceptance was not recorded.")

    accepted_at = now_iso()
    review_evidence = {
        "mode": "review-summary",
        "candidate_id": candidate.get("candidate_id"),
        "candidate_sha256": candidate.get("pptx_sha256"),
        "review_summary": rel_to_run(run_dir, review_path) if review_path.is_relative_to(run_dir) else str(review_path),
        "review_summary_sha256": sha256_file(review_path),
        "accepted_at": accepted_at,
    }
    for page in jobs.get("pages", []):
        page["status"] = "visual_review_passed"
        page["acceptance"] = review_evidence
    update_jobs_run_status(jobs)
    save_jobs(run_dir, jobs)
    set_run_status(run_dir, "visual_review_passed", "review evidence passed for current candidate")

    accepted_candidate = dict(candidate)
    accepted_candidate["status"] = "accepted"
    accepted_candidate["accepted_at"] = accepted_at
    accepted_candidate["acceptance"] = review_evidence
    for entry in deck.get("candidates", []):
        if entry.get("candidate_id") == accepted_candidate.get("candidate_id"):
            entry.update(accepted_candidate)
    deck["current_candidate"] = accepted_candidate
    deck["accepted_candidate"] = accepted_candidate
    deck["acceptance"] = review_evidence

    for page in jobs.get("pages", []):
        page["status"] = "accepted"
        page["accepted"] = True
        page["accepted_at"] = accepted_at
        page["candidate_id"] = candidate.get("candidate_id")
        page["candidate_sha256"] = candidate.get("pptx_sha256")
        page["acceptance"] = review_evidence
    jobs["current_candidate"] = accepted_candidate
    update_jobs_run_status(jobs)
    save_deck(run_dir, deck)
    save_jobs(run_dir, jobs)
    set_run_status(run_dir, "complete", "current candidate accepted")

    summary_payload = {
        "schema_version": 2,
        "run_id": deck.get("run_id"),
        "status": "complete",
        "candidate": accepted_candidate,
        "page_count": len(jobs.get("pages", [])),
        "output": str(output),
        "review_summary": str(review_path),
        "review_summary_sha256": review_evidence["review_summary_sha256"],
        "completed_at": accepted_at,
    }
    write_json(output.parent / "run_summary.json", summary_payload)
    print(json.dumps(summary_payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
