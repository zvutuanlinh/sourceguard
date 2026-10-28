# KHKT — ExamTrust AI: checkpoint tái kiểm chứng liên môn

**Checkpoint:** `KHKT_E42_BIO_PHY_20261028` — hồ sơ lưu trữ phục vụ ban tổ chức kiểm tra, không phải tuyên bố đã tái chạy độc lập.

## Trạng thái bằng chứng đã đóng băng

| Nội dung | Vật lí PHY12 (lịch sử) | Sinh học BIO12 |
|---|---|---|
| Nguồn | `PHY12_P06_R03`, `PHY12_P07_V01`, `PHY12_P08_V01` | `BIO12_P07_T1`, `BIO12_P07_T2`, `BIO12_P07_V1` |
| Lần đầu | V1 `SOURCE_EVIDENCE_FAIL` | E37 Grounding `FAIL` |
| Sau chỉnh lý | V2 `SOURCE_EVIDENCE_PASS` | E39 Structural/Grounding/Postgen `PASS` |
| Giáo viên | `APPROVED` theo hồ sơ Vật lí lịch sử | Trương Thị Thu Hằng, `APPROVE` E41 |
| Cuối | `READY_FOR_USE` trong hồ sơ lịch sử | Engine `APPROVED`, `ready_for_use=true` |

Vật lí và Sinh học được ghi nhận ở **hai thời điểm, quy trình kiểm duyệt khác nhau**. Không sử dụng 2 trường hợp này để khẳng định tỷ lệ chính xác hay ưu thế định lượng. `ready_for_use` không đồng nghĩa `production_approved`.

## Kiểm tra độc lập, không cần Google Colab/API/Git

Tại thư mục repo:

```bash
python khkt/scripts/verify_checkpoint.py
```

Lệnh kiểm tra SHA256 của gói, CRC của các ZIP lồng nhau, SHA256 bản E42 và E10, kết quả verifier và bản ghi duyệt Sinh học, cùng trạng thái tóm tắt Vật lí. **Không chạy lại mô hình, không gọi Gemini, không sửa bằng chứng.** Có thể mở `khkt/checkpoint/BAO_CAO_DOI_CHIEU.html` để xem báo cáo; bản có đủ 6 ảnh nằm trong ZIP `VERIFIED/BAO_CAO_DOI_CHIEU.html`.

## Pipeline tái lập

1. **Replay A — Archival (khuyến nghị BTC):** checkout commit và chạy verifier ngoại tuyến ở trên. Đây là cách tái hiện kết quả đánh giá **của hồ sơ lưu trữ**, kiểm tra hash nguồn/báo cáo.
2. **Replay B — Original engine:** cần bản snapshot engine gốc, nguồn gốc đầy đủ, SourceIndex FROZEN, hợp đồng, Grounding Review, API key và quyền dùng API. Bộ checkpoint này **chưa đóng gói đầy đủ mọi phụ thuộc bên ngoài**, vì vậy không thể cam kết tái chạy toàn chuỗi E17–E41 trên máy mới chỉ từ ZIP này.
3. **Replay C — New Gemini generation:** mô hình có thể đổi, quá tải hoặc trả kết quả khác. Phải chạy lại Gate và Verification, được giáo viên duyệt mới; tuyệt đối không gán kết quả lịch sử thành kết quả tái sinh.

## Cấu trúc

- `checkpoint/evidence/EXAMTRUST_E42_VERIFIED_CROSS_SUBJECT_FINAL.zip` — gói đã xác minh bất biến.
- `checkpoint/CROSS_SUBJECT_VERIFICATION.json` — kết quả đối chiếu lưu trữ.
- `checkpoint/BAO_CAO_DOI_CHIEU.html` — báo cáo HTML tóm tắt.
- `checkpoint/MANIFEST.json` — bảng SHA256 các file đang lưu trong repo.
- `scripts/verify_checkpoint.py` — kiểm chứng tự động không dùng thư viện ngoài.
- `.github/workflows/khkt-checkpoint.yml` — quy trình CI chạy khi thay đổi thư mục `khkt/`.

## Bảo toàn chuỗi bằng chứng

Chỉ thêm checkpoint này theo commit mới. Không sửa lịch sử nguồn, không thay thế kết quả FAIL lần đầu, không tạo phê duyệt giả, không commit API key/Colab Secrets. Khi BTC kiểm tra, cung cấp hash commit Git, manifest SHA256 và báo cáo kiểm tra từ CI.
