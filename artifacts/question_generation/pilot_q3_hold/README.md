# Pilot Q3 — Semantic Gate HOLD

## Contract

- Item: `QC_PILOT_03`
- Pilot slot: `Q3`
- Scope: `NON_EXPANDED`
- Level: `ADVANCED`
- Minimum reasoning steps: `3`

Sources:

- `PHY12_P08_G01`
- `PHY12_P08_G02`
- `PHY12_P08_N01`

## Final gate state

| Gate | State |
|---|---|
| Structural Gate | PASS |
| Source Selection | VALID_SELECTION |
| Semantic Gate | HOLD_NO_VALID_SOURCE_SET |
| Generation Allowed | NO |
| Question Generated | NO |
| Teacher Status | UNVERIFIED |
| Ready for Use | NO |

Hold code:

`ADVANCED_THIRD_RELATION_NOT_PROVEN`

## Why Q3 was not generated

The selected source set is structurally valid, but current evidence does not
establish a genuinely indispensable third reasoning relation contributed by
`PHY12_P08_N01`.

The ADVANCED contract requires at least three genuinely necessary reasoning
steps/relations and explicitly prohibits artificial complexity.

Therefore SourceGuard/ExamTrust records a semantic HOLD instead of forcing
generation.

## Pilot-history implication

Q3 is preserved in `PILOT_QUESTION_HISTORY_CURRENT.md` as a blocked pilot slot.

It is intentionally **not** appended to `pilot_6_items.jsonl`, because no
generated question exists and no Teacher Review has occurred.

## Evidence

### Semantic Gate JSON

`QC_PILOT_03_SEMANTIC_GATE_V1.json`

SHA256:

`53072a6625f1e8b7ce4e23b33931563caab75f45163ffc7d18a95a4919c22ef0`

### Semantic Gate Markdown

`QC_PILOT_03_SEMANTIC_GATE_V1.md`

SHA256:

`cf52fa7584bcf45490bc2eff5e76e0758ea7304acae5edca7b43cf236558b5b2`

### Q3 History Record

`Q3_HOLD_HISTORY_RECORD_V1.json`

SHA256:

`7de57c2010c4b531e865ab6d6c8ee827ce1d7fd3f40f649439e21b7cd9fff5cd`

### Human-readable Pilot Question History snapshot

`PILOT_QUESTION_HISTORY_CURRENT.md`

SHA256:

`05a1452057261d3268af17d046836d938d39903d4f255a87b6db16cdd170d167`

## Governance

- Page08 Gold modified: NO
- Runtime Source Index modified: NO
- Retrieval Runtime modified: NO
- Question Contract modified: NO
- `pilot_6_items.jsonl` modified: NO
- Checkpoint created: NO
- Freeze created: NO
- Force push: NO
