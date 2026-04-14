# Development History

## Phase 0 — single-paper debugging

The project began as a local-paper translation experiment focused on one benchmark paper:
- `2511.23174_Safety_Agents_or_Propaganda_Engine.pdf`

Early work revealed several recurring failure classes:
- source extraction noise
- figure/caption/body boundary contamination
- metadata splitting core prose
- placeholder residue
- provider instability
- final-artifact patching that hid upstream defects instead of fixing them

That led to a stage-gated restart philosophy:
- validate extraction
- validate normalization
- validate English repair
- validate segmentation
- validate trusted-slice translation
- only then scale to the whole paper

## Phase 1 — reusable canonical runner

The markdown-oriented lab evolved into a reusable pipeline with:
- paper-specific pathing
- one-command orchestration
- glossary extraction
- suspicious-block repair
- study/archival assembly
- visuals-enhanced study output

Key files:
- `local-paper-translation-lab/src/run_paper.py`
- `local-paper-translation-lab/src/attach_pdf_visuals.py`
- `local-paper-translation-lab/src/paper_paths.py`

## Phase 2 — completion-first PDF runner

A second branch of work redefined the immediate priority for PDF reconstruction:
- whole-document completion beats per-block elegance
- one bad page must not stall the document
- degraded decisions must be logged

This led to:
- `run_pdf2zh_by_page.py`
- `run_pdf2zh_by_page.sh`

The runner added:
- page-level execution
- resume/reuse behavior
- document manifest
- event log
- error log
- final merged mono PDF
- explicit degraded fallback

## Phase 3 — five-paper validation loop

The system was then pushed through a five-paper validation cycle.

Observed first-order bugs:
- suspicious-English validator too aggressive on reference pages
- placeholder validation too strict for harmless placeholder formatting variants
- reference placeholders being naturally expanded by the model but rejected as mismatches
- placeholder order changing under valid Chinese syntax
- role-adjacent placeholders being dropped during legitimate refusal outputs
- cache hits misleading runtime comparisons

## Phase 4 — root-cause fixes

The following fixes were implemented after targeted diagnostics:

### Suspicious-English validation
- allow source-present English terms
- normalize PDF line-break fragments before validation
- reduce false positives on citation/reference-heavy pages
- require stronger suspicious-English evidence before failing a block

### Placeholder validation
- allow internal-space variants like `{ v0 }`
- detect true dangling placeholders by masking valid placeholders first
- allow placeholder reordering when the placeholder set matches
- allow reference-placeholder expansion into explicit conference/association text
- allow role-adjacent placeholder removal in refusal-style outputs

### Cache discipline
- treat unexpectedly fast reruns as probable cache hits
- clear `~/.cache/pdf2zh/cache.v1.db*` before clean verification reruns when validation logic changes materially

## Resulting transition

The project moved from:
- fragile experimentation with many degraded pages

to:
- operational-beta multi-paper completion with only isolated edge cases remaining

The decisive shift was not just better prompts.
It was:
- explicit manifests
- targeted diagnostics
- bounded reruns
- validator redesign
- placeholder policy refinement
