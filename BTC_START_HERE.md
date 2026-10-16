# EXAMTRUST AI — BTC / BGK START HERE

> Đây là điểm bắt đầu ngắn gọn để BTC/BGK kiểm tra dự án.
> Không cần tin một bản tường thuật duy nhất: toàn bộ Git, Drive, RAW, SHA256,
> evidence lịch sử và pipeline tái kiểm chứng đều có thể được đọc/chạy trực tiếp.

---

## 1. KIỂM TRA NHANH — NÊN MỞ FILE NÀY TRƯỚC

Mở notebook:

```text
docs/btc/BTC_PROJECT_AUDIT_GUIDE.ipynb
```

Notebook gồm **36 cell audit**. Chạy từ Cell 01 đến Cell 36.

Nó kiểm tra lần lượt:

```text
Google Drive
→ GitHub authentication
→ local/remote Git authority
→ Git graph + tags + commits
→ RAW P06/P07/P08 + SHA256
→ Source Unit candidate universe
→ Human source selection
→ Multi-source composition
→ Question Contract
→ PREGEN PASS_FOR_GENERATION
→ Candidate V1
→ POSTGEN V1 SOURCE_EVIDENCE_FAIL
→ Candidate V2
→ POSTGEN V2 SOURCE_EVIDENCE_PASS
→ Cognitive PASS
→ Teacher APPROVED
→ READY_FOR_USE
→ historical checkpoints / receipts
→ Q1–Q6 history
→ R2 history
→ reusable RAW-to-READY pipeline
→ final machine audit
```

---

## 2. TÀI LIỆU CHI TIẾT

Nếu muốn đọc giải thích từng bước trước khi chạy notebook:

```text
docs/btc/README_BTC_PROJECT_AUDIT.md
```

README này mô tả cùng **36 kiểm tra**,
mỗi phần đi kèm cell gọi trực tiếp dữ liệu từ dự án.

---

## 3. CHẠY LẠI FINAL PIPELINE TỪ RAW

Trong Google Colab đã mount Drive, chạy:

```python
!python /content/drive/MyDrive/SourceGuard_Git/sourceguard/code/examtrust_btc_p06_p07_p08_pipeline_from_raw.py --mode btc-replay
```

Kết quả cuối kỳ vọng:

```text
RAW SOURCE TRUTH ............. PASS
SOURCE UNIT UNIVERSE ......... PASS
HUMAN SOURCE SELECTION ....... PASS
COMPOSITION .................. PASS
QUESTION CONTRACT ............ PASS
PREGEN ....................... PASS_FOR_GENERATION
GENERATION MODE .............. FROZEN_ARTIFACT_REPLAY
CANDIDATE V1 ................. STRUCTURAL_PASS
POSTGEN V1 ................... SOURCE_EVIDENCE_FAIL
CANDIDATE V2 ................. STRUCTURAL_PASS
POSTGEN V2 ................... SOURCE_EVIDENCE_PASS
COGNITIVE .................... PASS
TEACHER ...................... APPROVED
READY_FOR_USE ................ TRUE

RESULT = PASS / RAW_TO_READY_FOR_USE_PIPELINE_VERIFIED
```

Lưu ý:

```text
LIVE GEMINI = NO
LIVE OCR = NO
LIVE SEGMENTATION = NO
HISTORICAL ARTIFACT MUTATION = NO
```

Pipeline này tạo **một reproducibility run mới**.
Run mới dùng để tái kiểm chứng; không giả nhận là evidence lịch sử gốc.

---

## 4. CÁC MỐC GIT CHÍNH

```text
Project closure checkpoint
b0196cdcaf365b808fcb91b1cd85c2e54f4e0903
tag: examtrust-project-closure-v1

R2 cumulative history head
187b7972348f6279c4ba950577ab4092c4601e97

Final P06/P07/P08 question checkpoint
f56338a14a21e063de3d68eb31c0a6242ad29d18
tag: btc-final-p06-p07-p08-question-v1

History integration merge
0e4b3624a3a905ca117918d8609fcb886519fff8

Reusable RAW-to-READY pipeline
1d2cabed1e6f669a841399afc92c16f4b13bca0f

BTC project audit README/notebook
520b5b15f0a5ba07d623980040d9f5cb09ce2ac1
```

---

## 5. DRIVE PACKAGE

BTC package root:

```text
/content/drive/MyDrive/EXAMTRUST_BTC_FINAL_ISOLATED_V1
```

Audit guide mirror:

```text
06_PACKAGE/BTC_PROJECT_AUDIT_GUIDE/
```

Reproducibility runs:

```text
07_REPRO_RUNS/
```

Final-question durable checkpoint:

```text
05_MANIFEST/BTC_FINAL_QUESTION_PIPELINE_CHECKPOINT_V1/
```

---

## 6. CÁCH HIỂU CÁC LOẠI BẰNG CHỨNG

**Historical original evidence**
: artifact thực sự sinh ra trong quá trình phát triển.

**Historical Git evidence**
: commit/tag ghi lại các mốc của dự án.

**Retrospective BTC checkpoint/index**
: index/snapshot tạo sau để BTC audit dễ hơn; không được xem là artifact lịch sử gốc.

**Current reproducibility run**
: run mới tạo khi chạy lại pipeline; chứng minh khả năng tái kiểm chứng, không thay thế lịch sử.

---

## 7. NGUYÊN TẮC AN TOÀN / TOÀN VẸN

Trong quá trình đóng gói BTC:

```text
FORCE PUSH = NO
REBASE = NO
HISTORICAL MUTATION = NO
```

Final-question checkpoint tag vẫn cố định tại:

```text
btc-final-p06-p07-p08-question-v1
→ f56338a14a21e063de3d68eb31c0a6242ad29d18
```

---

## 8. TRÌNH TỰ KHUYẾN NGHỊ CHO BTC/BGK

1. Đọc file `BTC_START_HERE.md` này.
2. Mở `docs/btc/BTC_PROJECT_AUDIT_GUIDE.ipynb`.
3. Chạy lần lượt Cell 01 → Cell 36.
4. Khi cần giải thích thêm, đối chiếu `docs/btc/README_BTC_PROJECT_AUDIT.md`.
5. Cuối cùng chạy lại RAW-to-READY pipeline để tạo một reproducibility run mới.

Nếu Cell 36 trả về:

```text
RESULT = PASS / BTC_PROJECT_AUTHORITY_VERIFIED
```

và RAW-to-READY pipeline trả về:

```text
RESULT = PASS / RAW_TO_READY_FOR_USE_PIPELINE_VERIFIED
```

thì các authority chính của gói BTC đã được máy kiểm tra thành công.
