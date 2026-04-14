# System Design

Status: draft v0.1  
Author: Max  
Date: 2026-04-11

## 1. Design Principle

The system must be modular enough that a local model or subagent can implement one piece at a time with clear boundaries.

Updated first principle for full-document execution:
- finishing the whole document is more important than insisting every block pass a strict quality gate
- the runner must adapt automatically when one page or block is malformed
- the system should degrade locally, not stall globally
- every degraded decision must leave behind structured evidence for later repair

## 2. Pipeline Overview

```text
Input paper
  -> intake
  -> source extraction
  -> optional layout-aware region parsing
  -> source normalization / source reconciliation
  -> English repair / normalization (informed by layout roles when available)
  -> terminology extraction / glossary build
  -> clean English source artifact
  -> structural segmentation (informed by layout roles when available)
  -> content-type handling
       - paragraphs
       - headings
       - figures
       - tables
       - equations
       - references
       - metadata / footnotes / noise
  -> first-pass Gemini translation from clean English source + glossary subset
  -> suspicious-block detection
  -> targeted Gemini repair
  -> document assembly
  -> study assembly
  -> validation
  -> final markdown outputs
```

## 3. Core Modules

### M1. Intake Module
Responsibility:
- identify source paper path
- define output basename
- create run metadata

Input:
- source PDF path

Output:
- normalized job metadata

### M2. Source Extraction Module
Responsibility:
- obtain machine-readable source text from PDF
- support either direct PDF parsing or pre-extracted markdown fallback

Input:
- PDF file

Output:
- source markdown/text candidate in working format

### M3. Optional Layout-Aware Region Parsing Module
Responsibility:
- extract page-level layout hints before text-first repair begins
- identify likely body / caption / footnote / metadata / table-like / figure-like / reference-like regions
- provide structured evidence for later English repair and segmentation
- optionally borrow design ideas or implementation patterns from PDFMathTranslate-style layout parsing

Output:
- optional layout-region artifact

### M4. Source Normalization / Reconciliation Module
Responsibility:
- choose or construct the cleanest available English source
- allow multiple source candidates (e.g. PDF extraction, markitdown output)
- reconcile conflicts conservatively

Output:
- preliminary clean English source artifact

### M5. English Repair Module
Responsibility:
- repair extraction artifacts in English before translation
- merge broken lines and split headings conservatively
- clean metadata / footnote / inline artifact noise without speculative rewriting
- preserve auditability of the repaired English source

Output:
- repaired clean English source artifact

### M6. Terminology / Glossary Module
Responsibility:
- extract repeated important terms from the repaired English source
- classify terms into preserve-English / canonical zh-TW / preferred zh-TW buckets
- provide compact glossary subsets to downstream translation steps

Output:
- glossary artifact for the paper

### M7. Structural Segmentation Module
Responsibility:
- split repaired clean English source into ordered blocks
- classify blocks into: heading / paragraph / figure / table / equation / code / reference / unknown
- use optional layout-region hints when available to reduce caption/body/footnote contamination

Output:
- ordered block list with stable IDs

### M8. Content Transformation Module
Responsibility:
- normalize blocks before translation
- preserve equations/code/raw identifiers
- convert table structures into intermediate representation

### M9. Translation Module
Responsibility:
- translate only translatable blocks from the repaired clean English source
- use Gemini 2.5 Flash as the canonical translation backend
- preserve protected tokens and structures
- support block-type-aware prompts
- inject relevant glossary subsets for local term consistency
- support chunked execution only as a stability tactic, not as the target output structure
- preserve enough local section context to stabilize terminology without requiring multi-block structured parsing
- support translator middleware abstraction so backend adapters and cache behavior are not entangled with parsing logic
- support local-model translation only as optional comparison/debug paths, not the default production path

### M10. Repair Module
Responsibility:
- inspect first-pass Gemini output for suspicious blocks
- isolate bad blocks without invalidating good blocks
- rerun only suspicious blocks through a repair prompt
- use source + draft + block metadata as repair context
- use glossary guidance when useful to restore term consistency
- emit a repaired translated block artifact

### M11. Assembly Module
Responsibility:
- reconstruct archival markdown in original order
- render tables, figures, equations consistently
- prefer repaired block text over first-pass text when available

### M12. Study Assembly Module
Responsibility:
- produce a reading-oriented zh-TW study version
- suppress raw error markers and obvious extraction artifacts when possible
- keep section flow readable for deep study
- allow conservative omission of low-value noisy material such as broken reference tails in the study view while preserving archival output separately

### M13. Validation Module
Responsibility:
- verify required sections exist
- verify output is non-empty
- verify equations/tables/figure captions were not silently dropped
- verify source-cleanliness and translation quality as separate concerns
- verify suspicious-block detection and repair behave deterministically enough for iterative reruns
- verify glossary extraction improves consistency rather than introducing obvious term drift
- classify each block/page into pass / degraded-pass / failed-hard rather than treating validation as a pure stop signal

### M14. Error Logging and Run Manifest Module
Responsibility:
- write a structured run manifest for the whole document
- record page-level status, block-level validator reasons, fallback reasons, and retry counts
- preserve enough information to reproduce or repair degraded output after the run
- separate completion robustness from translation elegance in the final report

Suggested run statuses:
- `pass`: translated normally and passed validation
- `degraded_pass`: finished with fallback or relaxed validation
- `failed_hard`: impossible to continue without corrupting the output structure

## 4. Recommended Working Files

```text
outputs/work/
  source_extracted.md
  source_reference.md
  layout_regions.jsonl           # optional layout-aware region artifact
  source_clean.md
  source_repaired.en.md
  glossary.json
  blocks.jsonl
  translated_blocks.gemini.jsonl
  translated_blocks.repaired.gemini.jsonl
  assembled.archive.md
  assembled.study.md
  validation_report.json
```

## 5. Design Choice: Intermediate Representation

The system should not translate raw PDF text directly in one pass.

Instead, use an intermediate block representation.

Suggested per-block schema:

```json
{
  "block_id": "b000123",
  "type": "paragraph",
  "section": "3.2",
  "source": "original text",
  "translated": null,
  "meta": {}
}
```

Reason:
- easier debugging
- easier retry
- easier partial re-run
- better suited to subagent work boundaries
- enables block-level repair instead of whole-document rerun

## 6. Error Handling

If a block cannot be reliably processed:
- do not drop it silently
- mark it explicitly
- preserve source text in a fallback wrapper if needed
- keep the failure localized to one block so it can be repaired later
- do not let one bad block stall a whole-document run unless the PDF structure itself would become invalid

Execution policy for full-document mode:
1. try strict translation + validation
2. retry a bounded number of times
3. if still failing, produce a degraded-pass fallback that can still be assembled
4. write the reason into a run manifest / error log
5. continue to the next block or page

Example:
```text
[UNPROCESSED_TABLE_BLOCK:b000145]
<original content>
```

Example manifest fields:
```json
{
  "page": 7,
  "block_id": "b000145",
  "status": "degraded_pass",
  "validator_reason": "dangling_placeholder",
  "fallback_strategy": "source_text_passthrough",
  "retry_count": 3
}
```

## 7. Non-Goals for v1

- perfect layout preservation
- full PDF recreation
- image OCR inside figures
- automatic semantic rewriting for elegance
- using a single generic translation prompt for every block type
