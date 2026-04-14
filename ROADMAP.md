# Roadmap

## Status

The runner is now operational beta.

That means:
- multi-paper completion is proven
- the main structural placeholder and validator failure families have been patched
- the system is usable now
- the next work is about making it cleaner, easier to operate, and easier to trust

## Priority 1 — reference-heavy formatting polish

Goal:
- improve reading quality on bibliography / citation-heavy pages without regressing completion robustness

Targets:
- reduce broken conference-title fragments
- reduce mixed translated/untranslated venue strings
- improve line-break scar cleanup in reference entries
- avoid introducing new false-positive validator failures while polishing these pages

Good next steps:
- add post-processing heuristics specifically for reference-heavy blocks/pages
- build a small regression set from benchmark-paper pages 10-13 and similar pages in later papers
- treat this as quality polish, not as a reason to block whole-document completion

## Priority 2 — wrapper-shell cleanup

Goal:
- remove non-fatal but confusing shell-noise at the end of background runs

Problem:
- background sessions currently end with `bash: HISTTIMEFORMAT: unbound variable`
- output artifacts are still valid, but the exit code is visually misleading

Desired outcome:
- background completion looks clean and unambiguous
- shell wrapper status matches real pipeline success

## Priority 3 — publish a more formal run schema

Goal:
- make artifacts easier to consume programmatically and easier to compare across runs

Possible work:
- version the run-manifest schema explicitly
- normalize error-log entry shape
- record validator/fallback/cache-policy versions in manifests
- attach a compact run-summary markdown file per run

## Priority 4 — optional sixth-paper / stress validation

This is optional, not required to prove baseline viability.

Possible uses:
- try a longer or more reference-heavy paper
- validate against a more layout-hostile paper
- confirm that the most recent placeholder fixes generalize

## Priority 5 — release engineering

Goal:
- make the repo easier for another operator to pick up and use

Possible work:
- add a reproducible environment/setup guide
- add a sample command cookbook
- add a short architecture diagram
- document what is canonical versus diagnostic in one place

## Not the immediate priority

The following are valuable, but no longer urgent blockers:
- another local-model bakeoff
- chasing tiny runtime improvements without cache control
- polishing every reference page before the runner is packaged cleanly

## Success condition for the next cycle

The next cycle should end with:
- clean wrapper behavior
- reference-heavy page readability improved
- manifests/logs stable enough for routine use and external sharing
