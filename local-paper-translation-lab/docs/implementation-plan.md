# Implementation Plan

Status: draft v0.1  
Author: Max  
Date: 2026-04-11

## 1. Implementation Strategy

Implement in bounded milestones so Step 2A / 2B can be delegated to subagents safely.

## 2. Milestones

### Milestone 0: Repo bootstrap check
Goal:
- confirm repo structure
- define sample input path
- define expected output path

Done when:
- sample path documented
- outputs directory exists

### Milestone 0.5: Completion-oriented PDF reconstruction runner
Goal:
- formalize a page-level reconstruction runner that can finish a whole document without manual babysitting
- make local degradation an official runtime behavior rather than an ad hoc emergency patch
- write machine-readable run artifacts for later diagnosis

Required outputs:
- document-level run manifest
- page-level event log
- error log for degraded pages/blocks
- merged mono output assembled from translated pages plus explicit passthrough fallback when needed

Done when:
- one bad block/page no longer stalls the entire run
- a run can be resumed page-by-page
- degraded pages are logged rather than silently swallowed
- the final document can still be assembled even when some pages fall back

### Milestone 1: Source extraction
Goal:
- convert sample paper into machine-readable markdown/text candidate

Allowed files:
- `src/extract_*`
- `tests/test_extraction.*`

Required outputs:
- `outputs/work/source_extracted.md`

Done when:
- extraction runs successfully
- file exists and is non-empty

### Milestone 2: Source normalization / source reconciliation
Goal:
- construct a cleaner English source artifact from available candidates
- support markitdown output as a primary source candidate when helpful

Required outputs:
- `outputs/work/source_clean.md`
- optionally `outputs/work/source_reference.md`

Done when:
- source_clean exists and is non-empty
- source quality is better than raw extraction for translation purposes

### Milestone 3: Block segmentation
Goal:
- split clean English source into typed ordered blocks

Required outputs:
- `outputs/work/blocks.jsonl`

Done when:
- every block has block_id and type
- order is preserved

### Milestone 4: Minimal translation pipeline
Goal:
- translate headings and paragraph blocks only from clean English source
- preserve equations/code untouched
- use Gemini 2.5 Flash as the default translation backend

Required outputs:
- `outputs/work/translated_blocks.jsonl`

Done when:
- translatable blocks receive translated text
- protected blocks remain intact
- Gemini-backed translation path runs successfully

### Milestone 5: Assembly
Goal:
- assemble translated blocks into final markdown
- optionally assemble clean English markdown too

Required outputs:
- `outputs/2511.23174_Safety_Agents_or_Propaganda_Engine.en-clean.md`
- `outputs/2511.23174_Safety_Agents_or_Propaganda_Engine.zh-TW.md`

Done when:
- final markdown exists
- section order is preserved

### Milestone 6: Tables and figure captions
Goal:
- add explicit handling for figures and tables

Done when:
- figure captions preserved and translated
- tables preserved or converted into structured readable form

### Milestone 7: Validation
Goal:
- add automated validation checks

Required outputs:
- `outputs/work/validation_report.json`

Done when:
- validation script passes on sample paper

## 3. Step 2A / 2B Execution Rule

Each model implementation run should work milestone-by-milestone, not all at once.

Recommended order:
1. implement one milestone
2. run milestone tests
3. inspect outputs
4. only then move to next milestone

## 4. Prompting Rule for Subagent Implementation

Every Step 2 prompt must include:
- exact milestone name
- exact files allowed to edit
- exact expected output file(s)
- exact test command(s)
- instruction to stop after milestone completion

## 5. Compare Qwen vs Gemma Fairly

To compare models fairly:
- use the same repo state
- use the same milestone definition
- use the same sample paper
- use the same acceptance criteria
- record defects by milestone

## 6. Implementation Artifacts to Save

For each Step 2 run, keep:
- implementation notes
- test output logs
- generated sample output
- failure notes

Suggested folders:

```text
outputs/qwen-run/
outputs/gemma-run/
```
