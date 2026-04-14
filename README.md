# paper-translation-runner-lab

Completion-first academic paper translation and PDF reconstruction.

This repo packages the system, docs, and validation artifacts behind a practical question:

Can a full academic paper finish end-to-end without manual babysitting, while leaving behind enough structure and logs to improve the system after each run?

Short answer: yes.

## Current status

Operational beta.

What is already true:
- five-paper validation completed
- zero hard-fail documents
- zero source-page passthrough documents
- later papers reached clean full-pass runs
- the remaining problems are now mostly output-polish issues, not workflow blockers

Validation headline:
- Paper 1: 6 pass / 9 degraded / 0 hard fail
- Paper 2: 19 pass / 0 degraded / 0 hard fail
- Paper 3: 21 pass / 0 degraded / 0 hard fail
- Paper 4: 29 pass / 1 degraded / 0 hard fail on first full run; remaining edge case diagnosed and patched
- Paper 5: 30 pass / 1 degraded / 0 hard fail on first full run; remaining edge case diagnosed and patched

See:
- `docs/development-history.md`
- `docs/five-paper-validation.md`
- `docs/known-issues.md`
- `CHANGELOG.md`
- `ROADMAP.md`

## What is in this repo

Two connected workstreams are preserved here.

### 1. Canonical markdown-oriented pipeline
Location:
- `local-paper-translation-lab/`

Purpose:
- extract a cleaner English source from academic PDFs
- repair source-side structure
- segment and translate into Traditional Chinese markdown
- assemble study-oriented outputs

This is the path for higher-quality reading artifacts.

### 2. Completion-first PDF reconstruction runner
Entry points:
- `run_pdf2zh_by_page.py`
- `run_pdf2zh_by_page.sh`

Purpose:
- run page by page
- resume safely
- degrade locally instead of stalling globally
- log what happened in machine-readable form
- always produce a merged mono PDF if the document can be assembled

This is the path for robustness-first whole-document completion.

## Why this repo exists

The problem is not just translation quality.

The real systems problem is:
- can one bad page stop a whole paper?
- can failures be localized instead of becoming all-or-nothing?
- can edge cases be diagnosed from manifests and logs rather than guesswork?
- can repeated paper runs steadily improve the system?

This repo exists to answer those questions with working code and validation artifacts.

## Main design principles

- completion first
- local degradation over global stall
- explicit manifests and logs over hidden state
- stage-gated thinking for upstream quality problems
- cache-aware reruns when behavior changes materially
- patch root causes, not just final artifacts

## Suggested entrypoints

### A. Completion-first PDF reconstruction

```bash
./run_pdf2zh_by_page.sh \
  --src /absolute/path/to/paper.pdf \
  --out /absolute/path/to/output-dir
```

Expected artifacts:
- `run-manifest.json`
- `run-events.jsonl`
- `error-log.jsonl` when degraded pages exist
- per-page outputs under `pages/page-XX/`
- final merged mono PDF

### B. Canonical markdown-oriented path

```bash
cd local-paper-translation-lab
python3 src/run_paper.py /absolute/path/to/paper.pdf --paper-id my-paper
```

Expected artifacts include:
- clean English source
- glossary
- segmented blocks
- translated / repaired blocks
- archival markdown
- study markdown
- visuals-enhanced study markdown

## Repo layout

```text
paper-translation-runner-lab/
├── README.md
├── CHANGELOG.md
├── ROADMAP.md
├── docs/
├── local-paper-translation-lab/
├── papers/
├── run_pdf2zh_by_page.py
├── run_pdf2zh_by_page.sh
├── tests/
└── validation/
```

## Validation artifacts included here

Included:
- compact run manifests for the five full-document validation runs
- degraded/error logs when present
- the regression tests added during debugging
- development notes and findings docs

Deliberately excluded:
- large generated PDF outputs
- raw caches
- heavyweight per-run work directories
- source PDFs themselves

## Key engineering findings from the validation loop

The biggest gains did not come from one perfect prompt.
They came from fixing failure families:
- suspicious-English false positives on reference-heavy pages
- placeholder formatting variants like `{ v0 }`
- reference placeholders naturally expanded into full venue names
- placeholder reordering under valid Chinese syntax
- role-adjacent placeholder dropping during refusal outputs
- cache confusion during reruns

Once those were isolated and patched, later papers became dramatically cleaner.

## Known remaining polish targets

These are not workflow blockers anymore:
- reference-heavy page formatting still mixes untranslated venue fragments in some outputs
- shell wrapper exits can show non-fatal `HISTTIMEFORMAT` noise in background runs
- runtime comparisons still require cache discipline to be meaningful

## License

MIT
