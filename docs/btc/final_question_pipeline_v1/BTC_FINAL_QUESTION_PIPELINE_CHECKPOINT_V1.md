# ExamTrust AI — Final P06/P07/P08 Question Pipeline Checkpoint V1

Checkpoint ID: `BTC-FINAL-P06-P07-P08-QUESTION-PIPELINE-V1`

Checkpoint created UTC: `2026-10-16T08:38:10.194036+00:00`

## Important interpretation

This checkpoint was created **after** the final question workflow completed.

It is a retrospective index and durable byte-for-byte snapshot of artifacts that already existed.

It does **not** claim that the checkpoint files themselves existed earlier.

- Historical source artifacts rewritten: `NO`
- Gemini called while creating this checkpoint: `NO`
- OCR called while creating this checkpoint: `NO`
- Question regenerated while creating this checkpoint: `NO`

## Final question

Dựa trên đồ thị Hình 1.5 và mô hình động học phân tử ở Hình 1.3, hãy xác định các đặc điểm về chuyển động và trạng thái của các phân tử nước trong quá trình đun sôi từ điểm A đến điểm C.

**A.** Trong đoạn AB, tốc độ chuyển động của các phân tử tăng dần khi nhiệt độ tăng từ 20°C đến 100°C; trong đoạn BC, xảy ra sự chuyển thế từ trạng thái các phân tử ở gần nhau, sắp xếp không trật tự sang trạng thái các phân tử ở xa nhau, chuyển động về nhiều hướng khác nhau.
**B.** Trong đoạn AB, tốc độ chuyển động của các phân tử tăng dần khi nhiệt độ tăng từ 20°C đến 100°C; trong đoạn BC, nhiệt độ không đổi ở 100°C cho thấy đang xảy ra quá trình chuyển thế của nước.
**C.** Trong đoạn BC, nhiệt độ nước giữ nguyên ở 100°C để thực hiện quá trình chuyển thế; các phân tử chuyển từ trạng thái ở gần nhau, sắp xếp không trật tự sang trạng thái ở xa nhau và chuyển động về nhiều hướng khác nhau.
**D.** Trong đoạn AB, tốc độ chuyển động của các phân tử tăng dần khi nhiệt độ tăng từ 20°C đến 100°C; các phân tử nước chuyển từ trạng thái ở gần nhau, sắp xếp không trật tự sang trạng thái ở xa nhau, chuyển động về nhiều hướng khác nhau.

**Correct answer:** A

## Final state

- Pre-generation Grounding: `PASS_FOR_GENERATION`
- Post-generation Grounding: `SOURCE_EVIDENCE_PASS`
- Cognitive Validation: `PASS`
- Teacher Review: `APPROVED`
- Ready for Use: `TRUE`

## Exact final source set

- `PHY12_P06_R03`
- `PHY12_P07_V01`
- `PHY12_P08_V01`

## Actual development pipeline

| # | Stage | Actual action | Result |
|---:|---|---|---|
| 1 | `RAW_SOURCE_TRUTH` | Bind original P06/P07/P08 page pixels as source authority. | `PASS` |
| 2 | `SOURCE_UNIT_CANDIDATE_UNIVERSE` | Build the candidate Source Unit universe from P06/P07/P08. | `PASS` |
| 3 | `HUMAN_SOURCE_SELECTION` | Human selects exactly PHY12_P06_R03 + PHY12_P07_V01 + PHY12_P08_V01. | `PASS` |
| 4 | `MULTI_SOURCE_COMPOSITION` | Validate 3-source coherence, necessity and leave-one-source-out behavior. | `PASS` |
| 5 | `QUESTION_CONTRACT` | Freeze scope, cognitive target, selected sources, reasoning requirements and external-knowledge restrictions. | `PASS` |
| 6 | `PREGEN_GROUNDING` | Build/approve fact, number/unit/quantity and relation ledgers including RL01/RL02/RL03. | `PASS_FOR_GENERATION` |
| 7 | `CONTROLLED_GENERATION_V1` | Generate Candidate V1 inside the approved source boundary. | `STRUCTURAL_PASS` |
| 8 | `POSTGEN_V1` | Ground Candidate V1 against approved facts, relations and Step–Source Map. | `SOURCE_EVIDENCE_FAIL` |
| 9 | `CONTROLLED_REGENERATION_V2` | Regenerate Candidate V2 with repaired grounding constraints; preserve the same approved source authority. | `GENERATED` |
| 10 | `SYNTAX_ONLY_JSON_REPAIR` | Remove malformed trailing JSON comma without changing semantic question content. | `PASS` |
| 11 | `CANDIDATE_V2_FINALIZATION` | Finalize Candidate V2 with RL01/RL02/RL03 and all three selected sources. | `STRUCTURAL_PASS` |
| 12 | `POSTGEN_V2` | Validate claims, numbers, quantities, relations, visuals and Step–Source Map. | `SOURCE_EVIDENCE_PASS` |
| 13 | `COGNITIVE_AND_TEACHER_GATE` | Validate cognitive requirements and require explicit Teacher Approval. | `APPROVED` |
| 14 | `READY_FOR_USE` | Close the final candidate as Ready for Use. | `READY_FOR_USE` |

## Critical real-history point: V1 did not pass

The final history was **not** a straight path from generation to approval.

Candidate V1 was generated and structurally valid, but post-generation grounding rejected it.

- Candidate V1 SHA256: `af504a8336ef754ffa28c7fab0d7fc7d6075572b89e8adbfcf01f87820814dca`
- Postgen V1 SHA256: `7460b8f0ea93f0d7a2a1407c5349230712d326055df0a9f64354bb2437bc4d12`
- Result: `SOURCE_EVIDENCE_FAIL`

A new V2 candidate was then generated under the same approved source authority.

- Original V2 raw SHA256: `91f9603eaf98d926f1102b957301136e878f94464652d5825ecafc65a710b489`
- Syntax-only repaired JSON SHA256: `4d221721b5fce06482b25851034425f5eff03faf90d3e5c021b9f7783ba4ef91`
- Candidate V2 SHA256: `7b5a6a69cf0cc56f55584074faec8d2a1cba8df4029a24d94db42f7fbc59b862`
- Postgen V2 SHA256: `f0719db4f4256628fb56a580dddc6000fe713b11d90dbd78ff78e660a21ca669`
- Result: `SOURCE_EVIDENCE_PASS`

This failed-then-repaired lineage is intentionally preserved because it is part of the actual engineering history.

## Original source authority

### P06

- Path: `/content/drive/MyDrive/PILOT01_Physics12_Page06_Source.png`
- SHA256: `3d524f1df5c37c47754ad08317c6b59c77bb2a77a2598af674b1884389f243c2`

### P07

- Path: `/content/drive/MyDrive/PILOT01_Physics12_Page07_Source.png`
- SHA256: `081629b1c4973eedf8f7bddc4b2f7f93ff380b1db02ff103c0bf3e2cd6df24ed`

### P08

- Path: `/content/drive/MyDrive/PILOT01_Physics12_Page08_Source.png`
- SHA256: `59c336d932a0fbe36ad2498f3658724d7d92e176710ac54bdcb2933c93932ac4`

## Snapshot policy

Files under `SNAPSHOTS/` are new checkpoint copies.

Their purpose is durable historical preservation and audit.

Each snapshot is SHA256-identical to the corresponding artifact that already existed in the completed workflow.

The snapshots are **not** represented as if they were created at the original workflow time.

## Replay / verification

See:

`BTC_FINAL_QUESTION_PIPELINE_REPLAY_V1.md`

