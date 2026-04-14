# Subagent Execution Contract

Status: draft v0.1  
Author: Max  
Date: 2026-04-11

## Purpose

This document defines the exact operating contract for Step 2A / 2B implementations when they are executed by isolated local-model subagents.

Subagents must not rely on prior chat memory. Every assigned task must therefore be fully self-contained.

---

## 1. Global Rules for Step 2A / 2B

Every implementation run must obey these rules:

1. Work milestone-by-milestone
2. Do not redesign the system unless the task explicitly asks for redesign
3. Do not edit files outside the allowed file list
4. Stop when the milestone end condition is satisfied
5. If blocked, produce a concrete blocker report instead of guessing
6. Always run the milestone test commands before declaring completion
7. Respect canonical backend decisions in the spec (for example Gemini 2.5 Flash as the default translation engine)

---

## 2. Required Task Header Format

Every subagent task must include the following fields.

```text
TASK NAME:
OBJECTIVE:
CONTEXT:
ALLOWED FILES:
FORBIDDEN FILES:
INPUTS:
REQUIRED OUTPUTS:
TEST COMMANDS:
DONE WHEN:
FAIL IF:
REPORT BACK WITH:
```

No field may be omitted.

---

## 3. Start State Definition

A valid task start state must specify:

- current repo path
- current branch
- current milestone
- existing input artifact path(s)
- expected output artifact path(s)
- exact files allowed for edits

Example:

```text
Repo path: ~/obsidian/Max-Docs/llm-ccp-propaganda/local-paper-translation-lab
Branch: main or a dedicated working branch
Milestone: M1 Source Extraction
Input: ../papers/2511.23174_Safety_Agents_or_Propaganda_Engine.pdf
Output: outputs/work/source_extracted.md
Allowed files: src/extract.py, tests/test_extraction.py
```

---

## 4. End State Definition

A valid task end state must specify all of the following:

1. required files created or updated
2. test command(s) executed successfully
3. resulting artifact path(s) listed explicitly
4. known limitations listed explicitly
5. subagent stops after milestone completion

Example:

```text
End state achieved when:
- src/extract.py exists and runs
- outputs/work/source_extracted.md exists and is non-empty
- tests/test_extraction.py passes
- subagent reports file paths and stops
```

---

## 5. Milestone Boundaries

### M0 Repo Bootstrap Check
Allowed files:
- README.md
- docs/*
- tests/smoke_* (if needed)

Must not do:
- implement translation logic

### M1 Source Extraction
Allowed files:
- src/extract.*
- tests/test_extraction.*

Must not do:
- segmentation
- translation
- assembly

Output:
- outputs/work/source_extracted.md

### M2 Source Normalization / Reconciliation
Allowed files:
- src/normalize_source.*
- tests/test_source_normalization.*
- small helper files directly imported by normalization code

Must not do:
- segmentation
- translation
- assembly

Output:
- outputs/work/source_clean.md
- optionally outputs/work/source_reference.md

### M3 Segmentation
Allowed files:
- src/segment.*
- tests/test_segmentation.*

Must not do:
- translation logic
- final assembly

Output:
- outputs/work/blocks.jsonl

### M4 English Repair / Normalization
Allowed files:
- src/normalize_*.*
- src/repair_english*.*
- tests/test_source_normalization.*
- tests/test_english_repair*.*

Must not do:
- change downstream zh-TW rendering policy
- introduce speculative semantic rewriting

Output:
- outputs/work/source_repaired.en.md

### M5 Terminology / Glossary
Allowed files:
- src/glossary*.*
- src/term*.*
- tests/test_glossary*.*

Must not do:
- hardcode paper-specific translations without explicit glossary policy
- inject the full glossary blindly into every prompt

Output:
- outputs/work/glossary.json

### M6 Translation Core
Allowed files:
- src/translate.*
- tests/test_translation.*

Must not do:
- rewrite source normalization policy unless the task explicitly asks for it
- redesign final markdown format

Output:
- outputs/work/translated_blocks.<model>.jsonl

Notes:
- translation core is responsible for first-pass Gemini translation only
- translation core should support block-type-aware prompting, glossary-aware prompting, and conservative chunk recombination

### M6B Translation Repair
Allowed files:
- src/repair*.*
- src/translate.*
- tests/test_repair*.*

Must not do:
- redesign source extraction / normalization
- redesign final study markdown policy unless explicitly asked

Output:
- outputs/work/translated_blocks.repaired.<model>.jsonl

### M7 Assembly
Allowed files:
- src/assemble.*
- tests/test_assembly.*

Must not do:
- change translation policy

Output:
- outputs/<paper>.en-clean.md
- outputs/<paper>.zh-TW.md
- outputs/<paper>.study.zh-TW.md

### M6 Figure/Table Handling
Allowed files:
- src/render_*.*
- tests/test_rendering.*

Must not do:
- change upstream block schema unless task explicitly requests schema migration

### M7 Validation
Allowed files:
- src/validate.*
- tests/test_validation.*

Must not do:
- modify generated content to game tests

---

## 6. Failure Reporting Format

If a milestone cannot be completed, the subagent must stop and report:

```text
STATUS: blocked
MILESTONE:
LAST SUCCESSFUL STEP:
BLOCKER:
EXPECTED NEXT ACTION:
FILES TO INSPECT:
```

---

## 7. Completion Reporting Format

When a milestone completes, the subagent must report:

```text
STATUS: complete
MILESTONE:
FILES CHANGED:
OUTPUT FILES:
TESTS RUN:
KNOWN LIMITATIONS:
NEXT RECOMMENDED MILESTONE:
```

---

## 8. Anti-Drift Rule

Subagents must not expand scope.

Bad:
- "I also refactored the pipeline architecture"
- "I also improved README and changed output schema"

Good:
- "I completed M2 segmentation only and stopped"

---

## 9. Why This Contract Exists

The local models in Step 2A / 2B may be strong enough to implement useful modules, but are more reliable when:
- the scope is narrow
- the file boundaries are explicit
- the completion criteria are explicit
- they are not asked to solve the whole project in one pass
