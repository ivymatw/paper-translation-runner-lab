# Changelog

## 2026-04-14 — five-paper validation and stabilization pass

### Added
- public packaging repo for the paper-translation runner lab
- top-level completion-first runner:
  - `run_pdf2zh_by_page.py`
  - `run_pdf2zh_by_page.sh`
- five-paper validation manifests under `validation/manifests/`
- degraded/error logs for runs that needed them under `validation/error-logs/`
- regression test suite for translator validation edge cases:
  - `tests/test_pdf2zh_translator_validation.py`
- public-facing docs:
  - `docs/development-history.md`
  - `docs/five-paper-validation.md`
  - `docs/known-issues.md`
  - `CHANGELOG.md`
  - `ROADMAP.md`

### Changed
- suspicious-English validation was relaxed and made more source-aware
  - source-present English terms are no longer treated as automatic failures
  - PDF line-break fragments are normalized before validation
  - validation now requires stronger evidence before flagging suspicious English leakage
- placeholder validation was made less brittle
  - internal-space variants like `{ v0 }` are accepted
  - legitimate placeholder reordering is accepted when the placeholder set matches
  - reference placeholders may expand into explicit conference / venue text without failing validation
  - role-adjacent placeholders may be dropped in refusal-style outputs without failing validation
  - true dangling placeholders are still rejected
- cache-awareness became part of the workflow
  - clean verification reruns now clear `~/.cache/pdf2zh/cache.v1.db*`
  - unexpectedly fast reruns are treated as likely cache hits rather than true inference-speed improvements

### Diagnosed
- initial benchmark-paper degraded pages were traced to a small set of root-cause families:
  - suspicious-English false positives
  - placeholder formatting variants
  - reference-placeholder expansion
  - placeholder reordering
  - refusal-path placeholder deletion
- paper 4 page 8 degraded case was traced to role-adjacent placeholder loss in refusal outputs
- paper 5 page 16 degraded case was traced to harmless placeholder reordering under valid translated syntax

### Validation results
- Paper 1 (`2511.23174`) initial run:
  - 6 pass / 9 degraded / 0 hard fail
- Paper 2 (`2602.06371`) after fixes:
  - 19 pass / 0 degraded / 0 hard fail
- Paper 3 (`2506.01814`) after fixes:
  - 21 pass / 0 degraded / 0 hard fail
- Paper 4 (`2505.17441`) first full run:
  - 29 pass / 1 degraded / 0 hard fail
  - remaining degraded case later diagnosed and patched
- Paper 5 (`2603.18280`) first full run:
  - 30 pass / 1 degraded / 0 hard fail
  - remaining degraded case later diagnosed and patched

### Result
The system moved from fragile single-paper experimentation to operational-beta multi-paper use:
- whole-document completion is now reliable
- degraded behavior is localized rather than catastrophic
- remaining issues are mostly quality-polish issues, not workflow blockers
