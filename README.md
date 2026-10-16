# SourceGuard

Version-controlled rules, manifests, frozen metadata, checkpoints,
source indexes, code and tests for the SourceGuard pipeline.

## Frozen architecture

Container → Object → ReadingRegion → Anchor → ReadingLane →
RegionGrowing → Validation → Render

## Storage policy

Git stores:
- source code
- JSON / JSONL metadata
- rules
- manifests
- checkpoints
- tests
- documentation
- SHA256 references

Large source images, PDFs, video and other binary evidence remain
on Google Drive and are referenced by path + SHA256.

## GitHub owner

zvutuanlinh

<!-- SOURCEGUARD_R2_FINAL_ACCEPTED_START -->

## R2 — Final Accepted Cumulative Checkpoint

The final accepted R2 physical-segmentation state is preserved as the
following cumulative checkpoint:

`EXAMTRUST_R2_5PAGE_CUMULATIVE_ACCEPTED_V1`

### Final accepted scope

The R2 accepted holdout scope consists of exactly five pages:

- `P06`
- `P07`
- `P11`
- `P12`
- `P29`

The following pages are **outside the final accepted R2 scope**:

- `P39`
- `P92`
- `P94`

`P08` and `P91` are development / standardization references. They are
not part of the five-page final R2 holdout result.

### Final cumulative source

The accepted cumulative pipeline source is:

`examtrust_pipeline_EXAMTRUST_R2_5PAGE_CUMULATIVE_ACCEPTED_V1.py`

SHA256:

`91915ed5950f7fab301d2859e48ab5b854939c0d62b97f8364c8fdb8e2c5ddcb`

This source represents the cumulative accepted state for the five-page
R2 scope rather than a page-specific production patch.

### Cumulative development rule

R2 development follows a cumulative acceptance model:

`Accepted State N`
→ `Fix the next page on the exact full accepted state`
→ `Integrate the generic rule into one cumulative source`
→ `Regression-test all previously accepted pages`
→ `Accept State N+1`

A page is therefore not treated as independently accepted if its change
breaks a previously accepted page.

Page-specific production hardcoding is not part of the accepted design.

### Processing architecture

The frozen SourceGuard processing architecture remains:

`Container → Object → ReadingRegion → Anchor → ReadingLane → RegionGrowing → Validation → Render`

The R2 cumulative work extends and validates behavior within this
architecture; it does not redefine the frozen architecture.

### Execution contract

The accepted R2 evidence follows this execution relationship:

`RAW`
→ `FULL CUMULATIVE PIPELINE`
→ `FINAL PHYSICAL RESULT`
→ `LABEL`
→ `FINAL RENDER`

The original RAW pages remain the source input. Accepted evidence is
associated with the cumulative pipeline state and its final rendered
results.

### Accepted result validation

For the final five-page cumulative checkpoint, the preserved acceptance
state records:

- geometry validation: `PASS`
- label / render validation: `PASS`
- human visual review: `ACCEPTED`
- Python compile check: `PASS`
- RAW mutation: `NO`
- protected Engine mutation: `NO`
- Page08 reference mutation: `NO`
- Page91 reference mutation: `NO`
- accepted parent-state mutation: `NO`

The protected Engine, Gold and Page91 artifacts are treated as
read-only references in this workflow.

### Final accepted render SHA256

The five accepted final evidence renders are identified by SHA256:

| Page | Final evidence SHA256 |
|---|---|
| `P06` | `6a1b2876d44b3f6b212e805ea65531b2cd53b7260c715aa5e04c81176c4d72e6` |
| `P07` | `3471aa3249b5b809906bb1146b902e275e6ce7efc3378655a210b37b93ebb859` |
| `P11` | `5b0ce1a0727f95c75df7ff8835fa86731c0dcc7da7fea4c924e50431deb9dbad` |
| `P12` | `4dc143391ad5cf1a5af4be9d51e35ed040b23728206b06790722f43c86ebaba2` |
| `P29` | `0ce5b248976b37511f753e846654eab482fe49425ca49df10c6d26b8cb59dfa6` |

These hashes identify the preserved accepted visual evidence associated
with the final cumulative R2 state.

### R2 Git history

Two preserved commits mark the final R2 repository state:

`b7c1fe7175036503aa0e5dc4c801d27858bd4543`

`feat(r2): finalize 5-page cumulative physical segmentation checkpoint`

followed by:

`9babe35a5635311ad0f568b09d4dc1034e306d72`

`docs(r2): preserve 5-page accepted visual evidence`

The second commit is the R2 state immediately before this README
documentation update.

Updating this README documents the already accepted R2 state. It does
not modify the accepted cumulative source, checkpoint, manifests,
evidence renders, frozen references or R2 tags.

### Interpretation of R2 evidence

Repository presence alone does not make an experimental page or
intermediate artifact part of the accepted R2 result.

For the final R2 claim, the authoritative accepted scope is:

`P06 + P07 + P11 + P12 + P29`

Development, diagnostic and out-of-scope artifacts are retained for
traceability but must not be interpreted as additional accepted R2
pages.

<!-- SOURCEGUARD_R2_FINAL_ACCEPTED_END -->

<!-- SOURCEGUARD_QG_COMPONENT_REVIEW_RULE_START -->

## Question Generation — Human Component Review

A semantic **Source Unit may contain one or multiple geometry components**.

Multiple components are not automatically considered an extraction error. A valid semantic source may be split into several geometric regions, for example when an image, caption, layout object, or another region appears between text fragments.

Before a Source Unit is consumed by Question Generation, the approved workflow is:

`Source Unit → Historical Components → Human Component Review → Human Confirmation → Approved Component Set → Question Generation`

Operating rules:

- A Source Unit may contain `1..N` valid components.
- The reviewer must inspect the full source page and the individual component crops.
- The reviewer may approve one or multiple components.
- The complete selected component set must be shown again before confirmation.
- Question Generation may use only the exact human-approved component set.
- Historical frozen geometry is not rewritten by this review step.
- Human component approval is evidence authorization only; it is not Teacher Approval of the generated question.
- If generation requests geometry outside the approved set, generation must be blocked with `EVIDENCE_COMPONENT_NOT_APPROVED`.

QG invariant:

`requested_generation_components == approved_generation_components`

### Q4 pilot example

For `QC_PILOT_04 / PHY12_P91_R07`:

- Historical components: `3`
- Human-approved components: `C1 + C2`
- Excluded from QG input: `C3`
- Component gate: `PASS`
- Question generated at this review stage: `NO`
- Frozen Page91 mutation: `NO`
- Runtime mutation: `NO`
- Contract mutation: `NO`

Detailed evidence remains in the project evidence workspace:

`/content/drive/MyDrive/test_examtrust/QUESTION_GENERATION_PILOT/03_SOURCE_REVIEW/Q4/QC_PILOT_04_GENERATION_EVIDENCE_ALLOWLIST_V2.json`

Evidence SHA256:

`0d52a6f437a7bea953815441f5626623d881ed823dc5ec9412d84794c2c114ce`

This component-review control is downstream of SourceGuard extraction and does not change the frozen SourceGuard architecture:

`Container → Object → ReadingRegion → Anchor → ReadingLane → RegionGrowing → Validation → Render`

<!-- SOURCEGUARD_QG_COMPONENT_REVIEW_RULE_END -->
