# PDF reconstruction runner redesign — 2026-04-14

Date: 2026-04-14
Status: adopted for the current diagnostic PDF reconstruction path

## Goal

Redefine the immediate objective for the `pdf2zh + local model` branch.

The first goal is no longer:
- perfect per-block translation quality

The first goal is now:
- a whole document must run to completion
- adaptation to bad blocks must be automatic
- the run must leave behind enough structured evidence to guide later fixes

In short:
- completion first
- local degradation second
- post-run repairability third

## Why this redesign was necessary

During the MiniMax-based reconstruction experiments on:
- `2602.06371_Bilingual_Bias_in_LLMs_Taiwan_Sovereignty.pdf`

we observed repeated failure modes that were qualitatively different:

1. reasoning leakage entered the translated PDF
2. `pdf2zh` global cache preserved dirty outputs across reruns
3. ordinary words such as `worse`, `language bias`, `Abstract`, `Keywords`, and `Introduction` were incorrectly treated as placeholder variables and later reinserted as English
4. mono output still carried visible metadata-like residuals such as the vertical arXiv/date label
5. strict validator rules caused the full-document run to stall forever on single problematic pages
6. after one failure mode was fixed, a new one appeared on later pages (`dangling_placeholder`, then `suspicious_english: temperature,top-p`, etc.)

This means the old execution philosophy was wrong.

The workflow cannot be:
- strict validation or death

The workflow must be:
- strict when possible
- degraded but complete when necessary
- always logged

## New execution policy

### 1. Page-level orchestration is the default

For the PDF reconstruction branch, full-document execution should be page-level by default.

Why:
- page-level progress is visible
- retries are bounded
- one bad page does not invalidate already-completed pages
- reruns can reuse good pages
- final merge becomes deterministic

### 2. Validation is no longer a pure stop signal

Each translated unit should end in one of three states:
- `pass`
- `degraded_pass`
- `failed_hard`

Definitions:
- `pass`: translated and validated normally
- `degraded_pass`: validator failed, but a fallback output was emitted so assembly can continue
- `failed_hard`: output structure would be corrupted if we continued

Only `failed_hard` should stop the run.

### 3. Fallback is an official mechanism, not an embarrassment

Fallback must be treated as a first-class adaptation mechanism.

Examples:
- source-text passthrough for formula-heavy segments
- sanitized-but-not-perfect output for segments with suspicious English leftovers
- placeholder-preserving degraded output when the main translation path remains unstable

The key idea:
- one bad block should lower quality locally, not kill the document globally

### 4. Error logging is mandatory

Every degraded decision must be written to a structured artifact.

Minimum fields:
- page index
- block or segment identifier
- source snippet
- final emitted snippet
- validator reason
- retry count
- fallback strategy
- status (`pass` / `degraded_pass` / `failed_hard`)

Without this, the run may complete, but the system does not learn.

## What changed in this round

### A. Translator middleware

Observed fixes:
- sanitize reasoning leakage before caching
- validate cache hits before reusing them
- retry bad outputs
- if retries still fail, emit a fallback result instead of stalling the run

### B. Converter placeholder handling

Observed fixes:
- stop treating some ordinary ASCII text spans as formula placeholders
- preserve true math placeholders, but route normal title/heading/italic words back into normal text flow
- drop metadata-like arXiv/date vertical residuals rather than preserving them in mono output

### C. Whole-document execution strategy

Observed fixes:
- replace one-shot whole-document execution with page-by-page execution plus merge
- allow reuse of already-finished pages
- continue through pages even when some segments fall back to degraded output

## What still needs to be formalized

The current implementation proved the direction is correct, but it is still too ad hoc.

What should become formal artifacts:

1. a real page-level runner
- stable CLI
- resumable state
- page manifest
- final merge step

2. a structured run manifest
- one document-level JSON file
- one page-level JSONL or JSON report
- aggregate counts of `pass`, `degraded_pass`, `failed_hard`

3. validator versioning in cache keys
- prompt version
- sanitize version
- validator version
- fallback version

Without this, old low-quality cache entries will continue to be dangerous.

## Acceptance target going forward

For this branch, the next acceptance target is:

1. run several additional PDFs end-to-end
2. finish each without manual intervention
3. produce a machine-readable error log for every run
4. compare the distribution of degraded pages/blocks across papers
5. reduce the degraded-pass rate over time without losing completion robustness

The branch should only be considered stable when:
- multiple papers run end-to-end
- completion is boring
- degraded pages are rare
- error logs are explicit enough to guide the next repair cycle

## Final design judgment

The breakthrough of this round was not “MiniMax translates beautifully.”

The breakthrough was:
- a previously fragile PDF reconstruction workflow was converted into a completion-oriented adaptive runner
- local failures are now allowed to degrade gracefully instead of stalling the document forever

That is the right systems direction.

Quality improvement remains necessary.
But from this point onward, quality should be improved on top of a runner that can actually finish.
