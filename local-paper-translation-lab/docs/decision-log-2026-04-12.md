# Decision Log — 2026-04-12

## Decision

The project changes from:
- local Qwen/Gemma as both implementation models and candidate final translation engines

to:
- local Qwen/Gemma as implementation models
- Gemini 2.5 Flash as the canonical translation engine for final output

## Reason

Empirical results from the previous round showed:
- clean-source extraction/normalization improved executability
- but local Qwen/Gemma translation quality still did not meet the standard for deep reading
- Gemini 2.5 Flash quality is materially better and cost is low enough to be practical

## Implication

Future comparisons should answer:
- which local model is better at building the system?

rather than:
- which local model is the best final translation engine?
