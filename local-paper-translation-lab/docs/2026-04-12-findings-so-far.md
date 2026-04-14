# Findings So Far — restart1 to restart2

Date: 2026-04-12
Target paper: `2511.23174_Safety_Agents_or_Propaganda_Engine.pdf`

## 1. Project-direction findings

1. The project should no longer be framed as a local-LLM coding comparison.
2. The primary goal is now to make the paper-translation pipeline actually work for deep reading.
3. Max should implement and debug the system directly.
4. Local Qwen/Gemma runs are diagnostic only, not the main production path.
5. Gemini 2.5 Flash is the canonical translation backend for production-quality output.

## 2. Process findings

1. A passing unit-test suite is necessary but not sufficient.
2. Stage-gated validation is required; otherwise bad artifacts can flow downstream while tests still pass.
3. The correct development pattern is:
   - rerun from the earliest necessary stage
   - validate the current stage
   - only then advance
   - stop immediately when a gate fails
4. Old artifacts should be treated as references, not as trusted canonical inputs.

## 3. Source-side findings

### 3.1 Dominant early bottleneck
The earliest dominant bottleneck was not study assembly.
It was source-side structural reliability.

### 3.2 Specific source-side failure modes discovered
1. Footnote / metadata intrusion
   - `*Equal contribution` split the first introduction paragraph.
2. Figure-caption / body boundary failure
   - RQ1 body prose was truncated before Figure 1.
   - Figure 1 caption absorbed downstream body prose.
3. Segmentation contamination
   - metadata lines were merged into body prose blocks.

### 3.3 What fixed the source-side gate
1. English repair was redesigned to:
   - isolate intrusive metadata
   - merge prose interrupted by metadata
   - pull body continuation back out of Figure 1 mixed boundaries
2. Segmentation was redesigned to:
   - keep metadata noise lines separate (`unknown` instead of `paragraph`)
   - support caption continuation without swallowing following body prose
3. After this redesign, the trusted slice source-side gate passed.

## 4. Translation-side findings

### 4.1 First-pass translation failures discovered
1. `protect_text` was over-aggressive.
   - It masked common academic acronyms and ordinary technical terms.
   - This increased placeholder residue and translation drift.
2. First-pass Gemini translation could be complete but still poor.
   - Problems included awkward wording, English leakage, semantic drift, and malformed local phrasing.
3. Trusted-slice first pass was not acceptable on its own.

### 4.2 What improved translation quality
1. `protect_text` was narrowed to preserve only genuinely high-risk spans:
   - code spans
   - URLs
   - emails
   - inline math
2. Metadata noise was excluded from translation blocks by fixing segmentation.
3. Trusted-slice targeted repair improved quality materially.

## 5. Repair-stage findings

1. Repair prompt token budget mattered more than expected.
2. Gemini repair with `maxOutputTokens=1024` caused repair outputs themselves to truncate.
3. Raising Gemini `maxOutputTokens` to `4096` materially improved repair stability.
4. Suspicious-block detection should not only look for truncation.
5. It must also consider:
   - placeholder residue
   - semantic drift / malformed outputs
   - abnormal English-heavy outputs
   - duplicated fragments

## 6. Heuristic findings

### 6.1 Good heuristic changes
1. Truncated-translation detection prevented half-finished zh-TW from being treated as healthy output.
2. Citation-heavy but otherwise complete Chinese paragraphs should not be auto-flagged just because they contain many English names/citations.
3. Metadata noise lines should be isolated structurally before translation, not repaired after the fact whenever possible.

### 6.2 Remaining heuristic limitations
1. Some blocks are still flagged even though they are likely acceptable or only mildly rough.
2. Some rough but non-catastrophic paragraphs still pass because the heuristic is tuned to avoid false positives.
3. The current remaining suspicious set likely mixes:
   - genuinely noisy blocks
   - front-matter formatting blocks
   - table/figure-derived blocks
   - some paragraphs that are merely stylistically rough

## 7. Whole-paper findings

1. Whole-paper first-pass translation now completes successfully.
2. Whole-paper repair now completes successfully.
3. No `TRANSLATION_ERROR` markers remain in the repaired whole-paper artifact.
4. No `§PROTECTED_` markers remain in the repaired whole-paper artifact.
5. Restart2 is a real end-to-end pipeline run, not a patched-together partial output.

## 8. Artifact findings

### 8.1 Current best baseline
Current reviewable baseline:
- `outputs/2511.23174_Safety_Agents_or_Propaganda_Engine.study.zh-TW.restart2.md`

Archival companion:
- `outputs/2511.23174_Safety_Agents_or_Propaganda_Engine.zh-TW.restart2.md`

### 8.2 Current limitations in restart2
1. Study output is still not at true deep-reading final quality.
2. Some roughness remains in:
   - abstract wording
   - introduction wording
   - some table/list-derived passages
   - some figure/table-adjacent sections
3. Whole-paper repaired artifact still has 8 remaining suspicious blocks.
4. The 8-block list is recorded in:
   - `outputs/work/restart2-suspicious-blocks.txt`

## 9. Testing findings

1. The test plan had to be upgraded from artifact-existence checks to stage-gated quality checks.
2. The trusted slice is now the canonical translation health probe:
   - Abstract
   - Introduction first 3 paragraphs
   - Problem Definition 2.1 first paragraph
3. Regression tests were added for:
   - intrusive footnote isolation
   - Figure 1 caption/body boundary handling
   - metadata line isolation in segmentation
   - reduced false positives in suspicious-block detection
   - over-aggressive placeholder masking in translation

## 10. Practical conclusions

1. The architecture is now good enough to continue iterating on quality without another full redesign.
2. The system has moved from “pipeline still structurally unreliable” to “pipeline runs end-to-end but still needs focused polish.”
3. The highest-value next step is not another full restart.
4. The highest-value next step is a focused polish pass on the remaining suspicious blocks and visible rough study-output passages.

## 11. Recommended next step

Use restart2 as the new baseline.

Then do a focused restart3 polish pass:
1. inspect the 8 remaining suspicious blocks one by one
2. decide which are true defects vs heuristic noise
3. patch the truly bad ones
4. regenerate repaired artifact and final outputs
5. review whether restart3 qualifies as a final candidate
