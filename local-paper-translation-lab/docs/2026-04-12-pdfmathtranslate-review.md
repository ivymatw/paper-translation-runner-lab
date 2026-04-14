# PDFMathTranslate Review for local-paper-translation-lab

Date: 2026-04-12
Reviewed repo: `PDFMathTranslate/PDFMathTranslate`
Local inspection path: `/tmp/PDFMathTranslate`

## 1. What PDFMathTranslate is solving

PDFMathTranslate is optimized for translating scientific PDFs while preserving original layout and re-rendering a translated PDF.

Its core architecture is layout-first:
1. detect layout objects on rendered page images
2. parse textual and non-textual regions
3. translate extracted textual content through a translation middleware
4. re-render translated content back into PDF while preserving layout

This is different from our current text-first Markdown pipeline.

## 2. Important code-level findings

### 2.1 Layout-aware upstream is a first-class subsystem
Relevant files:
- `pdf2zh/doclayout.py`
- `pdf2zh/high_level.py`
- `pdf2zh/converter.py`
- `pdf2zh/pdfinterp.py`

What it does:
- uses an ONNX layout model (`DocLayout-YOLO-DocStructBench-onnx`)
- renders each PDF page to image
- predicts layout boxes for regions
- converts layout classes into a page mask / region map
- feeds the region map into a custom converter so text extraction and translation behave differently by region

Why this matters to us:
- our hardest bugs were footnote intrusion, caption/body confusion, and table-adjacent contamination
- those are layout problems, not pure text problems
- PDFMathTranslate treats layout as a primary signal, which is exactly where our current pipeline is weakest

### 2.2 Translator middleware is cleanly separated from parsing
Relevant file:
- `pdf2zh/translator.py`

What it does:
- defines a `BaseTranslator`
- implements many backend adapters under one interface
- supports config/env-based backend configuration
- includes translation cache at translator layer
- prompt generation is centralized per translator

Why this matters to us:
- our current pipeline already has a translation-client abstraction, but it is lighter and less formally middleware-like
- their separation between parser and translator is a useful design reference

### 2.3 Streaming / incremental workflow matters
Relevant file:
- `pdf2zh/high_level.py`

What it does:
- builds a page-by-page translation flow
- supports cancellation, callbacks, streaming, and partial-page work
- keeps state in memory and avoids unnecessary full reruns

Why this matters to us:
- our restart workflow already wants stage-level reruns and cacheable artifacts
- we should formalize stage cache/invalidation more aggressively

### 2.4 Their system is PDF-preserving, ours is Markdown/deep-reading preserving
This is the most important boundary.

We should borrow:
- layout-aware upstream parsing
- translator middleware ideas
- cache/invalidation discipline

We should NOT copy as our primary objective:
- PDF re-rendering
- font embedding / PDF/A workflows
- GUI / Docker / deployment concerns

## 3. Comparison against our current architecture

### PDFMathTranslate strengths relative to us
1. stronger upstream layout model
2. less dependence on text heuristics for caption/footnote/table boundaries
3. cleaner translator abstraction
4. stronger incremental processing mindset

### Our strengths relative to PDFMathTranslate
1. explicit clean English source artifact for auditability
2. explicit glossary stage
3. explicit suspicious-block repair stage
4. study-oriented Markdown output for deep reading
5. clearer separation between archival and study outputs

## 4. Best integration direction

### Recommended
Use PDFMathTranslate ideas and possibly some code as an optional upstream parser layer, while keeping our downstream Markdown pipeline.

In other words:
- do not replace our whole system with PDFMathTranslate
- do not change our primary output target from Markdown to rendered PDF
- do strengthen our upstream with layout-aware region tagging

### Most promising practical path
Add an optional layout-aware stage before source normalization:
- page rendering
- layout box detection / region tagging
- export a structured region artifact
- use that artifact to guide English repair and segmentation

## 5. Directly reusable or adaptable parts

### High-value candidate for adaptation
1. layout model wrapper concept from `pdf2zh/doclayout.py`
   - not necessarily copied verbatim
   - but the abstraction is useful: image page -> region boxes/classes

2. page-level orchestration pattern from `pdf2zh/high_level.py`
   - not for PDF rendering
   - but for per-page structured extraction and progress/caching

3. translator abstraction ideas from `pdf2zh/translator.py`
   - especially cache-aware backend adapters

### Lower-value for us right now
- re-rendering logic in `converter.py`
- PDF object patching internals
- font embedding / PDF/A conversion

## 6. Concrete recommendations for our repo

### Recommendation A
Add a new optional module:
- `src/layout_regions.py`

Responsibility:
- produce page-level region tags from PDF pages
- classify at least:
  - body
  - caption
  - footnote
  - metadata
  - table-like
  - figure-like
  - reference-like

### Recommendation B
Add a new work artifact:
- `outputs/work/layout_regions.restartN.jsonl`

This artifact should become an input to:
- English repair
- segmentation

### Recommendation C
Upgrade our block schema with upstream structure hints
Possible fields:
- `layout_role`
- `origin_page`
- `origin_bbox`
- `confidence`
- `is_metadata_noise`

### Recommendation D
Keep our current downstream strengths
Do not remove:
- repaired English artifact
- glossary artifact
- suspicious-block repair stage
- study assembly

These remain differentiators and are directly aligned with Steve's real use case.

## 7. Final decision

PDFMathTranslate should be treated as:
- an upstream layout-aware design reference
- a possible source of implementation ideas and partial code adaptation
- not a full replacement for our Markdown/deep-reading pipeline

## 8. Next step

Revise our design docs so the canonical architecture becomes:

PDF -> extraction candidates + optional layout-aware region parsing -> source normalization -> English repair informed by layout roles -> segmentation informed by layout roles -> glossary -> translation -> repair -> archival/study Markdown
