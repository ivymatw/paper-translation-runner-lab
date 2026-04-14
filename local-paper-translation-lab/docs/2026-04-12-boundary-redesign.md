# Boundary Redesign Note

Date: 2026-04-12

## Why this redesign exists

The restart pipeline stopped at G3 English repair.

The dominant failure modes are coupled:
1. intrusive metadata / footnotes split core prose
2. figure-caption boundaries are not represented correctly
3. body prose continuation is sometimes left attached to caption material

Treating English repair and segmentation as fully independent stages is still conceptually correct, but the boundary logic between them must now be redesigned together.

## New design intent

### English repair responsibilities
English repair should:
- isolate intrusive metadata blocks such as `*Equal contribution`
- merge prose that is clearly broken by such metadata interruptions
- fix within-line extraction damage that is strongly inferable
- avoid leaving core prose in obviously incomplete pre-figure fragments when the continuation is recoverable from nearby context

English repair should NOT:
- silently invent missing content
- aggressively rewrite figure captions into prose summaries
- decide final block typing for downstream structure

### Segmentation responsibilities
Segmentation should:
- classify repaired English into stable block types
- support figure captions that may continue across one local boundary if the continuation still looks caption-like
- keep true body prose out of figure blocks
- keep recovered body prose as paragraph blocks

Segmentation should NOT:
- assume every line after a figure is body prose
- assume every incomplete line before a figure belongs to the figure caption
- absorb downstream body prose into figure blocks just because the caption sentence appears incomplete

## Concrete target behaviors

### Behavior 1 — Footnote isolation
Input pattern:
- core prose line ending mid-sentence
- isolated metadata line such as `*Equal contribution`
- following line clearly continues the same sentence

Desired result:
- repaired English contains one continuous prose paragraph
- metadata is isolated or suppressed from core prose flow

### Behavior 2 — Figure caption continuation
Input pattern:
- figure caption starts on `Figure N:` line
- next nearby line still reads like caption continuation
- later nearby line resumes body reasoning

Desired result:
- figure block includes full caption only
- body continuation is not absorbed into the figure block
- if body continuation belongs semantically to a preceding paragraph, it should be recoverable by English repair before segmentation where possible

## Development rule

Implement this redesign with tests first:
1. failing English-repair regression test for footnote isolation
2. failing boundary regression test for Figure 1-style caption/body separation
3. only then modify code
