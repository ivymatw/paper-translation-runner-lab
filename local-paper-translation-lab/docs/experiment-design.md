# Experiment Design

Status: updated 2026-04-12  
Author: Max

## Goal

Separate two questions that were previously entangled:

1. Which system architecture can produce deep-reading-quality translated papers?
2. Which local model is better at implementing that architecture?

## Updated Decision

The project now adopts:
- **Gemini 2.5 Flash** as the canonical translation engine for production-quality translation output
- **Qwen** and **Gemma** as the two local implementation models being compared

This means the comparison target is no longer:
- "Which local model is the better final translation engine?"

It is now:
- "Which local model is better at building and evolving a translation system whose final translation backend is Gemini 2.5 Flash?"

## Why This Change Was Made

The previous experiments established:
- cleaner English source extraction is necessary
- local Qwen/Gemma translation runs are informative diagnostics
- but neither local model reliably met the quality bar for final academic deep-reading translation output
- Gemini 2.5 Flash appears cheap enough to serve as the practical default translation engine

## Canonical Workflow

```text
PDF
  -> source extraction
  -> source normalization / reconciliation
  -> clean English source
  -> segmentation
  -> Gemini 2.5 Flash translation
  -> assembly
  -> validation
  -> final zh-TW markdown
```

## Comparison Design: Qwen vs Gemma

### What is being compared
Qwen and Gemma are compared on:
- implementation completeness
- robustness under bounded milestone prompts
- quality of generated code and tests
- amount of Max intervention required
- speed to a working system
- ability to revise the system after feedback

### What is not the primary comparison anymore
- final translation quality produced directly by local Qwen/Gemma

That can still be measured as auxiliary diagnostics, but it is no longer the primary project objective.

## Evaluation Axes for Qwen vs Gemma as Implementers

1. Milestone completion rate
2. Number of retries / interventions needed
3. Test pass rate
4. Quality of architecture decisions within scope
5. Stability under strict task boundaries
6. Ability to produce maintainable code
7. Time-to-working-milestone

## Translation Engine Evaluation

Gemini 2.5 Flash should be evaluated separately on:
- fidelity
- readability for deep study
- terminology consistency
- structural preservation
- cost per paper

## Near-Term Plan

### Phase A
Update the implementation to make Gemini 2.5 Flash the default translation backend.

### Phase B
Run the same bounded implementation milestones with:
- Qwen
- Gemma

### Phase C
Use Max acceptance review to determine:
- which model is the better implementation lead going forward
- which failure modes are model-specific vs architecture-specific
