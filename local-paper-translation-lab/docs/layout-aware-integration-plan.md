# Layout-Aware Integration Plan

Date: 2026-04-12

## Goal

Add an optional upstream layout-aware stage inspired by PDFMathTranslate so our Markdown pipeline gets explicit region hints before English repair and segmentation.

## Non-goal

Do not replace our pipeline with PDF re-rendering.
Do not change the primary outputs away from:
- repaired English source
- archival zh-TW Markdown
- study zh-TW Markdown

## Minimal integration target

### New stage
`layout_regions`

### New artifact
`outputs/work/layout_regions.restartN.jsonl`

Each record should contain at least:
- `page_index`
- `region_id`
- `label`
- `bbox`
- `source_hint`
- `confidence`

Preferred labels:
- body
- caption
- footnote
- metadata
- table
- figure
- reference
- equation
- unknown

## Initial experiments

### Experiment 1
Can PDFMathTranslate dependencies run in this environment?

### Experiment 2
Can we invoke its layout model or relevant parser logic to produce page-level region hints for our target paper?

### Experiment 3
Can those region hints improve at least one of these failure modes?
- metadata / footnote intrusion
- figure caption / body confusion
- table-adjacent contamination

## Integration strategy

### Option A — direct wrapper
Use PDFMathTranslate's layout model / page orchestration directly as an upstream helper.

### Option B — partial code borrowing
Borrow their page rendering + region detection pattern, but re-implement a lighter adapter for our repo.

### Option C — external preprocessor
Run an external helper script that writes layout-region JSONL, then feed it into our pipeline.

## Preferred order

1. Get dependencies working
2. Produce a layout-region artifact for one sample paper
3. Inspect whether labels are useful enough for our real failure cases
4. If useful, wire hints into English repair and segmentation
5. Compare against restart2 baseline

## Success criteria

This integration is worth keeping if it materially improves one or more of:
- source-side gate pass quality
- reduction in suspicious blocks after full run
- reduction in manual cleanup around figures / footnotes / tables
