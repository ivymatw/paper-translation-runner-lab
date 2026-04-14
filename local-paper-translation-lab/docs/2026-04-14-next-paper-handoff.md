# Next-paper handoff — 2026-04-14

Status: ready for context reset and continuation

## What was just completed

A previously ad hoc page-by-page PDF reconstruction script was upgraded into a formal runner:
- `run_pdf2zh_by_page.py`
- wrapper entrypoint: `run_pdf2zh_by_page.sh`

The new runner now supports:
- page-level execution
- resumable runs
- page reuse
- document-level manifest
- page event log
- error log for degraded pages
- final merge into a complete mono PDF
- passthrough fallback so one bad page does not stall the whole document

## Where it lives

Project root:
- `~/obsidian/Max-Docs/llm-ccp-propaganda/`

Formal runner:
- `run_pdf2zh_by_page.py`
- `run_pdf2zh_by_page.sh`

## What has already been proven

On the Taiwan sovereignty paper:
- the old fragile workflow was repaired until a full 19-page mono PDF could be produced
- end-to-end runtime was about 9.67 hours in the experimental run
- the system can now finish a whole document by degrading locally rather than stalling globally

On the new formal runner smoke test:
- a limited page-range run completed successfully
- artifacts were written correctly:
  - `run-manifest.json`
  - `run-events.jsonl`
  - `error-log.jsonl`
  - merged mono PDF

## Immediate next task after reset

Run the next paper through the formal runner, not the old ad hoc loop.

Primary objective:
- verify that another full paper finishes without manual babysitting

Secondary objective:
- inspect `error-log.jsonl` and `run-manifest.json` to see whether degraded reasons are specific enough to guide the next repair cycle

## Required acceptance for the next paper

Minimum success:
1. whole document finishes
2. merged mono PDF exists
3. `run-manifest.json` exists
4. `error-log.jsonl` exists
5. degraded pages are explainable from logs

Nice to have:
- degraded-pass rate lower than the Taiwan sovereignty run
- fewer metadata/placeholder-related failures

## Suggested command pattern

From:
- `~/obsidian/Max-Docs/llm-ccp-propaganda`

Run:
```bash
./run_pdf2zh_by_page.sh \
  --src /absolute/path/to/next-paper.pdf \
  --out /absolute/path/to/output-dir
```

Optional bounded test before full run:
```bash
./run_pdf2zh_by_page.sh \
  --src /absolute/path/to/next-paper.pdf \
  --out /absolute/path/to/output-dir \
  --start-page 1 \
  --end-page 2
```

## What to inspect after the next run

1. `run-manifest.json`
- page counts by status
- total page runtime
- merged output path

2. `error-log.jsonl`
- dominant degraded reasons
- whether fallback was translator-level or original-page passthrough

3. representative page logs under:
- `logs/page-XX.log`

## Strategic reminder

Do not optimize first for beautiful translation.
Optimize first for:
- whole-document completion
- explicit degradation
- useful logs

Once completion becomes boring, then reduce degraded-pass rate.
