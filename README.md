# paper-translation-runner-lab

A completion-first research repo for academic-paper translation and PDF reconstruction.

This repo captures two connected workstreams:

1. `local-paper-translation-lab/`
   - the canonical markdown-oriented pipeline
   - extraction -> normalization -> English repair -> glossary -> segmentation -> translation -> repair -> assembly
   - intended for higher-quality study outputs

2. `run_pdf2zh_by_page.py`
   - the completion-first PDF reconstruction runner
   - page-level orchestration, resumable execution, degraded fallback, manifest/event/error logging
   - intended for robust whole-document completion without manual babysitting

## Why this repo exists

The main engineering question was not just "can a paper be translated?"

It was:
- can a full academic paper finish end-to-end without stalling?
- can failures degrade locally instead of killing the whole run?
- can logs and manifests make the next repair cycle obvious?
- can the workflow become stable enough for repeated multi-paper use?

## What happened in this development cycle

We ran a five-paper validation loop and patched the system based on real failure modes.

High-level result:
- 5 papers completed end-to-end
- 0 hard-fail documents
- 0 source-page passthrough documents
- later papers reached near-clean or fully clean pass rates
- remaining issues were narrowed from broad instability to a small number of placeholder/reference edge cases

See:
- `docs/development-history.md`
- `docs/five-paper-validation.md`
- `docs/known-issues.md`

## Main components

Top-level runner:
- `run_pdf2zh_by_page.py`
- `run_pdf2zh_by_page.sh`

Canonical lab project:
- `local-paper-translation-lab/src/`
- `local-paper-translation-lab/tests/`
- `local-paper-translation-lab/docs/`

Validation artifacts included here:
- `validation/manifests/`
- `validation/error-logs/`

## Design principles

- completion first
- local degradation over global stall
- every degraded decision should be loggable
- validate upstream boundaries before polishing downstream artifacts
- cache-aware reruns when behavior changes materially

## Current status

This repo is now in an operational beta state:
- usable for repeated multi-paper runs
- still worth polishing on reference-heavy formatting and a few edge-case placeholder patterns

## Suggested entrypoints

PDF reconstruction / completion-first path:

```bash
./run_pdf2zh_by_page.sh \
  --src /absolute/path/to/paper.pdf \
  --out /absolute/path/to/output-dir
```

Canonical markdown-oriented path:

```bash
cd local-paper-translation-lab
python3 src/run_paper.py /absolute/path/to/paper.pdf --paper-id my-paper
```
