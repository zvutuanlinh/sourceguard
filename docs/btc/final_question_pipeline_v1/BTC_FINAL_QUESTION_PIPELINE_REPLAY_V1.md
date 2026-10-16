# BTC Final Question Pipeline — Replay / Verification V1

This guide verifies the historical result without regenerating it.

## Trace path

```text
RAW P06/P07/P08
↓
Source Unit candidate universe
↓
Human selection
↓
Composition review
↓
Question Contract
↓
Pregen Grounding
↓
Candidate V1
↓
Postgen V1 FAIL
↓
Candidate V2
↓
Postgen V2 PASS
↓
Teacher APPROVED
↓
READY_FOR_USE
```

## Fast verification

1. Verify RAW SHA for P06/P07/P08.
2. Verify checkpoint snapshot hashes.
3. Verify Candidate V1 and V1 failure artifact.
4. Verify Candidate V2 and V2 postgen PASS.
5. Verify final teacher state.

## Expected final values

```text
PREGEN ................ PASS_FOR_GENERATION
CANDIDATE V1 .......... STRUCTURAL PASS
POSTGEN V1 ............ SOURCE_EVIDENCE_FAIL
CANDIDATE V2 .......... STRUCTURAL PASS
POSTGEN V2 ............ SOURCE_EVIDENCE_PASS
COGNITIVE ............. PASS
TEACHER ............... APPROVED
READY_FOR_USE ......... TRUE
```

## Important

Replay means verification of stored evidence.

It does not mean calling Gemini again.

It does not mean recreating Q5/Q6.

If an expected SHA differs, stop with `HOLD`.
