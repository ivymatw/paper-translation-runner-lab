# local-paper-translation-lab

A repo for designing, implementing, and evaluating a local-LLM workflow that first extracts a clean English source from academic PDFs and then translates it into high-quality Traditional Chinese Markdown for deep reading.

## Goal

Build a paper translation system that:
- takes a standard academic PDF as input
- first produces a clean English source artifact
- then outputs a Traditional Chinese `.md` file suitable for deep reading in Obsidian
- preserves article structure and reading flow
- handles figures, tables, and equations in a readable way
- is implementable by local models with explicit specs and modular steps

## Primary Research Goal

This repo is now primarily about making the paper-translation pipeline actually work end-to-end on full documents without manual babysitting.

Current top priority:
- a complete document run must finish instead of stalling on one bad block
- mid-run adaptation must be automatic rather than requiring manual intervention
- failures must be localized, logged, and reviewable after the run
- the pipeline should prefer degraded-but-complete output over hanging forever
- after several papers have been run this way, the system should become a stable everyday workflow

Important updated decisions:
- the local-LLM coding comparison is no longer the primary objective
- Max will handle the implementation directly when needed
- the canonical translation engine for production-quality output is Gemini 2.5 Flash
- local Qwen/Gemma/MiniMax runs are now diagnostic and systems-learning paths, not the canonical production path
- the canonical production path is still English repair / normalization + terminology extraction + Gemini first-pass translation + suspicious-block repair + study-oriented assembly
- for PDF reconstruction experiments, the first acceptance criterion is now completion robustness, not per-block elegance

## Workflow

### Step 1 — Design and implementation by Max
Max now owns both:
- system design and module breakdown
- implementation and debugging of the pipeline
- test design and validation criteria
- output review and iteration

### Step 2 — Stage-gated validation
The pipeline should now be advanced by acceptance gates rather than by model-comparison runs:
- source-side acceptance: repaired English + segmentation quality
- translation micro-evaluation on trusted slices
- whole-paper canonical run only after upstream stages pass

### Step 3 — Final acceptance
Max reviews:
- structural reliability of the English-side artifacts
- test results
- translation completeness and faithfulness
- reading usability of the translated paper

If needed, the pipeline is revised and rerun from the failing stage rather than treated as a whole-document black box.

## Evaluation Strategy

Current priority:
- improve source-side structural reliability
- improve canonical Gemini translation quality
- localize failures to individual stages and blocks
- reach a trustworthy deep-reading output for the target paper

## Test Paper

The first paper used for development and evaluation is:

- `2511.23174_Safety_Agents_or_Propaganda_Engine.pdf`

Reason:
- standard academic paper format
- includes figures, tables, and equations
- suitable for testing structure preservation and deep-reading usability

## Expected Output

Primary output formats:
- clean English Markdown (`.en-clean.md`)
- archival Traditional Chinese Markdown (`.zh-TW.md`)
- study-oriented Traditional Chinese Markdown (`.study.zh-TW.md`)

The output should prioritize:
1. readability for deep study
2. preservation of article logic and section structure
3. understandable handling of figures, tables, and equations
4. clear separation between source-quality problems and translation-quality problems
5. block-level repairability rather than full rerun whenever a translation block is suspicious
6. glossary-guided term consistency after the English source has been repaired

## One-command runner

The repo now has a single-command orchestration entrypoint:

```bash
python3 src/run_paper.py /path/to/paper.pdf --paper-id my-paper
```

By default this now produces both:
- a normal study markdown
- a visuals-enhanced study markdown with cropped figure/table regions pulled from the original PDF

This runs the canonical path:
1. extraction
2. source normalization
3. optional layout-region extraction
4. English repair
5. glossary extraction
6. segmentation
7. first-pass translation
8. suspicious-block repair
9. archival assembly
10. study assembly

Useful options:

```bash
python3 src/run_paper.py /path/to/paper.pdf \
  --paper-id my-paper \
  --outputs-dir outputs \
  --english-repair-mode heuristic \
  --translation-model gemini-2.5-flash \
  --translation-backend gemini
```

Optional layout artifacts:

```bash
python3 src/run_paper.py /path/to/paper.pdf \
  --paper-id my-paper \
  --with-layout-regions \
  --render-layout-source
```

The namespaced outputs for a paper now go under:

```text
outputs/<paper_id>/
├── <paper_id>.zh-TW.md
├── <paper_id>.study.zh-TW.md
├── <paper_id>.study.zh-TW.visuals.md
├── assets/
│   └── <paper_id>.study.zh-TW.visuals/
├── run-summary.json
└── work/
    ├── source_extracted.md
    ├── source_clean.md
    ├── source_repaired.en.md
    ├── glossary.json
    ├── blocks.clean.jsonl
    ├── translated_blocks.jsonl
    ├── translated_blocks.repaired.gemini.jsonl
    ├── layout_regions.jsonl                 # optional
    └── source_layout_clean.md               # optional
```

Notes:
- legacy `outputs/work/...` defaults are still preserved for backward compatibility in individual stage CLIs
- the reusable path layer is activated by `--paper-id` / `--outputs-dir`
- the runner writes `run-summary.json` so later skills can consume stable artifact locations

## Planned Repo Structure

```text
local-paper-translation-lab/
├── README.md
├── docs/
│   ├── spec.md
│   ├── system-design.md
│   ├── implementation-plan.md
│   ├── test-plan.md
│   └── acceptance-rubric.md
├── src/
├── tests/
├── samples/
│   └── 2511.23174_Safety_Agents_or_Propaganda_Engine.pdf
└── outputs/
```

## Current Status

- [x] Repo initialized
- [x] Core pipeline prototyped and partially implemented by Max
- [x] Reusable paper-specific path layer added (`paper_id + outputs_dir`)
- [x] One-command runner added (`src/run_paper.py`)
- [x] Visuals-enhanced study output added (`.study.zh-TW.visuals.md` with cropped figure/table regions)
- [x] Runner now falls back to sibling markdown when PDF extraction fails and such a fallback exists
- [x] The original benchmark paper now has a reviewable visuals-enhanced study artifact
- [x] A second paper (`2602.06371_Bilingual_Bias_in_LLMs_Taiwan_Sovereignty.pdf`) validated the source-side reusable path on a new paper
- [x] A diagnostic PDF reconstruction path now exists that can finish a whole 19-page document via page-level execution plus automatic degradation fallback
- [ ] Source-side acceptance gate defined and reviewed as a reusable standard, not just for the benchmark paper
- [ ] Translation provider-failure strategy finalized (Gemini 503 / OpenAI 429 handling, deferred/partial mode)
- [ ] PDF reconstruction runner formalized so completion, fallback, and error logging are first-class artifacts rather than ad hoc patches
- [ ] Multi-paper validation completed on several additional PDFs so the workflow can be considered stable for routine use
- [ ] Whole-paper canonical run accepted as a stable everyday workflow
