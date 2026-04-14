# Restart Execution Plan

Date: 2026-04-12
Target paper: `2511.23174_Safety_Agents_or_Propaganda_Engine.pdf`

## Goal

Restart the pipeline from the earliest stage, validating each stage before advancing.

## Rule

Do not trust any old artifact by default.
Old artifacts may be used as references for comparison only.

## Execution order

1. Extraction
2. Source normalization
3. English repair
4. Glossary extraction
5. Segmentation
6. Trusted-slice translation
7. Suspicious-block repair
8. Assembly / study assembly
9. Whole-paper canonical run

## Stage policy

For each stage:
1. run stage code
2. run unit tests relevant to the codebase
3. run stage-gate checks from `docs/test-plan.md`
4. record a short validation note
5. only then advance

## Immediate stop conditions

Stop and discuss if any of these occur:
- missing major sections after extraction or normalization
- footnote/metadata contamination in core prose after English repair
- caption/body boundary failure in segmentation
- truncated prose in trusted-slice translation
- repair fails to fix or clearly isolate bad blocks
- assembly masks upstream defects

## Fresh artifact naming

New restart artifacts should use a clean suffix rather than mutating old "vnext" chains where possible.
Recommended pattern:
- `source_extracted.restart1.md`
- `source_clean.restart1.md`
- `source_repaired.restart1.en.md`
- `glossary.restart1.json`
- `blocks.restart1.jsonl`
- `translated_blocks.restart1.jsonl`
- `translated_blocks.repaired.restart1.jsonl`

## Current plan for this session

Start with:
- extraction rerun
- extraction gate review
- if pass, continue to source normalization
- if pass, continue to English repair
- stop immediately if any gate fails
