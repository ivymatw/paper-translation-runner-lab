# Five-Paper Validation Summary

## Goal

Determine whether the completion-first runner can become a stable repeated workflow rather than a one-off success.

## Papers

1. `2511.23174_Safety_Agents_or_Propaganda_Engine.pdf`
2. `2602.06371_Bilingual_Bias_in_LLMs_Taiwan_Sovereignty.pdf`
3. `2506.01814_DeepSeekR1_vs_o3mini_bias.pdf`
4. `2505.17441_Discovering_Forbidden_Topics.pdf`
5. `2603.18280_Refusal_Based_Alignment_Eval_Fails.pdf`

## Results

### Paper 1
- pages: 15
- initial full-run result:
  - pass: 6
  - degraded_pass: 9
  - failed_hard_source_passthrough: 0
- role in development:
  - primary bug-discovery paper
  - exposed placeholder and validator failure families

### Paper 2
- pages: 19
- result:
  - pass: 19
  - degraded_pass: 0
  - failed_hard_source_passthrough: 0

### Paper 3
- pages: 21
- result:
  - pass: 21
  - degraded_pass: 0
  - failed_hard_source_passthrough: 0

### Paper 4
- pages: 30
- first full-run result:
  - pass: 29
  - degraded_pass: 1
  - failed_hard_source_passthrough: 0
- isolated issue:
  - page 8 placeholder mismatch caused by role-adjacent placeholder behavior
- follow-up status:
  - edge case diagnosed and validator policy patched
  - clean targeted rerun no longer triggered degraded fallback

### Paper 5
- pages: 31
- first full-run result:
  - pass: 30
  - degraded_pass: 1
  - failed_hard_source_passthrough: 0
- isolated issue:
  - page 16 placeholder mismatch caused by placeholder reordering under valid translation structure
- follow-up status:
  - edge case diagnosed and validator policy patched
  - clean targeted rerun no longer triggered degraded fallback

## What the five-paper loop proved

### Proven
- whole-document completion is robust
- degradation is localized rather than catastrophic
- later papers can pass cleanly after validator/placeholder fixes
- the runner is suitable for repeated operation

### Important engineering lesson
The right unit of improvement was not the whole document.
It was the family of edge cases:
- suspicious-English false positives
- reference-placeholder expansion
- placeholder formatting variants
- placeholder reordering
- refusal-path placeholder deletion

Once those were isolated and fixed, stability improved sharply across later papers.

## Current operational status

The system is now best described as:
- operational beta
- completion-ready
- multi-paper validated
- still worth polishing for reference-heavy formatting quality
