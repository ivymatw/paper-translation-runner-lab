# Milestone Task Templates for Step 2A / 2B

Status: draft v0.1  
Author: Max  
Date: 2026-04-11

## Purpose

These templates are the canonical task prompts for future Step 2A / 2B implementation runs.

They are designed to be directly reusable for Qwen and Gemma with minimal ambiguity.

---

## Template: M1 Source Extraction

```text
TASK NAME:
M1 Source Extraction

OBJECTIVE:
Implement a minimal source extraction module that converts the sample paper into machine-readable markdown/text.

CONTEXT:
Repo: ~/obsidian/Max-Docs/llm-ccp-propaganda/local-paper-translation-lab
Paper: ../papers/2511.23174_Safety_Agents_or_Propaganda_Engine.pdf
Read docs/spec.md, docs/system-design.md, docs/implementation-plan.md, docs/test-plan.md before editing.

ALLOWED FILES:
- src/extract.py
- tests/test_extraction.py
- small helper files directly imported by src/extract.py

FORBIDDEN FILES:
- docs/*
- README.md
- src/segment.py
- src/translate.py
- src/assemble.py

INPUTS:
- ../papers/2511.23174_Safety_Agents_or_Propaganda_Engine.pdf

REQUIRED OUTPUTS:
- outputs/work/source_extracted.md

TEST COMMANDS:
- run the extraction script on the sample paper
- run tests/test_extraction.py

DONE WHEN:
- extraction script exists
- source_extracted.md exists and is non-empty
- test file passes
- you stop after M1

FAIL IF:
- you start implementing segmentation or translation logic
- output file is missing or empty
- tests are not run

REPORT BACK WITH:
- files changed
- exact command used
- output file path
- test results
- known limitations
```

---

## Template: M2 Source Normalization / Reconciliation

```text
TASK NAME:
M2 Source Normalization / Reconciliation

OBJECTIVE:
Construct a clean English source artifact from available source candidates.

CONTEXT:
Use outputs/work/source_extracted.md from M1.
You may also use the existing markitdown-generated source paper markdown when available.
Read docs/spec.md, docs/system-design.md, docs/implementation-plan.md, docs/test-plan.md before editing.

ALLOWED FILES:
- src/normalize_source.py
- tests/test_source_normalization.py
- small helper files directly imported by the normalization module

FORBIDDEN FILES:
- docs/*
- README.md
- src/segment.py
- src/translate.py
- src/assemble.py

INPUTS:
- outputs/work/source_extracted.md
- ../papers/2511.23174_Safety_Agents_or_Propaganda_Engine.md (if present)

REQUIRED OUTPUTS:
- outputs/work/source_clean.md
- optionally outputs/work/source_reference.md

TEST COMMANDS:
- run normalization on available sources
- run tests/test_source_normalization.py

DONE WHEN:
- source_clean.md exists and is non-empty
- source_clean is cleaner and more usable than raw extraction as translation input
- tests pass
- you stop after M2

FAIL IF:
- you start implementing segmentation or translation logic
- source_clean is missing or clearly unusable

REPORT BACK WITH:
- files changed
- which source candidates were used
- output paths
- test results
- known limitations
```

---

## Template: M3 Segmentation

```text
TASK NAME:
M3 Segmentation

OBJECTIVE:
Implement a segmentation module that converts the clean English source into ordered typed blocks.

CONTEXT:
Use outputs/work/source_clean.md from M2.
Read docs/system-design.md and docs/implementation-plan.md before editing.

ALLOWED FILES:
- src/segment.py
- tests/test_segmentation.py
- shared schema helper if necessary

FORBIDDEN FILES:
- docs/*
- README.md
- translation and assembly modules

INPUTS:
- outputs/work/source_clean.md

REQUIRED OUTPUTS:
- outputs/work/blocks.jsonl

TEST COMMANDS:
- run segmentation on the clean source
- run tests/test_segmentation.py

DONE WHEN:
- every block has block_id, type, source
- blocks.jsonl is parseable line-by-line as JSON
- order is preserved
- tests pass
- you stop after M3

FAIL IF:
- you redesign upstream source normalization format without need
- you start translating content

REPORT BACK WITH:
- files changed
- block schema summary
- output path
- test results
- known limitations
```

---

## Template: M4 Translation Core

```text
TASK NAME:
M4 Translation Core

OBJECTIVE:
Implement translation of heading and paragraph blocks from the clean English source into Traditional Chinese while preserving protected content.

CONTEXT:
Use outputs/work/blocks.jsonl from M3.
Use Gemini 2.5 Flash as the canonical translation backend.
Local-model translation may exist only as an optional diagnostic path, not as the default final-output path.
Do not solve full figure/table rendering in this milestone.

ALLOWED FILES:
- src/translate.py
- tests/test_translation.py
- shared schema/model client helpers if necessary

FORBIDDEN FILES:
- docs/*
- README.md
- assembly module
- validation module

INPUTS:
- outputs/work/blocks.jsonl

REQUIRED OUTPUTS:
- outputs/work/translated_blocks.jsonl

TEST COMMANDS:
- run translation on sample blocks
- run tests/test_translation.py

DONE WHEN:
- heading and paragraph blocks receive translated text
- protected blocks remain preserved
- output block count matches input block count
- Gemini-backed translation path works successfully
- tests pass
- you stop after M4

FAIL IF:
- equations or code blocks are rewritten destructively
- output block count changes unexpectedly

REPORT BACK WITH:
- files changed
- translation policy actually implemented
- output path
- test results
- known limitations
```

---

## Template: M5 Assembly

```text
TASK NAME:
M5 Assembly

OBJECTIVE:
Assemble the clean English source and translated blocks into final Markdown outputs for the sample paper.

CONTEXT:
Use outputs/work/source_clean.md and outputs/work/translated_blocks.jsonl.
Maintain original order.

ALLOWED FILES:
- src/assemble.py
- tests/test_assembly.py

FORBIDDEN FILES:
- docs/*
- README.md
- extraction/normalization/segmentation/translation logic unless required for tiny import fixes

INPUTS:
- outputs/work/source_clean.md
- outputs/work/translated_blocks.jsonl

REQUIRED OUTPUTS:
- outputs/2511.23174_Safety_Agents_or_Propaganda_Engine.en-clean.md
- outputs/2511.23174_Safety_Agents_or_Propaganda_Engine.zh-TW.md

TEST COMMANDS:
- run assembly
- run tests/test_assembly.py

DONE WHEN:
- final markdown outputs exist
- section order preserved
- title exists in Chinese
- tests pass
- you stop after M5

FAIL IF:
- final markdown is empty
- large sections are missing

REPORT BACK WITH:
- files changed
- output paths
- test results
- known limitations
```

---

## Template: M6 Figure and Table Handling

```text
TASK NAME:
M5 Figure and Table Handling

OBJECTIVE:
Improve the pipeline so figure captions and tables are preserved in readable form.

CONTEXT:
This milestone upgrades rendering quality, not the whole architecture.

ALLOWED FILES:
- src/render_figures.py
- src/render_tables.py
- tests/test_rendering.py
- minimal related integration changes

FORBIDDEN FILES:
- docs/*
- README.md
- broad schema redesign unless explicitly justified

INPUTS:
- outputs/work/blocks.jsonl
- outputs/work/translated_blocks.jsonl

REQUIRED OUTPUTS:
- improved assembled markdown with preserved figure captions and tables

TEST COMMANDS:
- run rendering tests
- regenerate sample output and inspect figure/table placeholders

DONE WHEN:
- figure captions preserved and translated
- tables preserved or converted into structured bullets
- tests pass
- you stop after M5

FAIL IF:
- tables are silently dropped
- figure captions disappear

REPORT BACK WITH:
- files changed
- sample figure/table behavior
- test results
- known limitations
```

---

## Template: M7 Validation

```text
TASK NAME:
M7 Validation

OBJECTIVE:
Implement automated validation checks for the final output quality constraints.

CONTEXT:
Use the v1 acceptance conditions from docs/spec.md and docs/test-plan.md.

ALLOWED FILES:
- src/validate.py
- tests/test_validation.py

FORBIDDEN FILES:
- docs/*
- README.md
- do not modify assembled output by hand to satisfy checks

INPUTS:
- outputs/2511.23174_Safety_Agents_or_Propaganda_Engine.zh-TW.md

REQUIRED OUTPUTS:
- outputs/work/validation_report.json

TEST COMMANDS:
- run validation on final markdown
- run tests/test_validation.py

DONE WHEN:
- validation report exists
- tests pass
- validation catches missing critical structures
- you stop after M7

FAIL IF:
- checks are too weak to catch obvious truncation or omission

REPORT BACK WITH:
- files changed
- validation checks implemented
- report path
- test results
- known limitations
```
