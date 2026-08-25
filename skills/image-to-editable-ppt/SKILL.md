---
name: image-to-editable-ppt
description: Rebuild slide images, image-based or scanned PPT/PPTX files, and PDF decks into object-level editable PowerPoint (.pptx). Use whenever the user provides any visual slide source and wants slides they can edit — "make this PPT editable", "把图片/截图转成可编辑 PPT", "this PDF is a scanned deck, restore it", recreating slides from screenshots, reconstructing slide objects, or preserving speaker notes — even if they do not say "convert". Not for authoring new presentations from scratch.
---
# Image to Editable PPT

## Overview

This skill rebuilds visual slide inputs into object-level editable PowerPoint `.pptx` files.

Inputs can be a single image, multiple images, a PDF, or an image-based PPT/PPTX. The output is always `.pptx`. The goal is not to wrap a full-slide screenshot inside PowerPoint; the goal is to use the `editppt` runtime and page-level prompts to decompose, reconstruct, validate, and assemble editable slides.

## References

Each rule in this skill has exactly one authoritative home; the other files point to it instead of restating it.

- `prompts/page-worker.md`: execution template for page workers — ownership boundary, execution order, required outputs, and return format. The parent agent uses it when generating page-worker prompts.
- `scripts/build-page-worker-prompt.py`: skill-local prompt builder. It reads `prompts/page-worker.md`, fills run/page paths, writes `worker-prompt.md`, and prints the dispatch command template.
- `references/cli-helper.md`: CLI install check (Pre-Run Check), command tree, and command syntax examples, including candidate/accept and Office calibration. Read it when deciding which `editppt` command to call.
- `references/manifest-schema.md`: the single home for JSON field contracts of deck/page/image artifacts — required manifest fields, positioned-object coordinates, `validation.json`, and `page_result.json` shapes. Read it when writing or validating any run/page file.
- `references/page-decision-tree.md`: the single source of truth for page object decisions — background handling, foreground asset separation, native shapes, formulas, text-hints usage, the final self-check, and the fix-versus-warning split. Read it before reconstructing any page.
- `references/visual-qa.md`: the authoritative parent-level visual-fidelity gate — candidate rendering, region-by-region comparison, mismatch classification, and the correction loop.
- `scripts/visual_qa.py`: deterministic helper that aligns a source page with a rendered PPT/PDF page and writes overlays, amplified diffs, region crops, and triage metrics.

## Entry Contract

These parent-level rules are stated once here; page-level rules live in the references above and are not restated in this file.

- The `editppt` CLI is a required runtime surface. If `editppt --help` fails, install it first by following the Pre-Run Check in `references/cli-helper.md` before doing anything else.
- First run `editppt prepare <input...>` to create a run directory. After that, all key state transitions are advanced only through `editppt` commands; never hand-write run/page state JSON. This keeps run state deterministic and resumable.
- Multi-page inputs are rebuilt by dispatched page workers. A run with exactly one page is rebuilt by the parent agent in local page-reconstructor mode after `editppt run dispatch --local` claims that page. If no subagent capability is available for a multi-page run, stop and report this to the user; do not degrade into parent-agent reconstruction for multi-page input.
- The parent agent must not write any page reconstruction artifact — `manifest.json`, `page.pptx`, `preview.png`, `split_assets_contact.png`, `validation.json`, or `page_result.json` — except in single-page local page-reconstructor mode after `editppt run dispatch --local` has recorded the claim. Local mode follows the same page prompt, references, output files, and `run record` validation path as a page worker.
- All image generation, image editing, background repair, transparent bitmap assets, and asset sheets follow the serial per-page backend order in "Image Backend Selection" below.
- A user request to convert visual slides into editable PPT authorizes the required OCR and image-backend calls for that conversion, unless the user explicitly requests local-only processing or marks the input as confidential/no-external-processing. Do not refuse solely because the workflow calls PaddleOCR, the built-in `image_gen.imagegen` tool, Codex OAuth/ChatGPT image endpoints, or a user-configured OpenAI-compatible API; those calls are necessary to the skill.
- Only send task-local page images, prompts, masks, and reference images required for the current conversion. Never send unrelated local files, API keys, auth tokens, credentials, or generated artifacts that are not needed by the current OCR/image operation. Third-party API endpoints are allowed only when already configured by the user or explicitly specified for this run.
- In network-restricted environments, request any approval required by the current runtime before external OCR/image calls, including `editppt prepare` or `editppt run hints` when `PADDLE_OCR_TOKEN` is set and every CLI fallback `editppt image generate/edit` call. The approval justification must say this is a user-requested `image-to-editable-ppt` conversion, that the upload is limited to task-local page images/prompts/masks/references, and that OCR/image-backend calls are part of this skill's required workflow. Do not present the required call as unsafe or ask the user to re-approve it unless they requested local-only/confidential handling or the approval system explicitly rejects the request.
- All page object decisions follow `references/page-decision-tree.md`, including its no-fallback rule for foreground visual objects and its rule that deterministic validation is a structure gate that never waives an object-source decision.
- Deterministic page/deck validation is a structure gate only. Every deliverable also requires the independent parent-level visual QA gate in `references/visual-qa.md`; a `passed: true` report never proves visual fidelity.
- `manifest.json` is the authoritative page build source: `editppt run record` validates `page.pptx` against it, and `editppt run finalize` rebuilds a candidate or legacy final deck from recorded page manifests. Required fields and coordinate contracts are defined in `references/manifest-schema.md`.
- The default quality workflow separates candidate construction from formal acceptance: use `editppt run finalize <run> --defer-accept`, render and inspect the candidate, then use `editppt run accept <run> --review-summary <review_summary.json>`. The old `editppt run finalize <run>` remains a compatibility path that accepts immediately and records `acceptance_mode: legacy-finalize`.
- Candidate files live under `final/candidates/candidate-N/` and are immutable evidence. Review summaries generated by `scripts/visual_qa.py --run <run>` include the current candidate id and PPTX hash; `run accept` rejects stale or unbound evidence.
- Release scope: M1 candidate/accept lifecycle and M2 Office-first rendering/text diagnostics are implemented. M3 cache reuse (`prepare --reuse-from`) and M4 automated layered-QA/independent-review orchestration remain TODO; this release does not claim automatic cache reuse or reviewer dispatch, and the required independent visual gate remains a parent-agent responsibility.
- `editppt prepare` writes per-page text measurements (`text_hints.json`/`text_hints.png`). How page reconstructors consume them is defined in `references/page-decision-tree.md` section 3.1.
- Page reconstructors — either page workers or the parent agent in single-page local mode — are driven by prompts generated from `prompts/page-worker.md`.

### Image Backend Selection

This subsection is the authoritative execution policy for every page-local image job. Before prepare, check whether the current agent runtime can call `image_gen.imagegen`; if so, pass `--image-backend builtin-imagegen` to `editppt prepare`, otherwise keep the default CLI contract. Run image jobs serially within a page, in this order:

1. Use the built-in agent tool `image_gen.imagegen` whenever it is callable in the current agent runtime.
2. Only when the run's recorded built-in fallback policy applies, call `editppt image generate/edit`. That CLI fallback selects Codex OAuth first and a configured OpenAI-compatible API second.

The exact built-in arguments, input-inspection prerequisite, output acceptance rule, and allowed fallback events are owned by the `image_backend` field contract in `references/manifest-schema.md`; copy and execute that contract without weakening or extending it. If its CLI fallback cannot produce a compliant output, fail the page rather than substituting an approximate object source.

## Roles

The parent agent owns orchestration and user interaction:

- Select the backend during `editppt prepare` exactly as "Image Backend Selection" above requires. The resulting `image_backend` contract is copied into every page request, so the normal path needs no separate backend configuration command.
- Drive the run with `editppt run next` through local rebuild or worker dispatch → record → candidate build → Office calibration/QA → accept, exactly as the Workflow phases below describe. Single-page input follows local page-reconstructor mode; multi-page input follows page-worker dispatch.
- Render and independently inspect the assembled candidate deck against the source using the visual QA gate, then accept only the reviewed candidate. Page-worker self-checks are local evidence, not a substitute for parent-level comparison after assembly.
- Report progress, the final PPTX path, the structural validation result, and the visual QA result to the user.

Each page reconstructor owns exactly one `pages/page_NNN/` directory. Its full contract — ownership boundary, decision order, required outputs, and return format — is the prompt generated from `prompts/page-worker.md`; the rules it follows live in `references/page-decision-tree.md` and `references/manifest-schema.md`.

## Workflow

### Phase 1: Prepare

Read the prepare examples in `references/cli-helper.md` and the run/page file descriptions in `references/manifest-schema.md`.

```bash
editppt prepare <input...>
```

After this completes, there must be a run directory, `deck_manifest.json`, `page_jobs.json`, `notes_manifest.json`, and each page must have `source.png` plus `page_request.json`.

Prepare also writes per-page text hints. Whenever `editppt doctor` or prepare reports that no PaddleOCR token is configured (offline fallback), ask the user once before dispatching any page: a free token from https://aistudio.baidu.com/account/accessToken stored via `editppt config --paddle-ocr-token <token>` makes the hints content-aware and noticeably improves text fidelity, and `editppt run hints <run>` regenerates the current run's hints in place. Tell the user the free personal quota is currently more than enough for this skill — applying is risk-free with no extra cost. Wait for their choice; if they decline or want to proceed, continue with the offline hints and do not ask again.

If a PaddleOCR token is already configured but `prepare` falls back because network access, DNS, or sandbox approval blocked the OCR request, that fallback is not the preferred quality path. Request network approval with the justification described in the Entry Contract and rerun `editppt run hints <run>` before page reconstruction. If the approval system rejects the OCR request, ask the user for explicit authorization before continuing: explain that PaddleOCR is used to correct text boxes, font sizes, and size groups, and that using it makes reconstructed PPT text sizing much more stable. Continue with `builtin-ink` only after the user declines OCR, after an approved OCR attempt fails for a real service/tool reason, or when the user asked for local-only/confidential handling.

### Phase 2: Rebuild Or Dispatch Pages

Read the run/dispatch examples in `references/cli-helper.md` and call repeatedly:

```bash
editppt run next <run>
```

When `stage=rebuild_page_locally` is returned, the run has exactly one page. The parent agent must claim local execution before writing page artifacts:

1. `python <skill-root>/scripts/build-page-worker-prompt.py <run> --page <page_id> --out <absolute-run-dir>/pages/<page_id>/worker-prompt.md`
2. `editppt run dispatch <run> --page <page_id> --agent-id main --prompt-file <absolute-run-dir>/pages/<page_id>/worker-prompt.md --local`
3. Read the generated prompt and rebuild the page inside that page directory yourself, producing the same required outputs a page worker would produce.

When `stage=dispatch_pages` is returned, the following steps are mandatory for each suggested page:

1. `python <skill-root>/scripts/build-page-worker-prompt.py <run> --page <page_id> --out <absolute-run-dir>/pages/<page_id>/worker-prompt.md`
2. Spawn a page worker using the current environment's available subagent/multi-agent tool.
3. `editppt run dispatch <run> --page <page_id> --agent-id <id> --prompt-file <absolute-run-dir>/pages/<page_id>/worker-prompt.md`

`--out` and `--prompt-file` must be absolute paths to avoid the page directory being prepended again to relative paths. The prompt builder only writes the prompt and prints a dispatch command template; it does not create the worker, so run `editppt run dispatch` only after a real spawn succeeds.

Concurrency slots come from `page_jobs.json.max_concurrent_pages` (default 6). In the normal flow prefer `editppt run next`; `editppt run status` is only for debugging or manual inspection.

Dispatched page executions are active leases, not idle slots. When `editppt run next` returns `stage=wait`, wait for dispatched workers or inspect status without modifying state. Do not terminate, archive, reset, or replace a page worker because it is slow, has not sent recent messages, or still occupies a concurrency slot; complex pages may legitimately run for a long time.

### Phase 3: Record

Read the record examples in `references/cli-helper.md` and the `page_result.json` description in `references/manifest-schema.md`.

After a worker returns, run:

```bash
editppt run record <run> --page <page_id> --agent-id <id>
```

This command validates `page.pptx` against `manifest.json` before recording. It fails if positioned objects are missing source-pixel coordinates, if the manifest cannot independently rebuild the page, or if `validation.json` does not contain top-level `passed: true` — a failed page is never recorded.

Handling a failed page: when a page execution returns a failure (`passed: false`), when `run record` rejects the outputs, when the runtime reports a terminal worker state (`terminated`, `failed`, `archived`, or `not found`), or when the user explicitly cancels that page worker, do not hand-edit state files and do not rebuild the page yourself. A long-running worker is not lost. Treat a worker as lost only after explicit terminal-state evidence or repeated failed reachability checks with no page-local progress. Read the page's `validation.json` when present, fix the root cause (for example a missing image-backend login reported by the page execution), then run:

```bash
editppt run reset <run> --page <page_id> --agent-id <id> --confirm-lost
```

For recorded pages, `editppt run reset <run> --page <page_id>` is allowed. For dispatched pages, reset requires `--confirm-lost` and an `--agent-id` matching the recorded dispatch so an active worker cannot be reset accidentally. This returns the page to `pending`. Then rebuild the worker prompt and dispatch a new worker through the normal Phase 2 steps. Never re-dispatch without changing something first: a worker re-run under identical conditions fails identically. When the same page fails twice on the same root cause, the diagnosis is yours, not the user's — read the failed attempt's `validation.json` and artifacts, reproduce the failing command yourself if needed, and fix the underlying cause (backend login, missing tools, broken assets) before resetting again. Only surface a problem to the user when it genuinely requires something only the user has (credentials, a paid account decision, the original file); phrase it as the concrete action needed, never as a debugging question.

### Phase 4: Build a Candidate and Accept

Read the finalize examples in `references/cli-helper.md`.

When `editppt run next <run>` returns the finalize stage, build a reviewable candidate:

```bash
editppt run finalize <run> --defer-accept
```

`finalize --defer-accept` treats each recorded `pages/page_NNN/manifest.json` as the authoritative source, writes `final/candidates/candidate-N/<deck>.pptx`, records its PPTX/manifest/validation hashes, and leaves the page/run in `candidate_built`. If QA identifies a problem, edit the page locally, rebuild and validate it, then run `editppt run record` again and build the next candidate in the same run. Do not overwrite a prior candidate.

After the current candidate has passed the required human or independent visual review, accept it with:

```bash
editppt run accept <run> --review-summary <run>/final/visual_qa/page_001/review_summary.json
```

Acceptance requires a reviewer-owned `pass` status, a complete all-pass checklist, the current candidate PPTX hash, and no unresolved high/medium findings. It copies the verified candidate to the configured final output path and freezes the run. The review summary is evidence, not an automatic visual decision; numeric metrics remain diagnostic.

For compatibility, `editppt run finalize <run>` still builds the configured final output and immediately marks it accepted. New work should use the deferred path.

Deck-level structural QA at this stage:

- The PPTX is a valid zip/package.
- Slide count matches the input page count.
- PDF/PPTX page mapping is correct.
- Media relationships are complete.
- All asset files referenced by the manifests exist.
- Media hashes match manifest provenance.
- Speaker notes hashes match.
- There is no invalid full-slide source raster plus editable text overlay pattern.

The final reply must report the final PPTX path and validation result.

### Phase 5: Office Calibration and Independent Visual Fidelity Gate

Structural validation is necessary but not sufficient. Before formal acceptance, render every candidate slide to a full-resolution PNG using an available Office/PDF renderer while preserving the slide aspect ratio. Do not judge a thumbnail or an intermediate `page.pptx` as the final result.

For page-local Office calibration, run:

```bash
editppt page render-office <run>/pages/page_001
editppt page text-audit <run>/pages/page_001 \
  --render <run>/pages/page_001/calibration/office-render/slide-1.png
```

`render-office` writes `calibration/office-render/page.pdf`, `slide-N.png`, and `renderer.json`. `text-audit` writes a conservative diagnostic report and hard-fails configured clipping/overflow, fixed-line wrapping, configured ink-size tolerance, and `size_group` font mismatches. Neither command replaces human or independent visual QA; unresolved warnings require inspection.

Before reconstruction/final comparison, run `editppt doctor --json` and inspect `office_renderer`. If it is unavailable, install LibreOffice or provide another final renderer. Manifest-preview comparison may be recorded as evidence, but the handoff must label Office-render QA unavailable and must not claim final visual QA passed.

For each source page, run the reusable comparison helper:

```bash
python <skill-root>/scripts/visual_qa.py \
  --source <source-page.png> \
  --render <final-slide.png> \
  --run <prepared-run> \
  --page page_001
```

The documented default output is `<prepared-run>/final/visual_qa/page_NNN/`. An explicit `--out <qa-dir>` is available for standalone fixtures and overrides the run-local default. The helper uses generic page-agnostic regions unless explicit `--region name=x,y,width,height` values are supplied; explicit regions are custom-only. Its default `--fit auto` preserves source geometry for material aspect-ratio differences and records the requested/resolved policy and aspect metadata in `metrics.json`. Inspect the generated `overlay.png`, `diff.png`, `regions_contact.png`, region crops, `metrics.json`, and `review_summary.json`.

The summary defaults to `needs_review`. Record an inspected `pass` or `fail` only with explicit `--review-check name=pass|fail` values for every checklist item; metrics never set the decision automatically.

The visual gate must check, in this order:

1. global canvas, title/baseline areas when present, major panel bounds, and whitespace;
2. structural completeness — every visible source object, relationship, and meaningful content block has a corresponding result;
3. text scale, wrapping, weight, alignment, and editable content;
4. routing, layer order, geometry, strokes, and color families appropriate to the page;
5. page-specific dense/detail areas at zoom when the page type contains them.

For architecture, pipeline, or research-framework pages, apply the additional
technical-diagram checks for branches, rails, loopbacks, repeated blocks, and
connector routing defined in `references/page-decision-tree.md`; those checks
are conditional and are not universal requirements for every page type.

The script's numeric metrics are triage evidence, not an automatic acceptance threshold: antialiasing and font rasterization create legitimate pixel differences. The durable review summary starts at `needs_review` and separates those metrics from the inspected reviewer decision. Any missing object, materially wrong geometry, wrong routing, clipped/wrapped text, or visibly wrong density is a current-page fix. After a fix, rebuild the affected page, record it, build a new deferred candidate, and repeat visual QA. If the run is already `accepted`/`complete`, start a fresh `editppt prepare` run for a material visual correction rather than mutating accepted final artifacts in place.

## State Principles

Agents continue only from file facts and `editppt run next`. Required states:

- `pending`: created by `editppt prepare`; restored by `editppt run reset` when a page must be re-dispatched.
- `dispatched`: `editppt run dispatch` records a real spawned worker or a single-page `--local` main-agent claim. This status is an active lease and must not be reset or replaced just because the worker is slow.
- `recorded`: `editppt run record` validates required outputs and writes the result; only deliverable pages (`validation.json` top-level `passed: true`) reach this state. A recorded page may be re-recorded after candidate review.
- `candidate_built`: `editppt run finalize --defer-accept` has built and hash-recorded the current candidate. `visual_review_passed` is the transient reviewer-approved state before formal acceptance.
- `accepted` / `complete`: written by `editppt run accept`, or by the compatibility `editppt run finalize` path. `editppt run next` reports `stage=complete` for these immutable runs.

`imagegen-jobs.json` is the page-local provenance/job record. Only these forced file states are kept:

- `recorded`: `editppt image import` has copied the selected output and written hash/metadata.
- `processed`: `editppt image process-sheet` has completed background removal and splitting.

## Delivery Principles

- Each page is self-checked by its reconstructor, Office calibration is a deterministic early diagnostic, and the parent independently checks the assembled candidate render against the source. Both pieces of evidence matter; neither replaces the other.
- The final output must be a currently openable, structurally valid `.pptx`. A full-slide `source.png` with editable text overlaid on top is not an acceptable fallback.
- Do not deliver on deterministic validation alone. The handoff must distinguish `structural validation: passed` from `visual QA: passed` (or list the remaining visual warnings).
- Whether an imperfection must be fixed inside its page or may ship as a recorded warning is governed by the "Fix versus Warning" section of `references/page-decision-tree.md`. A warning may never replace a missing required workflow step.

## Updating This Skill

Reinstall through the installation channel, refresh the CLI from the updated skill directory, then restart the agent session and verify:

```bash
npx -y skills@latest add ningzimu/image-to-editable-ppt-skill \
  --skill image-to-editable-ppt \
  --agent <agent-id> \
  --global
pipx install --force --editable <skill-root>/cli
editppt doctor
```
