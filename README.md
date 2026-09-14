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
