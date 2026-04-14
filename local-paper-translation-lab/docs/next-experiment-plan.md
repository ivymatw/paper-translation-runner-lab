# Next Experiment Plan

## Goal
Use the new completion-oriented page-level runner on additional papers and measure whether it can finish whole documents reliably while producing actionable logs for later quality repair.

## Immediate next run
Run the next paper through the formal runner, not the old ad hoc shell loop.

Primary questions:
1. does the whole document finish without manual intervention?
2. how many pages are `pass` vs `degraded_pass` vs passthrough fallback?
3. are the error logs specific enough to guide the next repair cycle?

## Experiment A — Multi-paper completion test
- input scope: whole paper
- runner: `run_pdf2zh_by_page.py`
- objective: verify full-document completion on at least one additional paper after the Taiwan sovereignty paper
- required artifacts:
  - `run-manifest.json`
  - `run-events.jsonl`
  - `error-log.jsonl`
  - merged mono PDF

## Experiment B — Degradation distribution review
- inspect degraded pages after the run
- bucket the reasons:
  - placeholder issues
  - suspicious English leftovers
  - metadata residue
  - citation / URL / name preservation issues
- objective: decide which failure mode is the next highest-leverage fix

## Experiment C — Cache/versioning hardening
- add explicit version markers for prompt / sanitize / validator / fallback policy
- objective: prevent old low-quality cache entries from contaminating reruns

## Experiment D — Quality repair after completion
- only after the whole-document run completes, choose the worst degraded pages and improve them
- objective: keep completion robustness as the invariant while iteratively lowering degraded-pass rate

## Decision Rule
The branch is moving in the right direction only if:
- whole-document completion becomes boring
- degraded pages become countable and explainable
- later fixes reduce degraded-pass rate without reintroducing full-run stalls
