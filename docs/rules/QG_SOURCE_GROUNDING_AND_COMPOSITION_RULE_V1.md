# QG Source Grounding & Multi-Source Composition Rule V1

## 1. Core Principle

> Every factual claim, numeric value, unit, quantity meaning, semantic relation, premise, answer claim, explanation claim, and required reasoning step must be traceable to approved original source evidence.

Question Generation may transform presentation, but it may not manufacture source truth.

## 2. Source Truth

`Original Page / Frozen Source Unit / Human-approved Evidence Crop`

An LLM rewrite, generated explanation, inferred statement, or reconstructed claim is not source truth by itself.

## 3. Mandatory Pre-generation Pipeline

```text
Approved Source Evidence
        ↓
Coherent Evidence Bundle
        ↓
Fact Ledger
        ↓
Number / Unit / Quantity Ledger
        ↓
Relation Ledger
        ↓
Question Opportunity Review
        ↓
Multi-source Composition Review
        ↓
Pre-generation Grounding Gate
        ↓
Controlled Generation
```

## 4. Coherent Evidence

- Approved geometry components are evidence boundaries, not proof of semantic completeness.
- Component authorization does not prove semantic coherence.
- Same page does not prove semantic relation.
- Same context_code does not prove semantic relation.
- Same lesson or chapter does not prove semantic relation.
- The evidence bundle must preserve the reading context required to interpret facts correctly.
- If selected fragments omit necessary bridging content, generation must be blocked.
- The model must not invent missing semantic bridges.

## 5. Fact Ledger

Every source-supported fact available to QG must be registered before generation.

Required fields:
- `fact_id`
- `claim`
- `source_id`
- `approved_component_reference`
- `support_state`

Allowed support states:
- `SOURCE_EXPLICIT`
- `SOURCE_DIRECTLY_DERIVABLE`

## 6. Number / Unit / Quantity Integrity

Numeric grounding is a semantic tuple, not merely a numeric string:

`[value, quantity, unit/context, source evidence]`

- A number may only be used with its source-supported semantic quantity.
- A ratio may not become an absolute quantity without source-supported absolute data.
- A count, frequency, thickness, ratio, angle, time, distance, probability or other quantity must retain its semantic type.
- A computed value is allowed only when all operands and operations are source-authorized.
- If any required operand is invented, the numeric reasoning chain fails.

## 7. Relation Ledger

Every semantic relation used by generation or reasoning must be explicit in the source or directly derivable from approved evidence.

Not sufficient by itself:
- `MODEL_BRIDGED_ONLY`
- `SAME_PAGE_ONLY`
- `SAME_CONTEXT_ONLY`
- `SAME_CHAPTER_ONLY`
- `PEDAGOGICAL_GUESS`

## 8. Multi-source Composition

- **M1.** Each selected Source Unit is sufficiently interpretable within the coherent evidence bundle.
- **M2.** The semantic relation between Source Units is explicit or directly derivable from original evidence.
- **M3.** The intended question genuinely requires the cross-source relation.
- **M4.** No missing semantic bridge is invented by the model.
- **M5.** No numeric value, unit, or quantity is reassigned across semantic meanings.
- **M6.** Sources are not stitched together solely to manufacture cognitive difficulty.
- **M7.** The complete minimum solution path can be reconstructed from approved evidence.
- **M8.** Removing a Source Unit declared as necessary makes the intended solution incomplete.

Failure of any mandatory condition means `MULTI_SOURCE_COMPOSITION = FAIL` and generation is blocked.

## 9. Question Opportunity Review

- The requested cognitive level must arise naturally from source-supported relations.
- Do not invent data to satisfy APPLY.
- Do not invent relations to satisfy ADVANCED.
- Do not force multi-source composition when a coherent simpler source is more natural.
- If the requested cognitive level is unsupported, return HOLD_NO_VALID_SOURCE_SET.

## 10. Mandatory Pre-generation Gate

The generation model must not be called until every required pre-generation check is `True`.

- `approved_evidence_verified`
- `coherent_evidence_bundle_confirmed`
- `fact_ledger_complete`
- `number_unit_quantity_ledger_complete`
- `relation_ledger_complete`
- `question_opportunity_valid`
- `multi_source_composition_valid_if_applicable`
- `no_unsupported_fact`
- `no_unsupported_number`
- `no_unsupported_unit`
- `no_unsupported_quantity`
- `no_unsupported_relation`
- `no_external_bridge`
- `no_artificial_complexity`

Failure action: `GENERATION_BLOCKED`

Teacher override: `NO`

LLM override: `NO`

## 11. Mandatory Post-generation Validation

```text
CLAIM_GROUNDING → NUMBER_GROUNDING → UNIT_GROUNDING → QUANTITY_GROUNDING → RELATION_GROUNDING → STEP_SOURCE_MAP_VALIDATION → SOURCE_EVIDENCE_VALIDATION → COGNITIVE_VALIDATION → TEACHER_REVIEW
```

## 12. Failure Codes

- `UNSUPPORTED_FACT` — Candidate fact is unsupported by approved evidence.
- `UNSUPPORTED_NUMERIC_FACT` — Candidate numeric value has no approved source support.
- `UNSUPPORTED_UNIT` — Candidate unit has no approved source support.
- `UNSUPPORTED_QUANTITY` — Candidate semantic/physical quantity is unsupported.
- `QUANTITY_MEANING_MISMATCH` — A source-supported number is reused as another quantity.
- `UNSUPPORTED_RELATION` — Required semantic relation is unsupported.
- `MISSING_SEMANTIC_BRIDGE` — Composition requires a bridge absent from approved evidence.
- `ARTIFICIAL_MULTI_SOURCE_COMPOSITION` — Fragments were combined merely to manufacture difficulty.
- `INCOMPLETE_COHERENT_EVIDENCE` — Approved evidence lacks necessary continuous semantic context.
- `COGNITIVE_LEVEL_NOT_SOURCE_SUPPORTED` — Requested cognitive level is not naturally supported.
- `HOLD_NO_VALID_SOURCE_SET` — No valid grounded source set supports the requested item.

## 13. Structural Pass Is Not Grounding Pass

```text
STRUCTURAL_PASS ≠ SOURCE_GROUNDED_PASS
```

Correct IDs, four options, valid JSON and a valid answer do not prove that a candidate is source-grounded.

## 14. SourceGuard Integration

`Container → Object → ReadingRegion → Anchor → ReadingLane → RegionGrowing → Validation → Render`

The frozen SourceGuard architecture is unchanged.

SourceGuard controls what original evidence is authorized. The QG grounding rule controls what the model is permitted to claim, calculate and infer from that evidence.

## 15. Anti-overfitting

This rule must not contain page-ID-specific, fixed-coordinate, candidate-specific or pilot-question-specific generation logic.

Pilot failures may be preserved as regression evidence but must not be encoded as special-case rules.

## 16. Final System Principle

> When the evidence is insufficient, HOLD is a successful safety result.

