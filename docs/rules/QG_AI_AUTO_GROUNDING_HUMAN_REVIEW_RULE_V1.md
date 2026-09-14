# QG AI Auto-Grounding + Human Review Rule V1

State: **FROZEN_RULE**

## Core Principle

**AI tự đối chiếu, tự trích xuất, tự so khớp rule; con người kiểm tra và phê duyệt.**

Human review is validation and approval, not manual reconstruction of the Question Generation evidence model.

## Mandatory Pipeline

```text
APPROVED_SOURCE_EVIDENCE
↓
AI_EVIDENCE_INTERPRETER
↓
AUTO_FACT_LEDGER
↓
AUTO_NUMBER_UNIT_QUANTITY_LEDGER
↓
AUTO_RELATION_LEDGER
↓
AUTO_COHERENCE_CHECK
↓
AUTO_MULTI_SOURCE_COMPOSITION_CHECK
↓
AUTO_COGNITIVE_OPPORTUNITY_CHECK
↓
HUMAN_QUICK_REVIEW
↓
PRE_GENERATION_GROUNDING_GATE
↓
GROUNDING_GUARD
↓
CONTROLLED_GENERATION
↓
POST_GENERATION_GROUNDING_VALIDATION
↓
COGNITIVE_VALIDATION
↓
TEACHER_APPROVAL
↓
READY_FOR_USE
```

## AI Responsibilities

- Read approved source evidence.
- Extract source-supported factual claims.
- Extract numbers together with their exact quantity meaning and unit/context.
- Extract explicit or directly derivable semantic relations.
- Evaluate evidence coherence.
- Evaluate multi-source composition requirements.
- Evaluate whether the requested cognitive level is naturally supported.
- Compare all proposed claims against the grounding rules.
- Propose PASS or HOLD conservatively.
- Expose all proposed facts, numbers and relations to the human reviewer.

## Human Responsibilities

- Inspect original approved evidence.
- Review AI-extracted facts, numbers, quantities and relations.
- Reject or deselect incorrect AI proposals.
- Correct an individual proposal when necessary.
- Approve or reject the resulting grounding review.

## Human Is Not Required To

- Manually construct the Fact Ledger from scratch.
- Manually construct the Number/Unit/Quantity Ledger from scratch.
- Manually construct the Relation Ledger from scratch.
- Manually invent cross-source semantic links.
- Manually design the question before generation.

## Hard Invariants

- `AI analysis ≠ AI approval`
- Human approval remains mandatory.
- Every generated claim must be source-grounded.
- Unsupported evidence results in `HOLD_NO_VALID_SOURCE_SET`.
- Generation is blocked before Grounding Guard PASS.
- Same page/context/chapter does not prove a semantic relation.
- Multi-source fragment stitching to manufacture difficulty is forbidden.
- HOLD is a valid successful safety output.

## SourceGuard Integration

`Container → Object → ReadingRegion → Anchor → ReadingLane → RegionGrowing → Validation → Render`

SourceGuard architecture remains unchanged.

SourceGuard controls the authorized original evidence. QG grounding governance controls what AI may legitimately derive from that evidence.

## Pilot Learning

Q5 demonstrated that structural validity does not guarantee source grounding.

Q6 demonstrated that the automated grounding layer can correctly produce `HOLD_NO_VALID_SOURCE_SET` when ADVANCED composition would require external knowledge or artificial source stitching.

These pilot cases are retained as provenance/regression evidence; they are not special-case generation rules.
