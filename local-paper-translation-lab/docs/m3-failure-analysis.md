# M3 Failure Analysis

Status: completed analysis  
Author: Max  
Date: 2026-04-11

## Purpose

Document why the initial M3 Translation Core implementation did not produce a reliably high-quality deep-reading translation, despite partial technical success.

This document is intended to guide the next spec revision.

---

## Executive Summary

The core problem is now better understood as **two separate engineering problems**, not one:

1. **English source extraction / normalization**
2. **English-to-Traditional-Chinese translation**

The initial M3 implementation implicitly treated these as one combined task by feeding noisy PDF-extracted text directly into the translation engine.

This made it difficult to determine whether failures came from:
- poor PDF extraction
- local serving instability
- model formatting behavior
- translation quality itself

The next spec revision should split these concerns explicitly.

---

## What We Observed

## 1. M1 source extraction was usable but noisy

The custom extraction path successfully produced machine-readable text, but it had known degradation:
- multi-column layout flattened into a linear stream
- ligature/glyph corruption
- unnatural line breaks
- weak structure around figures/tables/equations
- noisy front matter

This means the translation engine was not operating on a clean document.

## 2. Gemma 4 31B failed mainly on latency / serving stability

Observed failure mode:
- repeated socket timeout during full-sample translation
- persisted even after reducing batch size and char budget
- persisted even after sentence-level splitting

Interpretation:
- In the current implementation path, Gemma 4 31B dense is too slow or too unstable as a full-document direct translation backend.
- This is not necessarily a pure language-quality failure; it is a workflow fit failure.

## 3. Qwen 122B failed first on structured-output compliance

Observed failure mode:
- did not reliably return multi-block tagged output for parser consumption

Mitigation:
- switched to single-chunk translation mode

Interpretation:
- Qwen was more viable than Gemma as a throughput engine in this workflow
- but weaker under strict structured-output constraints

## 4. Qwen later reached technical completion, but output quality remained weak

Observed degradation patterns:
- repeated content
- content drift / non-faithful rewriting
- English leakage
- unstable heading/paragraph translation quality
- placeholder fallback needed for some chunks after retries

Interpretation:
- Technical completion of the translation pipeline is not equivalent to deep-reading-quality output.

---

## Root Cause Breakdown

## A. Source quality problems

This is likely the single biggest upstream issue.

The translation system was asked to translate text that was already degraded by PDF extraction. Therefore the model was doing at least two jobs at once:
- infer the intended English text
- translate into Chinese

This greatly increases drift risk.

### Symptoms linked to source degradation
- broken phrase boundaries
- malformed words due to glyph loss
- awkward paragraph boundaries
- figure/table context merged with body text

### Conclusion
A translation model should not be the primary repair mechanism for broken PDF text.

---

## B. Serving / inference stability problems

Both local backends exposed practical runtime constraints.

### Gemma
- timeout-dominated

### Qwen
- occasional HTTP 500
- temporary server unavailability
- more robust after engineering mitigations, but still not fully stable

### Conclusion
For long document translation, the serving stack matters almost as much as the model.

---

## C. Translation-discipline problems

Chatting fluently in Chinese is not the same as producing a faithful academic translation.

The models were weak on one or more of these constraints:
- do not summarize
- do not add content
- do not drift semantically
- preserve technical identifiers exactly
- stay consistent over many chunks

### Important distinction
The issue is not simply "the model cannot speak Chinese well".
The issue is that the model is being used as a **strict long-form document translation engine**, which is a much narrower and more demanding task than interactive chat.

---

## D. Missing consistency-control layer

The current M3 design lacks a dedicated layer for:
- terminology normalization
- cross-section consistency
- output verification against source
- cleanup of repeated/generated artifacts

Without this layer, even a technically successful run can still produce weak deep-reading output.

---

## Why shrinking chunks happened

Shrinking chunk size was not chosen because it improves translation quality in principle.

It was chosen because larger requests failed in practice due to:
- timeout
- server instability
- structured-output failure
- long-generation drift

So chunk shrinking was an **engineering survival tactic**, not an ideal translation strategy.

This distinction is important.

In theory:
- more context usually helps translation quality

In practice here:
- too much context prevented the system from completing at all

---

## Most Important Conclusion

The current evidence suggests that the real system should be redesigned as:

### Stage 1: English source extraction / normalization
Goal:
- produce the cleanest possible English source representation
- ideally using a stronger extraction source such as markitdown output as primary reference

### Stage 2: English -> Traditional Chinese translation
Goal:
- translate from clean English source
- not from raw PDF extraction artifacts

This split will make evaluation much clearer:
- extraction quality can be evaluated independently
- translation quality can be evaluated independently

---

## Practical Recommendation for Next Revision

## Recommendation 1
Treat source extraction and translation as separate milestones with separate success criteria.

## Recommendation 2
Use `markitdown`-generated markdown as a canonical or near-canonical English source candidate for v1 translation experiments.

## Recommendation 3
Retain PDF/block extraction as a secondary structural reference, especially for:
- figures
- tables
- equations
- block ordering

## Recommendation 4
Do not judge model translation quality solely from raw-PDF-to-Chinese runs.
That conflates extraction failure with translation failure.

## Recommendation 5
Revise the spec so M3 consumes a cleaner English source artifact rather than directly consuming noisy extraction output as the default path.

---

## Comparison Signal Collected So Far

### Gemma 4 31B dense
Strengths:
- likely stable in narrow/small requests
- conceptually attractive as a dense model

Weaknesses observed in this workflow:
- too slow / timeout-prone for direct full-document translation

### Qwen 122B
Strengths:
- more likely to complete translation requests after engineering mitigation
- better throughput fit than Gemma in the current workflow

Weaknesses observed in this workflow:
- weaker structured-output compliance
- more generation drift under strict translation constraints
- required multiple engineering workarounds

---

## Next Step

Revise Step 1 spec so that the pipeline is explicitly split into:
1. clean English source generation
2. Chinese translation from clean source

This has now led to a further practical decision:
- use Gemini 2.5 Flash as the canonical translation engine for production-quality output
- continue comparing Qwen and Gemma primarily on their ability to implement the system, not on their suitability as the final translation backend
