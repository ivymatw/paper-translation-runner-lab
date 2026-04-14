# Spec: Local LLM Paper Translation System

Status: draft v0.1  
Author: Max  
Date: 2026-04-11

## 1. Purpose

Build a local-LLM-driven system that converts a standard academic PDF paper into a clean English source representation and then translates it into Traditional Chinese Markdown for deep reading.

Primary objective:
- preserve article structure and reading flow
- produce output usable in Obsidian
- support figures, tables, and equations in a readable form
- separate source extraction quality from translation quality
- be implementable by local models under a strict, modular, testable workflow

Secondary objective:
- keep the codebase modular, testable, and inspectable enough that stage-level failures can be isolated and fixed quickly

Canonical development decision:
- the project no longer prioritizes local Qwen/Gemma as software implementers for this repo
- Max handles implementation directly unless there is a specific reason to delegate a bounded task

Canonical translation-engine decision:
- Gemini 2.5 Flash is the default translation backend for production-quality academic translation output
- local Qwen/Gemma translation runs may still be used as diagnostics or capability probes, but not as the default final-output path
- the production translation path is no longer treated as a one-pass full-document translation step
- the canonical production path is now: clean English source (+ optional layout-aware region parsing) -> English repair / normalization -> terminology extraction / glossary build -> typed block translation with Gemini -> suspicious-block repair with Gemini -> study-oriented assembly

## 2. First Target Paper

Primary development/evaluation paper:
- `2511.23174_Safety_Agents_or_Propaganda_Engine.pdf`

Characteristics:
- standard academic paper layout
- two-column sections
- contains figures, tables, and equations
- suitable as a realistic first implementation target

## 3. Output Requirements

Primary output formats:
- one cleaned English source Markdown file per paper
- one archival Traditional Chinese Markdown file per paper
- one study-oriented Traditional Chinese Markdown file per paper

Output goals:
1. English source is cleaner and more structurally reliable than raw PDF text extraction
2. Full-text translation, not summary
3. Good reading flow for deep study
4. Preserved section hierarchy
5. Equations preserved in original symbolic form
6. Tables preserved structurally when feasible
7. Figures represented in a way that preserves comprehension
8. Translation quality problems should be repairable at block level without rerunning the whole paper
9. Final reading output should come from a study-oriented assembly path rather than raw first-pass block concatenation

## 4. Scope

In scope:
- parse source PDF or use pre-extracted source markdown
- generate a clean English source artifact
- perform English repair / normalization before translation
- extract important terminology from the repaired English source and build a translation glossary
- translate the clean English source into Traditional Chinese
- support block-type-aware translation policy
- support suspicious-block detection and targeted repair after first-pass translation
- preserve section order and logical flow
- preserve and render tables, figures, equations, code blocks, references
- generate deterministic file outputs under a fixed directory structure
- run tests on extraction quality, structure quality, English repair quality, glossary quality, translation quality, and repair quality separately

Out of scope for v1:
- perfect publication-quality PDF regeneration
- redrawing all figures in Chinese
- OCR for low-quality scanned PDFs
- citation normalization across papers
- multilingual output beyond zh-TW

## 5. Translation Policy

### 5.1 General
- translate into Traditional Chinese (Taiwan usage)
- do not summarize
- do not omit sections unless explicitly marked as unprocessable
- preserve technical precision over literary fluency
- treat English repair, glossary building, translation, and zh-TW repair as separate stages
- prefer conservative block-level retry/repair over whole-document reruns
- translation consistency should be guided by a paper-specific glossary built from the repaired English source, not by ad-hoc prompt memory alone

### 5.2 Keep in original form
- author names
- institution names when official translation is uncertain
- emails
- URLs
- model names
- dataset names
- benchmark names
- BibTeX entries
- equations
- code blocks

### 5.3 English repair / normalization policy
Before translation begins, the system must produce a repaired English source that is materially cleaner than raw extraction output.

English repair requirements:
- merge obviously broken lines when the continuation is strongly inferable
- fix split headings when the structural intent is clear
- reduce extraction noise in metadata, footnotes, and inline artifacts conservatively
- use layout-aware region evidence when available to avoid mixing captions, footnotes, metadata, and main prose
- preserve factual content, citations, model names, dataset names, and mathematical notation
- avoid speculative rewriting or semantic expansion

The English repair stage is allowed to improve readability and structural integrity, but it must remain conservative enough that it can still serve as an auditable source artifact.

### 5.4 Terminology extraction / glossary policy
A paper-specific glossary should be extracted from the repaired English source before translation.

Glossary goals:
- improve translation consistency across repeated concepts
- reduce drift in key technical and conceptual terms
- distinguish terms that should stay in English from terms that should have canonical zh-TW translations

Glossary should include at least:
- paper title
- section titles
- repeated core concepts
- method names
- dataset names
- model names
- benchmark names
- politically sensitive concepts central to the paper

Each glossary entry should support one of these policies:
- preserve in English
- canonical zh-TW translation
- preferred zh-TW translation with context sensitivity

The glossary should be built after English repair, not directly from raw extraction output.

### 5.5 Layout-aware source policy
The system should optionally support a layout-aware upstream stage before final segmentation.

Goals:
- reduce caption/body confusion
- reduce footnote and metadata intrusion into core prose
- provide structured region hints that later stages can consume
- borrow or adapt ideas from PDFMathTranslate-style layout parsing when it materially improves accuracy

This stage is optional in the sense that the pipeline should still run without it, but it is a preferred direction for improving difficult scientific PDFs.

### 5.6 Block-type-aware translation policy
The system must not use a single undifferentiated translation policy for every block.

Required block families:

1. metadata blocks
   - title
   - author line
   - affiliation line
   - emails / identifier-heavy lines
   Policy:
   - translate title
   - preserve personal names, emails, URLs, and uncertain institution names
   - prefer minimal intervention over prose rewriting

2. core prose blocks
   - abstract
   - introduction / body / discussion / conclusion paragraphs
   Policy:
   - use Gemini as the canonical translator
   - use section-aware prompts
   - allow chunking only when needed for stability
   - recombine chunk outputs into one coherent paragraph block

3. caption blocks
   - figure captions
   - table captions
   Policy:
   - translate faithfully but compactly
   - preserve figure/table numbering and technical identifiers

4. protected blocks
   - equations
   - code
   - references / BibTeX-like content
   Policy:
   - preserve source as primary representation
   - only translate surrounding explanatory text when structurally separate

### 5.7 Translation middleware policy
The translation layer should remain cleanly separated from parsing and repair.

Requirements:
- backend adapters should share a common interface
- cache behavior should be controlled at translator/backend layer rather than mixed into parsing logic
- prompt profiles should be configurable without rewriting extraction code

### 5.8 Translation prompt context policy
The translation prompt should include a compact subset of the glossary relevant to the current block or section.

Rules:
- do not inject the entire glossary into every prompt if it would create prompt noise
- include the most relevant glossary entries for the current block
- section headings and local repeated concepts should have priority over distant low-frequency terms
- glossary guidance should influence term consistency but must not force obviously wrong translations in context

### 5.9 Figures
For each figure:
- preserve figure number
- translate caption
- add a short Chinese figure understanding note when needed
- if source image extraction is unavailable, still preserve figure placeholder and caption translation

### 5.10 Tables
Preferred order:
1. preserve as Markdown table
2. if table is too complex, convert into structured bullet form
3. never silently drop table content

### 5.11 Equations
- preserve equations using original LaTeX-style math where available
- translate surrounding explanatory text
- do not rewrite mathematical notation into prose only

### 5.12 Suspicious-block repair policy
The canonical Gemini path must include a repair stage after first-pass translation.

Repair stage requirements:
- detect suspicious translated blocks using explicit heuristics
- rerun only flagged blocks, not the entire paper
- provide Gemini with:
  - source English block
  - first-pass zh-TW draft
  - block type
  - section context
- ask Gemini to repair fluency and completeness while preserving claims, citations, numbers, names, and technical terms

Suspiciousness signals should include at least:
- explicit `[TRANSLATION_ERROR:...]` markers
- unresolved `§PROTECTED_x§` placeholder residue
- abnormal English residue in a prose block
- duplicated lines / duplicated fragments
- obviously broken chunk seams
- severe length anomalies compared with source

## 6. Repository-Level Workflow

Additional architecture note inspired by PDFMathTranslate:
- upstream layout parsing and downstream translation should be treated as separate first-class concerns
- if we adopt external layout-aware components, they should feed structured hints into our Markdown pipeline rather than replace the archival/study Markdown outputs

### Step 1 — design and implementation
Max maintains the design/spec/test documents and implements the pipeline directly.

### Step 2 — stage-gated execution
The system is rerun from the earliest necessary stage and may advance only after the current stage passes its gate.

Canonical restart order:
1. extraction
2. source normalization
3. English repair
4. glossary extraction
5. segmentation
6. trusted-slice translation
7. suspicious-block repair
8. assembly / study assembly
9. whole-paper canonical run

### Step 3 — stop-and-discuss rule
If a stage fails its gate:
- stop advancing
- document the failure mode
- decide whether to revise code, revise the stage design, or revise the tests
- rerun from the last good stage only after the failure is understood

## 7. Execution Constraints

The implementation must support clean stage boundaries.

Implications:
1. Every stage must have a clear start state
2. Every stage must have a clear end state
3. Each module must define exact input/output files
4. Each module must define success criteria
5. Each module must define what not to modify
6. Each stage should be rerunnable independently when possible

### 7.1 Required stage boundary format
Every stage should specify:
- objective
- input artifacts
- output artifacts
- test command(s)
- stage-gate checks
- completion condition
- failure condition

### 7.2 Anti-ambiguity rule
No implementation task should say only:
- "build the translation system"
- "handle figures/tables/equations"

Instead, each task must target one bounded stage, one bounded module, or one bounded failure mode.

## 8. Success Criteria for v1

A v1 run is considered successful if:
1. the system runs locally without manual patching mid-run
2. it produces a clean English source artifact
3. it produces both an archival zh-TW artifact and a study zh-TW artifact from that source
4. the output keeps the paper's main section order
5. most paragraphs are translated rather than omitted
6. equations are preserved
7. tables are preserved or transformed into readable structured form
8. figure captions are preserved and translated
9. suspicious blocks can be isolated and repaired without full rerun
10. tests pass

## 9. Canonical Directories

```text
samples/      input paper references
src/          implementation
tests/        automated checks
outputs/      generated markdown and artifacts
docs/         spec and process docs
```

Recommended output artifacts:

```text
outputs/work/source_extracted.md
outputs/work/source_reference.md
outputs/work/source_clean.md
outputs/work/blocks.jsonl
outputs/work/translated_blocks.<model>.jsonl
outputs/work/translated_blocks.repaired.<model>.jsonl
outputs/<paper>.en-clean.md
outputs/<paper>.zh-TW.md
outputs/<paper>.study.zh-TW.md
```

## 10. Core design deliverables

- `docs/spec.md`
- `docs/system-design.md`
- `docs/implementation-plan.md`
- `docs/test-plan.md`
- `docs/acceptance-rubric.md`

These documents are the canonical design input to stage-gated implementation and restart execution.
