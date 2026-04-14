# Reset Plan — local-paper-translation-lab

> For Max / Steve: this is a decision memo, not an implementation diff list.

Date: 2026-04-12

## 1. What the project is actually trying to do

The repo is not trying to prove that any available model can somehow produce a lucky final Chinese paper.

The real project goal is to build a reliable, inspectable pipeline that:
1. separates source-quality problems from translation-quality problems
2. localizes failures to blocks
3. allows deterministic repair and validation
4. produces a study-ready final artifact only when upstream artifacts are trustworthy

That means the current question is not:
- "How do we salvage vnext7/vnext8 into something barely readable?"

The correct question is:
- "Which stage is currently the dominant bottleneck, and what is the smallest decision that restores architectural clarity?"

## 2. What we have learned so far

### 2.1 Good news
- The repo now has a real modular pipeline.
- Tests exist across extraction / segmentation / translation / repair / assembly.
- Front-matter rendering for study output now exists.
- Suspicious truncated translation is now detected instead of silently flowing into final output.
- Block-level debugging is possible.

### 2.2 Bad news
- The current first target paper still fails the deep-reading standard.
- Failure is not isolated to one stage.
- There are at least three different defect classes mixed together:
  1. source repair defects
  2. segmentation defects
  3. translation / repair defects
- Because multiple defect classes are mixed, late-stage patching creates misleading progress.

### 2.3 Most important insight
The current bottleneck is not primarily "study assembly formatting".
The bottleneck is upstream structural reliability.

In particular:
- some paragraphs are structurally wrong before translation
- figure / table / footnote material still contaminates prose blocks
- some translated blocks are truncated or malformed
- therefore final-output quality cannot be used as the main optimization surface yet

## 3. What is the wrong next move

Do NOT continue with any of these as the main strategy:

1. keep patching study assembly to hide upstream defects
2. keep generating new vnext final outputs and judging them by spot-reading
3. keep doing full-paper reruns without a stage-level acceptance gate
4. keep mixing local-model translation experiments with canonical production evaluation
5. keep treating this as a prose polishing problem

These all collapse architecture and make diagnosis harder.

## 4. What is the correct next move

The correct move is to switch from "output chasing" to "stage-gated acceptance".

That means the project should enter a reset phase with one question:
- can the pipeline produce a trustworthy repaired English + block structure for this paper before we care about full zh-TW quality?

If the answer is no, translation evaluation is premature.

## 5. Recommended decision

Adopt this decision immediately:

### Decision A
Freeze final-output chasing.
Treat all current `study.zh-TW.*` files as diagnostic artifacts, not candidate finals.

### Decision B
Promote `repaired English source + segmentation quality` to the next acceptance gate.

### Decision C
Use Gemini production translation only after the English-side gate passes.
Do not use local Gemma/Qwen translation results as evidence for final-pipeline quality.
They are only diagnostic or implementation-path evidence.

## 6. New working phase

### Phase R1 — Source-side acceptance reset
Goal:
Establish whether the English-side pipeline is structurally trustworthy enough for translation.

Required deliverables:
1. one accepted repaired English source artifact
2. one accepted segmented block artifact
3. one validation note describing which known defects remain and why they are acceptable

Acceptance focus:
- no obvious paragraph truncation in core prose
- no figure/table caption swallowing body prose
- no footnote contamination inside core introduction / abstract / problem-definition paragraphs unless explicitly marked
- section ordering is coherent
- references remain references
- equations / tables / figures are not silently absorbed into prose

### Phase R2 — Translation micro-evaluation
Goal:
Test the canonical Gemini path only on a small trusted slice.

Suggested slice:
- Abstract
- Introduction first 3 paragraphs
- Problem Definition 2.1 first paragraph

Purpose:
- verify whether clean English + glossary + block prompts now produce complete zh-TW blocks
- measure completeness and faithfulness before rerunning the whole paper

### Phase R3 — Whole-paper canonical run
Only do this if R1 and R2 pass.

## 7. Concrete next implementation task

The single highest-value next task is:

"Create a source-side validation workflow and acceptance checklist for repaired-English + segmentation on one paper."

This is better than another translation rerun because it decides whether the system is ready for translation at all.

## 8. Concrete files that should become canonical for the next checkpoint

Instead of asking "which final markdown is best", the next checkpoint should name these canonical artifacts:

- `outputs/work/source_repaired.hybrid.vnext2.en.md` or successor
- `outputs/work/blocks.hybrid-vnext2-en.jsonl` or successor
- `docs/source-side-acceptance-checklist.md` (new)
- `outputs/work/source-side-validation-report.md` (new)

Only after those exist and pass review should we produce a new canonical translated artifact.

## 9. Recommended success criterion for the next session

A good next session does NOT end with a prettier final zh-TW file.

A good next session ends with:
1. a clear pass/fail verdict on English-side readiness
2. explicit examples of remaining segmentation defects
3. a decision whether translation should continue
4. if yes, a small trusted-slice Gemini evaluation

## 10. Bottom line

The project has reached the point where architectural discipline matters more than another patch.

The correct next move is:
- stop optimizing final output directly
- re-center the repo on source-side acceptance
- let Max continue direct implementation instead of treating local-model coding comparison as a primary track
- only resume canonical translation after upstream structure is trustworthy

That is the highest-leverage move now.