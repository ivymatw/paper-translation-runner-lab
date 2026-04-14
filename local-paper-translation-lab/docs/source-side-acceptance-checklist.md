# Source-Side Acceptance Checklist

Use this before any canonical whole-paper translation run.

Target artifacts:
- repaired English source
- segmented block file

## A. Repaired English source

Pass all:
- [ ] title present
- [ ] abstract present
- [ ] introduction present
- [ ] problem definition present
- [ ] references present if source paper includes references
- [ ] abstract core paragraph is complete
- [ ] introduction first 3 prose paragraphs are complete
- [ ] problem definition 2.1 first prose paragraph is complete
- [ ] no obvious figure/table caption text inserted into those core prose paragraphs
- [ ] no obvious footnote contamination that breaks reading flow in those core prose paragraphs

## B. Segmentation

Pass all:
- [ ] blocks file parses fully
- [ ] block ids unique and ordered
- [ ] headings represented as headings
- [ ] figure captions represented as figure/table blocks rather than body prose
- [ ] equations/code remain protected blocks
- [ ] references remain references
- [ ] introduction first 3 prose blocks are semantically complete
- [ ] problem definition 2.1 first prose block is semantically complete
- [ ] no known caption/body boundary failure around Figure 1

## C. Decision

### PASS
- source-side artifacts are trustworthy enough for trusted-slice canonical translation evaluation

### PASS WITH KNOWN DEFECTS
- minor defects documented, but trusted-slice translation may proceed cautiously

### FAIL
- source-side artifacts are not trustworthy enough; do not judge translation quality yet
