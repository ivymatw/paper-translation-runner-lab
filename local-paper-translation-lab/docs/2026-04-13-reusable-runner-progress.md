# Reusable Runner Progress — 2026-04-13

Date: 2026-04-13

## Goal of this phase

Move the project from a single-paper lab into the foundation of a reusable everyday skill:
- give each paper its own output namespace
- add a one-command runner
- produce a study artifact that is closer to real deep reading by reattaching visual evidence from the original PDF
- validate the pipeline on a second paper

## 1. What was completed

### 1.1 Paper-specific path layer
A new path helper layer was added so outputs can be namespaced by:
- `paper_id`
- `outputs_dir`

This allows outputs such as:
- `outputs/<paper_id>/work/source_clean.md`
- `outputs/<paper_id>/work/translated_blocks.jsonl`
- `outputs/<paper_id>/<paper_id>.study.zh-TW.md`
- `outputs/<paper_id>/<paper_id>.study.zh-TW.visuals.md`

Important compatibility decision:
- legacy `outputs/work/...` defaults were kept in individual stage CLIs
- reusable pathing is activated through `--paper-id` / `--outputs-dir`

This avoided breaking the current benchmark baseline and existing tests.

### 1.2 One-command runner
A real orchestration entrypoint now exists:
- `src/run_paper.py`

Current canonical path inside the runner:
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
11. visuals attachment

The runner now emits:
- study markdown
- visuals-enhanced study markdown
- archival markdown
- `run-summary.json`

### 1.3 Visual study output
A new helper was added:
- `src/attach_pdf_visuals.py`

Purpose:
- attach cropped figure/table visuals from the original PDF back into the study markdown

Important correction during implementation:
- the first version inserted whole PDF pages, which was not acceptable
- this was corrected to use cropped figure/table regions instead

For the benchmark paper, explicit crop overrides were added because the PDF layout mixes captions, tables, and body text in ways that defeat naive heuristics.

### 1.4 Benchmark-paper outcome
The original benchmark paper now has a more reviewable visuals-enhanced study artifact:
- `outputs/2511.23174_Safety_Agents_or_Propaganda_Engine.study.zh-TW.restart2.assembled.v2.visuals.md`

This is materially better than the plain study markdown because the reader can now inspect the original figure/table visuals inline.

## 2. Second-paper validation

Second validation paper:
- `2602.06371_Bilingual_Bias_in_LLMs_Taiwan_Sovereignty.pdf`

### 2.1 What succeeded
Source-side pipeline completed successfully on the new paper:
- `work/source_clean.md`
- `work/source_repaired.en.md`
- `work/glossary.json`
- `work/blocks.clean.jsonl`

This is the first real validation that the reusable runner structure is not confined to the benchmark paper only.

### 2.2 What failed
The end-to-end translated output did not complete successfully.

Observed blockers:
1. `extract.py` stalled on this PDF
2. translation backend availability was unstable
   - Gemini returned repeated HTTP 503 / high demand failures
   - OpenAI fallback probe returned HTTP 429 / rate-limit failure

### 2.3 What was changed because of this
The runner was upgraded so that:
- if extraction fails
- and a sibling markdown file exists (`<paper_id>.md`)
- it automatically falls back to that source candidate instead of aborting the whole run

The runner now records in `run-summary.json`:
- `extraction_error`
- `used_markitdown_fallback`

This makes source-side runs much more robust for real papers where PDF extraction may hang or degrade.

### 2.4 Current status of the second paper
A run note was written to preserve the exact state:
- `outputs/2602.06371_Bilingual_Bias_in_LLMs_Taiwan_Sovereignty/run-note.md`

Important conclusion:
- the reusable pipeline structure is now good enough to run source-side on new papers
- the dominant remaining risk is no longer repo orchestration
- it is provider-side translation availability / quota stability

## 3. Testing status

The test suite remained green throughout this phase.

Current status after this work:
- 66 tests passed

New test coverage now includes:
- paper-path namespacing
- runner orchestration contract
- visuals output path generation
- extraction fallback to sibling markdown when extraction fails

## 4. Practical interpretation

The project is no longer just “a benchmark-paper experiment.”

It is now:
- a reusable paper-runner foundation
- with namespaced outputs
- with one-command orchestration
- with visuals-enhanced study output
- and with extraction fallback logic for more robust operation on new papers

But it is not yet a fully dependable everyday skill because:
- translation still depends on external provider availability
- provider failure handling is not yet fully formalized into a deferred/partial-success mode
- visuals cropping is partially heuristic and partially benchmark-specific override logic

## 5. Follow-up update from 2026-04-14

A new branch of work on PDF reconstruction changed the practical priority.

New top priority:
- a whole document must finish without manual babysitting
- bad blocks must degrade locally instead of stalling the entire run
- every degraded decision must be logged for later repair

Observed result on the Taiwan sovereignty paper:
- a full 19-page mono PDF reconstruction was completed through page-level execution plus automatic degraded fallback
- this is an important systems milestone even though the output is not yet production quality

Implication:
- for reconstruction-oriented paths, completion robustness now comes before per-block elegance
- the next formal step is not more ad hoc patching
- it is to turn the current adaptive execution behavior into a real runner with a run manifest and error log

Relevant design note:
- `docs/2026-04-14-pdf2zh-autoadaptive-full-document-runner.md`
