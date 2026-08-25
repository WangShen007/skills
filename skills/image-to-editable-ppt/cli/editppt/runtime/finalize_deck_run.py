#!/usr/bin/env python3
"""Build a final deck or an immutable run-local candidate deck."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from candidate_lifecycle import manifest_digest, next_candidate_id
from deck_run_state import (
    RECORDABLE_PAGE_STATUSES,
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


SCRIPT_DIR = Path(__file__).resolve().parent


def run(command):
    print("+ " + " ".join(str(part) for part in command), flush=True)
    subprocess.run([str(part) for part in command], check=True)


def final_output_path(run_dir, deck):
    output = Path(deck.get("output", "final/deck_edited.pptx"))
    if output.is_absolute():
        return output
    return run_dir / output


def assert_pages_ready(jobs):
    problems = []
    for page in jobs.get("pages", []):
        status = page.get("status")
        if status not in RECORDABLE_PAGE_STATUSES | {"accepted"}:
            problems.append(f"{page['page_id']} status={status}")
            continue
        result = page.get("result") or {}
        if result.get("validation_passed") is not True:
            problems.append(f"{page['page_id']} validation_passed={result.get('validation_passed')}")
    if problems:
        raise SystemExit("Pages are not ready for finalize:\n" + "\n".join(problems))


def assert_run_is_mutable(jobs):
    if any(page.get("status") == "accepted" for page in jobs.get("pages", [])):
        raise SystemExit("Accepted runs are immutable; prepare a new run for a material correction.")


def build_and_validate(run_dir, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            sys.executable,
            SCRIPT_DIR / "build_pptx_from_manifest.py",
            "--deck-manifest",
            run_dir / "deck_manifest.json",
            "--out",
            output,
        ]
    )
    validation = output.parent / "validation.json"
    run(
        [
            sys.executable,
            SCRIPT_DIR / "validate_pptx.py",
            output,
            "--deck-manifest",
            run_dir / "deck_manifest.json",
            "--report",
            validation,
        ]
    )
    report = json.loads(validation.read_text(encoding="utf-8"))
    if report.get("passed") is not True:
        raise SystemExit(f"Deck validation did not pass: {validation}")
    return validation


def candidate_record(run_dir, deck, candidate_id, output, validation, *, status):
    manifest_sha256, page_manifests = manifest_digest(run_dir, deck)
    return {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "status": status,
        "created_at": now_iso(),
        "pptx": rel_to_run(run_dir, output),
        "pptx_sha256": sha256_file(output),
        "validation": rel_to_run(run_dir, validation),
        "validation_sha256": sha256_file(validation),
        "manifest_sha256": manifest_sha256,
        "page_manifests": page_manifests,
    }


def append_candidate(deck, candidate):
    candidates = list(deck.get("candidates") or [])
    candidates.append(candidate)
    deck["candidates"] = candidates
    deck["current_candidate"] = candidate


def write_candidate_summary(candidate, validation, *, status, output):
    summary = {
        "schema_version": 2,
        "run_id": candidate.get("run_id"),
        "status": status,
        "candidate": candidate,
        "output": str(output),
        "validation": str(validation),
        "created_at": candidate.get("created_at"),
    }
    summary_path = Path(output).parent / "run_summary.json"
    write_json(summary_path, summary)
    return summary_path


def build_candidate(run_dir, deck, jobs):
    candidate_id = next_candidate_id(run_dir, deck)
    candidate_dir = run_dir / "final" / "candidates" / candidate_id
    output = candidate_dir / Path(deck.get("output", "final/deck_edited.pptx")).name
    validation = build_and_validate(run_dir, output)
    candidate = candidate_record(run_dir, deck, candidate_id, output, validation, status="candidate_built")
    candidate["run_id"] = deck.get("run_id")
    append_candidate(deck, candidate)

    for page in jobs.get("pages", []):
        page["status"] = "candidate_built"
        page["candidate_id"] = candidate["candidate_id"]
        page["candidate_sha256"] = candidate["pptx_sha256"]
        page["acceptance"] = None
        page["accepted"] = False
    update_jobs_run_status(jobs)
    jobs["current_candidate"] = candidate
    save_deck(run_dir, deck)
    save_jobs(run_dir, jobs)
    set_run_status(run_dir, "candidate_built", f"built {candidate_id}")
    summary_path = write_candidate_summary(
        candidate,
        validation,
        status="candidate_built",
        output=output,
    )
    return candidate, validation, summary_path


def build_legacy_final(run_dir, deck, jobs):
    output = final_output_path(run_dir, deck)
    validation = build_and_validate(run_dir, output)
    candidate_id = next_candidate_id(run_dir, deck)
    candidate = candidate_record(run_dir, deck, candidate_id, output, validation, status="accepted")
    candidate["run_id"] = deck.get("run_id")
    candidate["acceptance_mode"] = "legacy-finalize"
    append_candidate(deck, candidate)
    deck["accepted_candidate"] = candidate

    for page in jobs.get("pages", []):
        page["status"] = "accepted"
        page["accepted"] = True
        page["accepted_at"] = now_iso()
        page["candidate_id"] = candidate["candidate_id"]
        page["candidate_sha256"] = candidate["pptx_sha256"]
        page["acceptance"] = {"mode": "legacy-finalize", "candidate_id": candidate["candidate_id"]}
    update_jobs_run_status(jobs)
    jobs["current_candidate"] = candidate
    save_deck(run_dir, deck)
    save_jobs(run_dir, jobs)
    set_run_status(run_dir, "complete", "legacy finalize accepted the built deck")
    summary = {
        "schema_version": 2,
        "run_id": deck.get("run_id"),
        "status": "complete",
        "candidate": candidate,
        "page_count": len(jobs.get("pages", [])),
        "output": str(output),
        "validation": str(validation),
        "completed_at": now_iso(),
        "acceptance_mode": "legacy-finalize",
    }
    write_json(output.parent / "run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Build and validate a candidate or final editable PPTX.")
    parser.add_argument("run", help="Run directory or deck_manifest.json")
    parser.add_argument(
        "--defer-accept",
        action="store_true",
        help="Build an immutable candidate under final/candidates without accepting it.",
    )
    args = parser.parse_args()

    run_dir = run_dir_from_target(args.run)
    deck = load_deck(run_dir)
    jobs = load_jobs(run_dir)
    assert_run_is_mutable(jobs)
    assert_pages_ready(jobs)

    if args.defer_accept:
        candidate, validation, summary_path = build_candidate(run_dir, deck, jobs)
        payload = {
            "schema_version": 2,
            "run_id": deck.get("run_id"),
            "status": "candidate_built",
            "candidate": candidate,
            "validation": str(validation),
            "summary": str(summary_path),
            "next": f"{Path(sys.argv[0]).name} run accept {run_dir} --review-summary <review_summary.json>",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    build_legacy_final(run_dir, deck, jobs)


if __name__ == "__main__":
    main()
