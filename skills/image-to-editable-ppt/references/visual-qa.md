# Visual Fidelity QA

This is the authoritative parent-level visual gate for
`image-to-editable-ppt`. It is deliberately separate from `editppt page
validate`, `run record`, and candidate build/accept: those commands verify the
editable object contract and package integrity, while this gate verifies what
a reader actually sees. Review the latest deferred candidate before formal
acceptance; never review a stale candidate after a page re-record.

## Required inputs and renderer readiness

For every source page, collect:

- the original page image (or a page-normalized raster extracted from the
  original PDF/PPTX);
- the current candidate (and, after acceptance, the copied final) PPTX rendered to a full-resolution PNG by LibreOffice,
  PowerPoint, or another available Office/PDF renderer;
- the source and rendered page dimensions and the alignment policy recorded by
  the comparison helper.

Before reconstruction/final comparison, run `editppt doctor --json` and
inspect `office_renderer`. A ready renderer includes its executable path. If
it is unavailable, install LibreOffice or provide another final renderer; the
workflow may continue with manifest-preview evidence, but it must label
Office-render QA as unavailable and must not claim final visual QA passed.

Render the current candidate deck, not only a page draft. Preserve the slide
aspect ratio and do not compare a thumbnail, a cropped screenshot, or a stale
preview. The page-local `editppt page render-office` command is the preferred
early renderer for font and wrapping calibration; this parent-level gate still
requires an assembled-deck render.

## Repeatable comparison

The preferred run-local invocation is:

```bash
python <skill-root>/scripts/visual_qa.py \
  --source <source-page.png> \
  --render <final-slide.png> \
  --run <prepared-run> \
  --page page_001
```

This writes to `<prepared-run>/final/visual_qa/page_001/`. An explicit
`--out <qa-dir>` remains available when comparing a standalone page or a
fixture, but it is an override rather than the durable workflow default.
The output directory is owned by this helper: rerunning a comparison replaces
its generated files and removes stale `region_*.png` crops. Keep unrelated
files out of that directory.

The helper's default `--fit auto` compares aspect ratios first. With the
documented 1% relative tolerance, near-equal ratios resolve to `stretch`;
materially different ratios resolve to `contain` so source geometry is not
silently distorted. Explicit `stretch`, `contain`, and `crop` remain
available. `metrics.json` records source/render dimensions, both aspect
ratios, signed and relative deltas, requested and resolved modes, tolerance,
and warnings. An explicit `stretch` on a materially different canvas is
reported as a warning because it can hide distortion.

When `--run` points to a prepared run with `current_candidate`, the helper also
writes a `candidate` object into `review_summary.json` containing the candidate
id, PPTX hash, manifest hash, and a hash verification flag. `editppt run accept`
requires this evidence to match the current candidate.

The helper writes:

- `source_aligned.png`: source mapped to the rendered canvas;
- `overlay.png`: 50/50 source-render overlay for geometry drift;
- `diff.png`: contrast-enhanced pixel difference for locating suspicious
  regions;
- `region_<name>.png`: source, render, and diff crops for each region;
- `regions_contact.png`: labeled contact sheet of all region comparisons;
- `metrics.json`: deterministic dimensions, alignment, region geometry, and
  triage metrics;
- `review_summary.json`: durable reviewer-owned status, checklist, notes, and
  artifact references. It starts at `needs_review`; metrics never set a pass
  or fail decision automatically.

The metrics are diagnostic only. Font rasterization, antialiasing, and Office
renderer differences can produce large pixel differences without a meaningful
design error. Visual inspection is the acceptance decision.

The default `review_summary.json` status is `needs_review`. To record an
inspected conclusion, pass `--review-status pass|fail` together with one
`--review-check name=pass|fail` for each of `global_canvas`,
`structural_completeness`, `text_scale_and_wrapping`, `routing_and_layering`,
and `style_and_detail`. A `pass` requires every checklist item to pass; a
`fail` requires at least one failed item. This keeps a claimed decision from
being paired with an entirely unreviewed checklist. Omit the status and leave
the summary at `needs_review` while inspection is incomplete.

## Region contract

Every region uses one normalized contract: `name=x,y,width,height`. Names are
lowercase safe slugs. `x` and `y` are non-negative, `width` and `height` are
positive, and `x+width <= 1`, `y+height <= 1`.

Without `--region`, the helper uses generic page-agnostic regions:
`full_slide`, `top_band`, `middle_band`, and `bottom_band`. Supplying one or
more `--region` values selects those custom regions only, so an application
can define semantic coverage without unrelated built-in labels. Use
`--include-default-regions` only when generic defaults are intentionally
useful in addition to custom regions.

Choose regions that cover the page's visually meaningful areas. The names are
labels for evidence, not an acceptance taxonomy; a different page type should
replace or supplement them with regions that cover every dense or semantically
important area.

## Inspection order

Inspect the whole slide first, then inspect the selected regions at zoom:

1. global canvas, title/baseline areas when present, major panel bounds, and
   whitespace;
2. structural completeness — every visible card, branch, arrow, dashed path,
   decision node, document strip, window strip, icon, and loopback that exists
   in the source;
3. text scale, wrapping, weight, alignment, and editable content;
4. connector routing, layer order, corner radii, strokes, and color families;
5. dense/detail areas at zoom, when the page type contains them.

The technical-diagram completeness list is conditional: apply the detailed
branch/rail/loopback and repeated-block checks to architecture, pipeline, or
research-framework pages, not as a universal requirement for every page type.

## Mismatch classification

Classify each visible discrepancy before changing the manifest:

- **missing object** — a visible source primitive or asset has no counterpart;
- **geometry** — a box, rail, arrow, corner, or whitespace boundary is
  displaced or scaled;
- **text** — content, font size, weight, line break, alignment, or editability
  is wrong;
- **routing/layering** — an arrow points to the wrong block, a dashed loopback
  is absent, or an object is covered;
- **style** — fill, border, radius, stroke width, color family, or asset edge
  differs;
- **renderer-only** — a small antialiasing or font-raster difference with no
  layout/content impact.

The first five categories are current-page fixes when they are visible or
affect comprehension. Only the last category, plus genuinely minor
non-critical decoration drift, may be recorded as a warning after the
required object-source workflow succeeds.

## Correction loop

Use this order to avoid compensating errors:

1. Fix missing structural primitives and major panel bounds.
2. Fix connector routes, arrowheads, dashed paths, and z-order.
3. Fix text boxes, font sizes, wrapping, and alignment. After manual
   calibration, disable automatic fitting for the calibrated boxes so the
   runtime does not shrink them again.
4. Fix colors, borders, corner radii, and minor spacing.
5. Rebuild the affected page from its manifest, run page validation, record it,
   build a new candidate with `editppt run finalize <run> --defer-accept`, and
   rerun this gate.

Do not patch only the rendered PNG or place a full-slide screenshot behind
editable text. Do not treat a low diff score as proof that an object-source
decision is valid. For a material correction after a run is
`accepted`/`complete`, create a fresh `editppt prepare` run rather than
mutating accepted final artifacts in place.

## Acceptance record

The handoff must state both outcomes separately and point to the durable
review evidence:

```text
structural validation: passed
visual QA: passed | failed | unavailable (Office renderer)
visual QA artifacts: <run>/final/visual_qa/page_NNN/
review summary: <run>/final/visual_qa/page_NNN/review_summary.json
```

Formal acceptance is a separate command:

```bash
editppt run accept <run> \
  --review-summary <run>/final/visual_qa/page_NNN/review_summary.json
```

It requires `review.status=pass`, a complete all-pass checklist, the current
candidate PPTX hash, and no unresolved high/medium findings. Numeric metrics
remain triage evidence and never set the visual decision automatically.

If the reviewer accepts a known minor difference, list the exact region and
category in the summary. Never report only “PPT generated successfully”; that
describes package creation, not visual fidelity.
