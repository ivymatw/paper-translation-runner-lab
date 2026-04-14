# Layout Integration Experiment

Date: 2026-04-12
Reference system: PDFMathTranslate (`pdf2zh`)
Environment used:
- isolated Python 3.12 venv at `/tmp/pdf2zh-venv`
- installed package: `pdf2zh 1.9.11`

## Goal

Test whether a PDFMathTranslate-style layout-aware upstream stage can improve our pipeline.

## What was implemented

### 1. Region extraction experiment
New script:
- `src/layout_regions.py`

What it does:
- opens the PDF with PyMuPDF
- runs `pdf2zh.doclayout.OnnxModel`
- extracts text blocks with `page.get_text("blocks")`
- assigns each text block the best-overlap layout label
- writes JSONL region hints

Output artifact:
- `outputs/work/layout_regions.restart2.jsonl`

### 2. Alternate source reconstruction experiment
New script:
- `src/layout_to_source.py`

What it does:
- renders the layout-region artifact back into a markdown-like text source
- intended only as an experiment to test whether layout-first text reconstruction can replace current `source_clean`

Output artifact:
- `outputs/work/source_layout_clean.restart2.md`

## Main findings

### Finding 1 — PDFMathTranslate layout parsing is technically usable here
This is a positive result.

Evidence:
- `pdf2zh` imports successfully in isolated Python 3.12 environment
- layout model runs on our target PDF
- region labels such as `title`, `plain text`, `abandon`, `figure_caption`, `table`, and `figure` are produced

This means a layout-aware upstream path is feasible.

### Finding 2 — The region hints are genuinely informative
Examples:
- `*Equal contribution` is detected as `abandon` / `noise`
- Figure 1 caption is detected as a dedicated caption-like region
- table-related content on later pages is clearly separated into table-heavy regions

This confirms the central architectural idea was correct:
our hardest bugs are layout problems, and layout-aware signals can help.

### Finding 3 — Directly reconstructing source text from layout regions is NOT a good replacement path right now
This is the most important negative result.

The generated alternate source (`source_layout_clean.restart2.md`) is materially worse than our current restart2 text-first source artifact.

Observed problems:
- body order is unstable
- figure-internal text is injected into main reading flow
- abstract/introduction sequencing becomes distorted
- some page-level regions are grouped too coarsely
- direct reconstruction does not preserve our desired deep-reading Markdown flow

Conclusion:
- layout-aware parsing is useful
- layout-derived text should NOT replace our current text-first normalized/repaired source artifact

### Finding 4 — Best use of layout-aware parsing is as a hint layer
This is the current recommended direction.

Use layout regions to inform:
- English repair
- segmentation
- noise suppression
- caption/body boundary decisions
- table/figure-adjacent block handling

Do NOT use it as the canonical source reconstruction path yet.

## Architecture decision after experiment

### Adopt
Keep layout-aware parsing as an optional upstream hint stage.

### Do not adopt
Do not replace our `source_clean` / `source_repaired` text artifacts with the raw layout-derived reconstruction.

## Recommended next integration step

Build the next layer as:
- `layout_regions` -> hint enrichment for existing text-first pipeline

Not as:
- `layout_regions` -> replacement source document

## Concrete next candidates

1. Use layout-region hints to mark known noise blocks before English repair.
2. Use layout-region hints to bias caption/body decisions in segmentation.
3. Use layout-region hints to identify table-heavy / figure-heavy suspicious blocks in later sections.

## Bottom line

PDFMathTranslate's parser is worth borrowing as an upstream signal generator.

Its value for us is:
- better structural hints
- better noise/caption/table detection

Its current direct-text reconstruction value for us is poor.

Therefore the correct integration path is:
layout-aware hints + our existing text-first Markdown pipeline.