# Clean-Source Translation Comparison: Qwen vs Gemma

Date: 2026-04-11

## Setup

Input source:
- `outputs/work/source_clean.md`

Segmented source:
- `outputs/work/blocks.clean.jsonl`

Model runs:
- Qwen: `outputs/work/translated_blocks.clean.qwen.jsonl`
- Gemma: `outputs/work/translated_blocks.clean.gemma.jsonl`

## Technical result

Both models now complete the clean-source translation run end-to-end.

This is already an important finding:
- splitting extraction/normalization from translation significantly improved workflow executability
- clean source removed one major upstream confound

## Quality result

However, both models still produce translation quality that is not yet acceptable for deep reading.

### Qwen clean-source behavior
Observed:
- many outputs contain English prefixes
- many outputs contain `<think>` / reasoning traces
- some headings drift into unrelated generated text
- many blocks mix English and Chinese in unstable ways
- technical completion is good; translation discipline is weak

Quick indicators:
- think artifacts: 85 blocks
- english-prefix pattern: 114 blocks
- translation_error placeholders: 0

Interpretation:
- Qwen is operationally more robust than Gemma in this workflow
- but it behaves more like a generative assistant than a faithful translation engine

### Gemma clean-source behavior
Observed:
- fewer explicit reasoning artifacts than Qwen
- still heavy English retention / malformed output
- placeholder corruption visible in some blocks
- one translation error placeholder present
- does not yet produce reliable deep-reading Chinese output either

Quick indicators:
- think artifacts: 0 blocks
- english-prefix pattern: 106 blocks
- translation_error placeholders: 1

Interpretation:
- clean source helps Gemma run to completion
- but output still fails the standard of faithful, stable academic translation

## Conclusion

The engineering split was correct:
1. clean English extraction / normalization
2. Chinese translation

But the comparison now shows a second conclusion:
- after source quality is improved, the main remaining bottleneck is **translation discipline / faithfulness**, not merely extraction quality

## Practical comparative takeaway

### Qwen
Better for:
- completing the workflow
- surviving real runtime conditions
- being the more practical engineering backend

Worse for:
- faithful translation behavior
- avoiding drift and hidden reasoning traces

### Gemma
Better for:
- fewer explicit reasoning-trace artifacts than Qwen

Worse for:
- still unstable as a reliable translation engine
- malformed outputs and English retention remain substantial
- more fragile overall in full-document workflows

## Current verdict

At this stage:
- Qwen is the better practical implementation model
- neither Qwen nor Gemma is yet good enough as the final translation engine for high-quality academic deep-reading output under the current prompting strategy

## Next engineering hypothesis

The next likely bottleneck is not source extraction anymore.
It is the translation strategy itself.

The next experiments should test more aggressive control strategies, for example:
1. ultra-short passage translation
2. heading-only vs paragraph-only separate prompts
3. stronger anti-English / anti-reasoning output constraints
4. post-edit cleanup pass after first-pass translation
5. abstract-only quality pilot before whole-paper translation
