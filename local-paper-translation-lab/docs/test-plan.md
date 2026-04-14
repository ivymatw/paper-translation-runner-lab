# Test Plan

Status: revised v0.2
Author: Max
Date: 2026-04-12

## 1. Why the old plan was insufficient

The previous test plan over-weighted artifact existence and end-stage output checks.

That allowed a bad outcome:
- unit tests passed
- pipeline artifacts existed
- but core zh-TW prose was still severely truncated

So the new rule is:
- tests must guard each stage against the actual failure modes of that stage
- a later stage must not be allowed to hide an earlier-stage defect
- passing tests must mean "safe to advance to next stage", not merely "files were produced"

## 2. Testing philosophy

The pipeline is now tested by stage gates.

A stage may advance only if:
1. code-level tests pass
2. stage-specific artifact checks pass
3. stage-specific quality gate passes
4. known residual defects are documented and judged acceptable for the next stage

This means we stop treating the whole paper as one opaque run.

## 3. Canonical stages

The canonical stages are:
1. extraction
2. source normalization
3. English repair
4. glossary extraction
5. segmentation
6. first-pass translation
7. suspicious-block detection and repair
8. assembly / study assembly
9. final acceptance review

## 4. Stage-gated test strategy

### Gate G1 — Extraction
Purpose:
Verify raw extraction is usable as input to normalization.

Automated checks:
- extracted source artifact exists
- file is non-empty
- target paper title appears
- abstract marker appears
- introduction marker appears
- references marker appears if present in the source paper

Failure conditions:
- extraction missing major paper sections
- extraction is mostly binary garbage / unreadable noise
- extracted artifact is too incomplete to continue

Human spot check:
- can a human roughly identify article flow?
- is the paper mostly present, even if dirty?

### Gate G2 — Source normalization
Purpose:
Verify normalization improves structure rather than merely rewriting text.

Automated checks:
- normalized source exists and is non-empty
- key sections remain present
- normalization does not delete title / abstract / introduction / references markers
- no obvious catastrophic duplication explosion

Failure conditions:
- normalized text loses major sections
- normalization creates new large repeated spans
- source order becomes less coherent than extraction

### Gate G3 — English repair
Purpose:
Verify repaired English is trustworthy enough to serve as the translation source.

Automated checks:
- repaired English exists and is non-empty
- key sections remain present
- no obvious paragraph-ending truncation in known long prose blocks
- no severe line-break damage in core prose where continuity is strongly inferable

Required targeted checks on the target paper:
- abstract paragraph should be complete
- introduction first 3 prose paragraphs should be complete
- problem definition 2.1 first prose paragraph should be complete

Failure conditions:
- core prose paragraphs are truncated
- footnotes are merged into body prose in a way that breaks reading
- figure/table material corrupts major body paragraphs

Human acceptance question:
- would I trust this repaired English as the canonical auditable source for translation?

### Gate G4 — Glossary extraction
Purpose:
Verify glossary supports consistency instead of adding prompt noise.

Automated checks:
- glossary artifact exists and parses
- includes paper title
- includes repeated key technical terms
- includes preserve-English entries for obvious model / dataset / benchmark names when appropriate

Failure conditions:
- glossary is empty or malformed
- glossary misses repeated core concepts central to the paper
- glossary introduces obviously wrong canonical translations

### Gate G5 — Segmentation
Purpose:
Verify structure is represented correctly before translation.

Automated checks:
- blocks file exists
- every line parses as JSON
- each block has `block_id`, `type`, `source`
- block ids are unique and ordered
- sections are monotonic enough to reflect reading flow

Required quality checks:
- no obvious paragraph truncation introduced by segmentation
- figure captions do not swallow following body prose
- tables do not swallow unrelated prose
- references remain references
- equations / code remain protected blocks

Required targeted checks on the target paper:
- introduction first 3 prose blocks should be semantically complete
- 2.1 first prose block should be semantically complete
- known figure-caption boundary near Figure 1 must not absorb following body prose

Failure conditions:
- prose broken into incomplete fragments that are not real semantic blocks
- figure/table/footnote contamination inside core prose blocks
- section order becomes misleading

### Gate G6 — First-pass translation
Purpose:
Verify translated blocks are complete enough to be candidates for repair, not silently broken.

Automated checks:
- translated block count matches source block count
- all translatable blocks contain translated text or explicit error markers
- unresolved placeholders are flagged
- repeated prompt leakage / reasoning traces are flagged
- likely truncated translations are flagged

Required targeted checks:
- introduction first 2 prose blocks must not end in obvious truncation
- 2.1 first prose block must not end in obvious truncation
- long prose blocks should not be suspiciously short relative to source

Failure conditions:
- large numbers of prose blocks are truncated
- prompt leakage appears in prose output
- model returns reasoning traces or repeated junk
- untranslated English dominates where translation should exist

Important rule:
Passing unit tests here is not enough. The stage fails if translated prose is materially incomplete even when file structure is correct.

### Gate G7 — Suspicious-block repair
Purpose:
Verify repair catches bad blocks rather than cosmetically rewriting already-good blocks.

Automated checks:
- suspicious blocks are explicitly detectable
- repair reruns only flagged blocks
- repaired blocks remove placeholder leakage when possible
- repaired blocks should not remain obviously truncated

Required targeted checks:
- the previously truncated target blocks must either:
  - become complete zh-TW, or
  - remain explicitly flagged and prevented from flowing into final zh-TW output as if healthy

Failure conditions:
- repair preserves obviously truncated drafts
- repair introduces fresh truncation
- repair emits meta text / leakage / explanations into final block text

### Gate G8 — Assembly / study assembly
Purpose:
Verify assembly preserves trustworthy content and does not mask stage failures.

Automated checks:
- final markdown exists and is non-empty
- title rendered
- section headings rendered
- equations preserved
- figures and tables represented
- references handled according to output type
- truncated zh-TW blocks do not silently appear as accepted prose

Failure conditions:
- assembly hides upstream structural failures
- study assembly silently drops important prose
- final output contains half-translated or obviously cut-off prose presented as normal

Important rule:
Assembly may fall back conservatively, but must not create the illusion that upstream translation passed.

### Gate G9 — Final acceptance review
Purpose:
Judge deep-reading usability only after earlier gates pass.

Manual review questions:
1. Can a human follow the paper from abstract to conclusion?
2. Are the key claims understandable in zh-TW without constant source cross-checking?
3. Are method and experiment sections coherent?
4. Are figures, tables, and equations usable during study?
5. Would Steve actually use this output for deep reading?

## 5. Test types

### A. Unit tests
Current suite covers:
- extraction
- source normalization
- English repair
- glossary
- segmentation
- translation
- repair
- assembly

Rule:
Unit tests should encode known failure patterns whenever we discover one.
The recent truncation bug is exactly the kind of failure that must become a regression test.

### B. Stage validation reports
In addition to unit tests, each major run should produce a human-readable validation report for the current gate.

Immediate need:
- `docs/source-side-acceptance-checklist.md`
- `outputs/work/source-side-validation-report.md`

### C. Trusted-slice evaluation
Before whole-paper reruns, use a small trusted slice:
- Abstract
- Introduction first 3 paragraphs
- Problem Definition 2.1 first paragraph

This slice becomes the canonical health probe for translation quality.

## 6. Current diagnosis of test-gap

The main missing coverage was:
- tests existed at code level
- but the plan did not explicitly require stage-gated completeness checks on known critical paragraphs
- so a run could be considered healthy while still producing severely truncated Chinese prose

This must not happen again.

## 7. Immediate next testing tasks

1. define a source-side acceptance checklist
2. review repaired English for the target paper against that checklist
3. review segmentation for the same trusted slice
4. only then rerun canonical translation on the trusted slice
5. only after that consider a whole-paper canonical run

## 8. Bottom line

A passing test suite is necessary but not sufficient.

For this project, a stage only passes when:
- code passes
- artifacts exist
- the stage-specific failure modes are checked
- the output is trustworthy enough to advance
