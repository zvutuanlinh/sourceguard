# Pilot Q1–Q6 — Final Summary V1

State: **PILOT_FINALIZED**

## Pilot matrix

| Slot | Scope | Cognitive target | Final disposition | Generated | Ready / Publication |
|---|---|---|---|---|---|
| Q1 | NON_EXPANDED | UNDERSTAND | APPROVED | YES | READY / PUBLISHED |
| Q2 | NON_EXPANDED | APPLY | APPROVED | YES | READY / PUBLISHED |
| Q3 | NON_EXPANDED | ADVANCED | HOLD_NO_VALID_SOURCE_SET | NO | NO |
| Q4 | SOURCE_BOUNDED_EXPANDED | UNDERSTAND | APPROVED | YES | READY / PUBLISHED |
| Q5 | SOURCE_BOUNDED_EXPANDED | APPLY | NEGATIVE_PILOT_EVIDENCE_RETAINED | YES | NO / NOT_PUBLISHED |
| Q6 | SOURCE_BOUNDED_EXPANDED | ADVANCED | FINAL_HOLD_NO_VALID_SOURCE_SET | NO | NO / NOT_PUBLISHED |

## Aggregate result

- Pilot slots: **6**
- Questions generated: **4**
- Ready / published items: **3**
- Pre-generation safe HOLD cases: **2**
- Post-generation negative grounding case: **1**
- `pilot_6_items.jsonl` published rows: **3**

The pilot is not evaluated only by the number of generated questions.

It validates three required system behaviors:

1. **Supported generation** — Q1, Q2, Q4.
2. **Safe refusal before generation** — Q3, Q6.
3. **Detection of unsupported generation after structural success** — Q5.

## Q5 significance

Q5 produced a structurally valid generated candidate but introduced the unsupported
absolute quantity `4×10^5` spots/min.

The candidate was therefore not allowed to become Ready or Published.

Q5 is preserved as negative regression and governance evidence.

Its original formal post-generation artifact remains unchanged:

- Formal review state: `HUMAN_REVIEW_INCOMPLETE`
- Source/Evidence Validation: `NOT_COMPLETED`
- Ready for Use: `NO`
- Publication: `NOT_PUBLISHED`

The pilot summary does not rewrite that historical artifact.

## Q6 terminal result

Q6 initially used:

`PHY12_P91_R03 + PHY12_P91_R07 + PHY12_P91_V03`

Pre-generation grounding returned:

`HOLD_NO_VALID_SOURCE_SET`

The system then performed source reselection over **all six frozen Source Units available
inside P91/B21**:

- `PHY12_P91_R02`
- `PHY12_P91_R03`
- `PHY12_P91_R07`
- `PHY12_P91_V01`
- `PHY12_P91_V02`
- `PHY12_P91_V03`

The AI reselection layer and human reviewer both concluded:

`FINAL_HOLD_NO_VALID_SOURCE_SET`

No replacement source set was approved.

The system correctly did **not** generate an ADVANCED question by adding outside physics
knowledge or manufacturing complexity.

## Important interpretation of Q6

Q6 is a **bounded-source terminal HOLD**, not a global statement that ADVANCED generation
is impossible.

The conclusion is only:

> The currently authorized P91/B21 source universe is insufficient for this ADVANCED slot.

Future production runs may use a wider approved SourceGuard universe across additional
pages, ReadingRegions, contexts or chapters.

If that wider evidence contains a coherent source set supporting the required reasoning
path, `SOURCE_BOUNDED_EXPANDED / ADVANCED` generation is allowed.

The governing invariant remains:

> **Broader source access may increase generation opportunity; it may never relax source grounding.**

## Governance checkpoint

The previously frozen governance checkpoint remains:

`qg-grounding-governance-v1`

It records:

`AI evidence analysis → Human review/approval → Grounding Guard → Controlled Generation`

The Pilot Q1–Q6 finalization is a separate checkpoint and does not move or rewrite that tag.

## Provenance

- Q5 Post-generation Review SHA256:
  `d181ebf1e968916010b5d83f4de6b29f6d2ac4be4a724c1cd79a5d3db0ed47e2`

- Q6 AI Grounding Proposal SHA256:
  `035e9b392f45c590e7284525d6ab7f519119290d58374798365e255b37d395cc`

- Q6 Pre-generation Grounding SHA256:
  `06c7cbbdaa99d295940725c6c66faed1b52b34f7047abc969f1c6261fbc031da`

- Q6 Source Reselection Review SHA256:
  `46d227ccbb9db3609d925c60d60aa7238640e12f96d90b95aa1ff6d5e178928d`

- Published pilot file SHA256:
  `1fe3296558b8ad85ec6ccffd1b41ab34aa80b5d44036a562fdb922f651ef9546`

- Final cumulative history SHA256:
  `92e9c3529bc2961a4823ee7dc3da35c3b49d81ad3bf28d63b0e82598f3d6f5a3`

## Final pilot status

`PILOT_Q1_Q6_FINALIZED`

The pilot is now closed as an engineering/governance pilot.

Future work should proceed with a broader approved source universe and reuse the frozen
grounding governance rather than forcing unsupported Q3/Q6 source sets.
