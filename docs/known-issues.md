# Known Issues and Next Polishing Targets

## Non-blocking issues

These are no longer workflow blockers, but still matter for output quality.

Important status update:
- the known five-paper validation placeholder blockers were diagnosed and patched
- remaining work is now mostly output-polish work, not completion-stability work

### 1. Reference-heavy page formatting
Common symptoms:
- proceedings / association names partially left in English
- line-break scars inside titles and venues
- mixed translated and untranslated citation fragments

Impact:
- reading quality issue
- not a completion or correctness blocker for the current runner

### 2. Wrapper-shell exit noise
Background runs end with a shell-side message like:
- `bash: HISTTIMEFORMAT: unbound variable`

Impact:
- non-fatal
- final output artifacts still exist
- easy to misread as a pipeline failure if not understood

### 3. Cache contamination risk in comparative reruns
The global cache can make reruns look much faster than they really are.

Impact:
- benchmarking confusion
- misleading confidence in speed improvements

Mitigation:
- clear `~/.cache/pdf2zh/cache.v1.db*` before clean verification reruns

## Suggested next polishing tasks

1. Reference formatting cleanup heuristics
- post-process reference-heavy pages more gracefully
- reduce broken conference-title fragments

2. Release-note / packaging cleanup
- make repository publishing cleaner
- document operational commands and expected artifacts

3. Optional sixth-paper validation
- useful for confidence
- no longer required to prove basic operational viability
