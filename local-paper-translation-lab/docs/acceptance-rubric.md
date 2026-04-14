# Acceptance Rubric

Status: revised v0.2
Author: Max
Date: 2026-04-12

## 1. Purpose

Used to evaluate the pipeline at the current project stage.

This rubric is no longer for comparing Step 2A / 2B local-model implementation runs.
It is now for judging whether the translation pipeline is trustworthy enough to advance from one stage gate to the next, and eventually whether the final paper output is usable for deep reading.

## 2. Review principle

A run is not accepted just because:
- code exists
- unit tests pass
- output files exist

A run is accepted only if:
1. the relevant stage gate passed
2. known failure modes were checked
3. defects are localized and documented
4. the output is trustworthy enough for the next stage

## 3. Score dimensions

Each review is scored on 5 dimensions, 1-5 each.

### A. Stage Reliability
- 1 = stage output is structurally untrustworthy
- 3 = stage mostly works but has important known defects
- 5 = stage output is reliable enough to serve as canonical input to the next stage

### B. Test Reliability
- 1 = tests missing or misleading
- 3 = useful tests exist but do not guard the key failure modes
- 5 = unit tests plus stage-gate checks reliably catch the important failure modes

### C. Structural Preservation
- 1 = article structure broken
- 3 = major structure mostly preserved but with damage
- 5 = title, sections, figures, tables, equations, and references remain usable in the intended artifact

### D. Translation Completeness and Faithfulness
- 1 = badly fragmented, truncated, or unreliable
- 3 = understandable but still rough and needing source cross-checks
- 5 = complete and faithful enough for real reading use

### E. Deep-Reading Fitness
- 1 = not suitable for study
- 3 = usable only with heavy cross-checking
- 5 = suitable for serious reading and note-taking

## 4. Mandatory reviewer notes

For every review, Max must record:
- strongest aspect
- weakest aspect
- top 3 failure modes
- which stage is the dominant bottleneck
- whether the next step is:
  1. source-side fix
  2. segmentation fix
  3. translation/repair fix
  4. assembly fix
  5. rerun from last good stage

## 5. Decision outcomes

### Pass
- stage or final artifact is acceptable for current purpose

### Pass with revisions
- usable, but specific modules need targeted improvement before the next full run

### Rework required
- output failed the current stage gate and should not be treated as trustworthy input downstream

## 6. Iteration rule

If a run fails, do not restart the entire project blindly.

Instead choose one:
1. revise tests to cover the real failure mode
2. revise one module
3. rerun from the last good stage
4. tighten the acceptance checklist before rerunning

## 7. Current emphasis

At the current project stage, the highest-weight dimensions are:
1. Stage Reliability
2. Test Reliability
3. Structural Preservation

Reason:
A pretty final document is meaningless if repaired English, segmentation, or translated blocks are still structurally untrustworthy.
