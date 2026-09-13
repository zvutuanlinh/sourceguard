# ExamTrust AI — Evidence Index (Current)

- Generated at UTC: `2026-09-13T18:59:32Z`
- Pilot state: `IN_PROGRESS`
- Completed reviewed items: `2 / 6`
- Completed slots: `Q1, Q2`
- Remaining slots: `Q3, Q4, Q5, Q6`
- Final acceptance: `NOT_EVALUATED`
- Historical artifacts mutated: `NO`
- Evidence bundle Git commit: `9182eecffebbc27abc4a430789b72570cf36cbd4`
- Evidence bundle remote verified: `YES`
- Publication receipt: `09_EVIDENCE_HISTORY/PUBLICATION_RECEIPT.json`

## 1. Historical baseline

- Original pilot manifest: `QUESTION_GENERATION_PILOT_MANIFEST_V1.json`
- SHA256: `3d818a433ab6153a687975c92b7b8976bd3a90eae8e6aeddcf80b076f2f373b2`

- Question contracts: `02_CONTRACTS/QUESTION_CONTRACTS_V1_REVIEW.json`
- SHA256: `606600cc6acd0cd38b98f6b22d62b48a53db3cd5c88d12199c17764a68496880`

These two artifacts are preserved as pre-generation historical records and are not rewritten.

## 2. Current pilot status

- Current status: `08_PILOT_RESULTS/QUESTION_GENERATION_PILOT_STATUS_CURRENT.json`
- Pilot items: `08_PILOT_RESULTS/pilot_6_items.jsonl`
- Pilot summary: `08_PILOT_RESULTS/pilot_summary.json`
- Acceptance report: `08_PILOT_RESULTS/acceptance_report.json`
- Human-readable question history: `08_PILOT_RESULTS/PILOT_QUESTION_HISTORY.md`

## 3. Q1 reviewed evidence

- Teacher review: `06_VERIFICATION_PACK/Q1/QC_PILOT_01_TEACHER_REVIEW_V1.json`
- Teacher review SHA256: `b3d1d6d25849e037961c3091853532cb852b31d9b2c2373e51f48682e7b377bd`
- Generated artifact: `artifacts/question_generation/pilot_q1_review/QC_PILOT_01_GENERATED_Q1_V1_REVIEW.json`
- Generated artifact SHA256: `8ff649ed364824b84a48580abde032f02ad295935e4139b2834954e0d40ea7b1`
- Raw model response: `artifacts/question_generation/pilot_q1_review/QC_PILOT_01_RAW_MODEL_RESPONSE_V1.txt`
- Raw response SHA256: `579a4eef64041135fe75a7ec397853386b2733b70039499c5589589cf35dae28`
- Review-history manifest: `artifacts/question_generation/pilot_q1_review/Q1_REVIEW_HISTORY_MANIFEST.json`
- Review-history manifest SHA256: `8ce2d57ef5637f24e31e3d9e870e861d535b50792075a240f519b5a828c7102a`

## 4. Q2 reviewed evidence

- Teacher review: `06_VERIFICATION_PACK/Q2/QC_PILOT_02_TEACHER_REVIEW_V1.json`
- Teacher review SHA256: `bb6619d31ac5d73b976d498339e5310a0efaa0e7e9cc4197fd1ea67d0ec24599`
- Generated artifact: `artifacts/question_generation/pilot_q2_review/QC_PILOT_02_GENERATED_Q2_V1_REVIEW.json`
- Generated artifact SHA256: `fbd8e92923270b690d08f1d117ac96a7b12ebd31bb39985e842183a786441731`
- Raw model response: `artifacts/question_generation/pilot_q2_review/QC_PILOT_02_RAW_MODEL_RESPONSE_V1.txt`
- Raw response SHA256: `17a7affddfe6c23969b5ffd4f0472878c532df5143e7542e45c533356eac425f`
- Review-history manifest: `artifacts/question_generation/pilot_q2_review/Q2_REVIEW_HISTORY_MANIFEST.json`
- Review-history manifest SHA256: `ce89789ef3a039903c83a165155f492c0c0d83e72e818fb8fe235e5a3b99ae3f`

## 5. Evidence history

- Append-only evidence history: `09_EVIDENCE_HISTORY/EVIDENCE_HISTORY.jsonl`
- Publication record: `09_EVIDENCE_HISTORY/PUBLICATION_RECORD_PENDING.json`

## 6. Notebook snapshot

- Storage scope: `Organizer Drive evidence only — notebook binary is intentionally not committed to Git`
- Git representation: `SHA256 + evidence index reference only`
- Snapshot: `09_EVIDENCE_HISTORY/NOTEBOOK_SNAPSHOTS/ExamTrust_Development_2026__SNAPSHOT_20260913_185412.ipynb`
- SHA256: `94772ca34e8837063ac17f021b84976c9e725a413138eeaf3f5b7e6d271eafe7`
- Purpose: `Evidence snapshot of the current development notebook at reconciliation time`
- Historical coverage claim: `NO — this snapshot is not claimed to represent the complete notebook history`

## 7. Portability note

Paths in this index are logical/project-relative paths wherever possible.

- Paths beginning with `artifacts/` are relative to the SourceGuard Git repository root.
- Paths beginning with `02_CONTRACTS/`, `06_VERIFICATION_PACK/`, `08_PILOT_RESULTS/`, or `09_EVIDENCE_HISTORY/` are relative to the Question Generation Pilot evidence root.
- Notebook snapshots are stored in Organizer Drive evidence; Git records their identity by SHA256 and index reference rather than committing the notebook binary.

Absolute Colab/Google Drive runtime paths are intentionally omitted from this organizer-facing index.

