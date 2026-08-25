# CLI Helper

This is the `editppt` command manual: install check, command tree, and syntax examples. Workflow policy lives in `SKILL.md`; object decisions and text-hints usage live in `references/page-decision-tree.md`; file and field contracts live in `references/manifest-schema.md`.

Usage principles:

- If a deterministic action can be completed with `editppt`, call the CLI directly instead of rewriting it as a temporary Python script.
- When full CLI parameters are needed, read `editppt <command> --help` or `editppt image <command> --help` first.
- In network-restricted agents, `editppt prepare`/`editppt run hints` with a PaddleOCR token and CLI fallback `editppt image generate/edit` calls need network approval. The approval and user-interaction policy lives in `SKILL.md` Entry Contract and Phase 1.
- `editppt doctor --json` reports `office_renderer` separately from Python/configuration health. Check it before final visual QA; an unavailable renderer does not make unrelated CLI checks fail, but it also does not permit claiming Office-render visual QA passed.

## Command Tree

```text
editppt                         - top-level CLI for setup, run orchestration, image assets, and formulas
|-- setup                       - create or verify the user-level runtime home and config files
|-- doctor                      - check local runtime health, dependencies, backends, and Office renderer availability
|-- config                      - write user-level OpenAI-compatible image API fallback settings
|-- prepare                     - normalize image/PDF/PPTX inputs into a run directory and page jobs
|-- run                         - advance run state and coordinate page workers
|   |-- next                    - read current run state and return the next required action
|   |-- status                  - inspect run/page state for debugging or manual checks
|   |-- backend                 - override or inspect the run-level image backend contract
|   |-- dispatch                - record that a page worker was spawned or a single-page local rebuild was claimed
|   |-- record                  - validate required page outputs and record page result hashes
|   |-- reset                   - return a failed or stuck page to pending for re-dispatch
|   |-- hints                   - regenerate per-page text hints for a prepared run
|   |-- finalize                - build a candidate or legacy final PPTX from recorded page manifests
|   `-- accept                  - bind reviewer evidence to the current candidate and freeze the run
|-- page                        - page-local helpers
|   |-- hints                   - detect and measure text lines for one page directory
|   |-- build                   - build page.pptx and preview.png from manifest.json
|   |-- contact-sheet           - create the origin-versus-preview comparison image
|   |-- render-office           - render page.pptx through LibreOffice/soffice for calibration
|   |-- text-audit              - audit configured text boxes against an Office render
|   `-- validate                - validate page.pptx against manifest.json as run record will
|-- image                       - generate, edit, import, and process bitmap assets
|   |-- generate                - create a new image from a text prompt
|   |-- edit                    - edit a source image for clean bases or source-faithful asset sheets
|   |-- import                  - copy a selected image into the page dir and record provenance
|   `-- process-sheet           - split a chroma-key asset sheet into transparent assets
`-- formula                     - render formula assets from agent-transcribed LaTeX
    `-- render-latex            - render LaTeX into SVG/PNG/PDF plus a manifest fragment
```

## Common Help Entrypoints

```bash
editppt --help
editppt run --help
editppt page hints --help
editppt image --help
editppt image edit --help
editppt formula render-latex --help
```

`editppt image` is the CLI fallback layer. Within that layer it automatically chooses Codex OAuth first, then OpenAI-compatible API credentials from `~/.editppt/config.yaml` or environment variables if OAuth is unavailable. See `manifest-schema.md` for the run/page backend field contract. `editppt doctor` checks CLI backend readiness and reports the local Office renderer; it cannot discover whether an agent runtime exposes the built-in tool.

Public `editppt image generate/edit` parameters are intentionally narrow. Required request inputs are `--prompt` or `--prompt-file`, plus at least one `--image` for `edit`. CLI fallback calls should pass an explicit `--out`. Retained useful controls are `--model` (default `gpt-image-2`), `--size` (default `auto`), `--quality` (default `auto`), `--force`, `--dry-run`, `--timeout`, and edit-only `--mask`. The CLI does not pass any other image API options.

## Skill Script Commands

```bash
python <skill-root>/scripts/build-page-worker-prompt.py <run> --page page_001 --out <absolute-run-dir>/pages/page_001/worker-prompt.md
```

Purpose: generate a page-worker prompt from the skill-local `prompts/page-worker.md` template. This is a skill script, not an `editppt` CLI command, because it reads skill documentation and references.

The script writes the prompt file and prints JSON with `prompt_file`, `page_id`, and `dispatch_command_template`. It does not create a page worker or claim local execution and must run before `editppt run dispatch`.

## Pre-Run Check

The `editppt` CLI is a required runtime surface for this skill. First confirm that the CLI is available:

```bash
editppt --help
```

If the shell returns command not found, or if the skill was just updated, install the skill-local CLI in editable mode:

```bash
pipx install --force --editable <skill-root>/cli
```

If `pipx` itself is unavailable, fall back to one of:

```bash
uv tool install --force --editable <skill-root>/cli
python3 -m pip install --user -e <skill-root>/cli
```

`<skill-root>` is the `image-to-editable-ppt` directory that contains `SKILL.md`. On Windows, use the same directory's `cli` subdirectory path.

After the CLI is available, run local runtime checks:

```bash
editppt setup
editppt doctor --json
editppt config --api-key "<key>" --base-url "<openai-compatible-base-url>" --model "<image-model>"
```

`editppt doctor --json` includes an `office_renderer` record with `ready`,
`executable`, `reason`, and actionable `next` fields. When it is unavailable,
install LibreOffice/`soffice` or provide another final Office/PDF renderer.
Manifest-preview comparison may continue as explicitly labeled evidence, but
the workflow must not claim final Office-render visual QA passed.

Write `editppt config` only when API fallback is needed or when the user explicitly provides a third-party image API. Do not write API keys into the project directory, run directory, prompts, or manifests.

Optional but recommended on first use: configure a PaddleOCR-VL token. The offline detector only measures text geometry (where and how large); with a token the hints also carry recognized text content and cleaner block boundaries. Store it next to the other credentials:

```bash
editppt config --paddle-ocr-token "<token>"
```

`editppt doctor` reports the current text-hints backend; without a token everything still works through the built-in offline detector. When and how to ask the user about the token — including the application URL and the regenerate step — is defined in `SKILL.md` Phase 1.

## Run Commands

```bash
editppt prepare input.png
editppt prepare input.pdf
editppt prepare input.png --image-backend builtin-imagegen
```

Purpose: normalize a single image, multiple images, a PDF, or an image-based PPTX into a run directory and generate `deck_manifest.json`, `page_jobs.json`, `notes_manifest.json`, plus per-page `pages/page_NNN/source.png`, `page_request.json`, and text hints. `--image-backend` records the requested run/page contract; selection policy lives in `SKILL.md` subsection "Image Backend Selection".

When a PaddleOCR token is configured, `prepare` may submit the input pages to PaddleOCR for content-aware text hints. In a sandboxed or approval-gated environment, request network approval up front for this command instead of accepting a DNS/sandbox failure followed by lower-quality `builtin-ink` fallback; see `SKILL.md` Phase 1 for the approval-rejection policy.

```bash
editppt run next <run> --json
```

Purpose: read current run state and return the next stage. `stage=rebuild_page_locally` appears only when the run has exactly one pending page; the parent agent must build the page prompt, claim local execution with `run dispatch --local`, and rebuild the page itself using that prompt. `stage=dispatch_pages` lists `suggested_pages` that must each be dispatched to a page worker. `stage=wait` means wait for dispatched pages to complete; slow dispatched workers remain active and must not be reset or replaced because they occupy a slot. `stage=finalize` means proceed to candidate assembly. `stage=candidate_review` means inspect the current candidate and prepare a reviewer summary; `stage=candidate_rebuild` means a page was re-recorded and a new deferred candidate should be built. `stage=complete` means the run is accepted and immutable and has no next command. `stage=configure_backend` appears only when `deck_manifest.json.image_backend` is missing; follow the returned `next_command`.

Generate the page-worker prompt with the skill script before spawning a worker:

```bash
python <skill-root>/scripts/build-page-worker-prompt.py <run> --page page_001 --out <absolute-run-dir>/pages/page_001/worker-prompt.md
```

```bash
editppt run dispatch <run> --page page_001 --agent-id <worker-id> --prompt-file <absolute-run-dir>/pages/page_001/worker-prompt.md
```

For a single-page local rebuild, use:

```bash
editppt run dispatch <run> --page page_001 --agent-id main --prompt-file <absolute-run-dir>/pages/page_001/worker-prompt.md --local
```

Purpose: record that a page has been dispatched to a worker or claimed for single-page local reconstruction. For worker dispatch, first create the worker with the current environment's available subagent/multi-agent tool, then run this command. For local reconstruction, `--local` is allowed only when the run has exactly one page. `--prompt-file` uses the same absolute path as the prompt-builder `--out`. `--agent-id` is any stable identifier for the execution; the same id must be reused at `run record`.

```bash
editppt run record <run> --page page_001 --agent-id <worker-id>
```

Purpose: after the page reconstructor writes its required outputs (see `manifest-schema.md`), validate `page.pptx` against `manifest.json` and record the page result. Missing `box_px` / `points_px` on positioned objects is a page failure. The command also fails when `validation.json` does not contain top-level `passed: true` — a failed page is never recorded; fix the root cause, `run reset` the page, and dispatch or claim a fresh page execution.

```bash
editppt run reset <run> --page page_001 --agent-id <worker-id> --confirm-lost
```

Purpose: return a dispatched or recorded page to `pending`, clearing its dispatch and result records, so a new worker can be dispatched. Recorded pages can be reset with only `--page`. Dispatched pages require `--agent-id` plus `--confirm-lost`, and the id must match the recorded dispatch. Use this only when a worker returned a failed page, `run record` rejected the outputs, the runtime reports a terminal worker state, the user cancels that worker, or repeated reachability checks prove the worker is lost. The failure-handling policy is in `SKILL.md` Phase 3.

```bash
editppt run finalize <run> --defer-accept
```

Purpose: rebuild the recorded page manifests into a new immutable candidate at
`final/candidates/candidate-N/`, validate the candidate, and record its PPTX,
manifest, and validation hashes. This is the preferred path before visual QA.
The candidate remains reviewable in the current run; a failed review does not
require `prepare` again.

```bash
editppt run accept <run> --review-summary <run>/final/visual_qa/page_001/review_summary.json
```

Purpose: accept only the current candidate. The summary must contain a complete
all-pass reviewer checklist, `review.status=pass`, and a `candidate.pptx_sha256`
matching the candidate recorded by `finalize --defer-accept`. High/medium
findings must be resolved. Acceptance copies the verified candidate to the
configured final output and makes the run immutable.

```bash
editppt run finalize <run>
```

Purpose: compatibility path for callers that expect immediate acceptance. It
rebuilds, validates, and outputs the final PPTX, records an implicit candidate
with `acceptance_mode=legacy-finalize`, and freezes the run. New workflows should
use `--defer-accept` followed by `run accept`.

## Page Build Commands

These are the worker-side commands for turning a finished `manifest.json` into the required page artifacts. Use them instead of writing any page-local PowerPoint or imaging code.

```bash
editppt page build pages/page_001
```

Purpose: build `page.pptx` and render `preview.png` from `manifest.json` with the deterministic runtime. Optional `--manifest/--out/--preview` override the default file names inside the page directory.

```bash
editppt page contact-sheet pages/page_001
```

Purpose: create `split_assets_contact.png`, the origin-versus-preview comparison image, from `source.png` and `preview.png` in the page directory.

```bash
editppt page validate pages/page_001
```

Purpose: validate `page.pptx` against `manifest.json` with the same manifest-contract checks `editppt run record` will run (record additionally verifies the full artifact set, hashes, and top-level `passed: true`). Run it before returning so manifest-contract failures are fixed inside the page instead of bouncing back from the parent's record step. Optional `--report <file>` writes a JSON report.

```bash
editppt page render-office pages/page_001
editppt page text-audit pages/page_001 \
  --render pages/page_001/calibration/office-render/slide-1.png
```

`render-office` converts the page PPTX through the available local
LibreOffice/`soffice` renderer, writes `calibration/office-render/page.pdf`,
`slide-N.png`, and `renderer.json`, and records renderer/input/font evidence.
`text-audit` writes `calibration/text-audit.json`. It checks only configured
diagnostics: rendered ink touching/crossing text-box edges, fixed expected line
counts, target ink dimensions, target font sizes, and consistent `size_group`
font sizes. Its `passed` result is a deterministic calibration signal, not
visual acceptance; warnings and the full-page visual gate remain required.

## Parent-level visual QA command

After `editppt run finalize <run> --defer-accept` and a full-resolution
candidate-slide render,
keep the visual evidence beside the final output:

```bash
python <skill-root>/scripts/visual_qa.py \
  --source <source-page.png> \
  --render <final-slide.png> \
  --run <run> \
  --page page_001
```

This writes `<run>/final/visual_qa/page_001/`, including `metrics.json`
(diagnostic only) and `review_summary.json` (the durable reviewer-owned
conclusion). When `--run` points to a prepared run, the summary also records
the current candidate id and PPTX hash for `run accept`. Repeated
`--region name=x,y,width,height` arguments provide
page-specific semantic coverage and replace the generic built-ins. The
helper defaults to `--fit auto`; explicit `stretch`, `contain`, and `crop`
remain supported. Use `--review-status pass|fail` only with one
`--review-check name=pass|fail` for each checklist item; otherwise leave the
summary at its default `needs_review`. Detailed inspection and the separate
structural/visual conclusions are defined in `references/visual-qa.md`.

## Text Measurement Commands

```bash
editppt run hints <run>
```

Purpose: regenerate `text_hints.json`/`text_hints.png` for every page of a prepared run — for example right after configuring a PaddleOCR token, so the current run gets content-aware hints without re-running prepare.

When used with a configured PaddleOCR token, this command calls the external OCR service. If the runtime requires approval for network access, request it with the task-local conversion-data justification from `SKILL.md`; see `SKILL.md` Phase 1 for the approval-rejection policy.

```bash
editppt page hints pages/page_001
```

Purpose: detect the text lines on one page's `source.png` and write `text_hints.json` (each line's source-pixel `box_px`, measured glyph height, and derived font sizes) plus `text_hints.png`, the source image with every detected line framed and labeled. `editppt prepare` already runs this for every page (PDF inputs are OCR'd in one batch job when a PaddleOCR token is available via the `PADDLE_OCR_TOKEN` environment variable or `~/.editppt/config.yaml`; otherwise the built-in offline detector runs). Use this command only to regenerate hints for a page. How to consume the hints is defined in `page-decision-tree.md` section 3.1.

## Image Backend Commands

The commands below are the CLI image-generation surface; `image_gen.imagegen` is an agent tool and has no `editppt` subcommand. See `manifest-schema.md` for the backend field contract.

Generate a new image:

```bash
editppt image generate \
  --prompt-file prompt.txt \
  --out pages/page_001/assets/support.png
```

Create a clean base or foreground asset sheet from the source image:

```bash
editppt image edit \
  --image pages/page_001/source.png \
  --prompt-file clean-base.prompt.txt \
  --out pages/page_001/assets/clean-base.png

editppt image edit \
  --image pages/page_001/source.png \
  --prompt-file asset-sheet.prompt.txt \
  --out pages/page_001/assets/asset-sheet.png
```

When multiple fallback image outputs are required, run `editppt image generate` or `editppt image edit` calls serially. For foreground icons and small visual objects, prefer one sparse asset sheet with generous spacing; create a second sheet only when one sheet cannot fit the required objects cleanly.

These commands select Codex OAuth first, then a configured OpenAI-compatible API fallback. In a network-restricted runtime, request approval before the call and state that only task-local prompts plus required page images/masks/references are uploaded for the current conversion.

## Asset Processing Commands

Record a selected image output:

```bash
editppt image import pages/page_001 \
  --job-id icon-sheet \
  --source-image /tmp/generated.png \
  --dest assets/icon-sheet.png \
  --role asset_sheet \
  --backend builtin-imagegen
```

`--source-image` must be an existing, readable local image. `--backend` records the actual producer and is required; `--fallback-reason` is accepted only when it is consistent with the page's backend contract. Field values and provenance rules live in `manifest-schema.md`.

Process a chroma-key asset sheet:

```bash
editppt image process-sheet pages/page_001 \
  --job-id icon-sheet \
  --asset-sheet-source assets/icon-sheet.png \
  --assets-dir assets/icons
```

When `--job-id` is present, the default chroma image, alpha image, and split report are written under `assets/` with that job id in the filename. This keeps multiple asset-sheet jobs on one page isolated. Explicit `--chroma`, `--alpha`, and `--split-manifest` values still override those defaults; calls without `--job-id` retain the legacy page-level filenames.

The asset sheet key color is determined by the generation prompt; `process-sheet` samples the key color from the image edge. Key-color selection and when to regenerate a sheet with a different key color are defined in `page-decision-tree.md` section 2.2.

## Formula Commands

```bash
editppt formula render-latex pages/page_001 \
  --tex "\\sum_{i \\in N} p_{ij}x_{ij} \\ge a_j u_j" \
  --out assets/formula_001.svg \
  --box 100,120,360,80 \
  --id formula_001 \
  --fragment assets/formula_001.fragment.json
```

The agent transcribes the formula from the source into LaTeX. The CLI only renders it into an image asset and manifest fragment.
