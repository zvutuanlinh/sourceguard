# EXAMTRUST AI – SOURCEGUARD
## Hồ sơ nghiên cứu KHKT Hà Nội, năm học 2026–2027

### 1. Thông tin dự án
Tên dự án: ExamTrust AI – SourceGuard.

Định hướng: Hỗ trợ xây dựng nguồn học liệu có thể truy xuất,
kiểm soát chất lượng cấu trúc tài liệu và hỗ trợ giáo viên
trong quá trình tạo, đánh giá câu hỏi.

Đây là nhánh hồ sơ dành riêng cho cuộc thi KHKT Hà Nội
năm học 2026–2027.

### 2. Cơ sở phát triển
Dự án kế thừa các thành phần và kinh nghiệm nghiên cứu
từ ExamTrust AI đã tham gia cuộc thi AI trước đây.

Các kết quả lịch sử, checkpoint đóng băng và bằng chứng
đạt giải không được thay đổi hoặc diễn giải lại.

### 3. Kiến trúc xử lý
Quy trình nền SourceGuard:

Container -> Object -> ReadingRegion -> Anchor
-> ReadingLane -> RegionGrowing -> Validation -> Render

Bản thí điểm mở rộng gồm:
- Phát hiện ứng viên Text và Visual từ ảnh PNG.
- Graphic Gate thử nghiệm để bảo vệ ứng viên hình có
  cấu trúc đồ họa trước bước loại đoạn văn.
- Loại vùng Text trùng lặp.
- Xử lý các thành phần trang trí và chân trang.
- Tách caption khỏi vùng Text.
- Liên kết caption với Visual V2.
- Giữ core_bbox riêng và full_bbox gồm caption.
- Xuất JSON, ảnh phân đoạn và bằng chứng SHA256.

### 4. Thử nghiệm Sinh học 12, trang 7
Dữ liệu đầu vào: 01 trang sách giáo khoa dạng PNG.

Kết quả thí điểm:
- 02 vùng văn bản cuối.
- 02 vùng hình ảnh cuối.
- Caption Hình 1.3 được liên kết với Visual V2.
- Hai lần chạy Replay độc lập tạo JSON và ảnh giống nhau.

Đây là kết quả thử nghiệm trên một trang, không phải
chứng minh chất lượng tổng quát trên mọi môn học.

### 5. Tái lập
Chạy trong môi trường Python có các thư viện cần thiết:

python code/replay.py \
  --input source/input.png \
  --output outputs/NEW_RUN \
  --code-dir code

Thư mục outputs/NEW_RUN không được tồn tại trước khi chạy.

Các kết quả chạy mẫu nằm trong:
- outputs/RUN_01
- outputs/RUN_02

Minh chứng kiểm chứng nằm tại:
- evidence/REPLAY_VERIFICATION.json
- SHA256_MANIFEST.json

### 6. Phạm vi đã xác minh
Đã xác minh:
- Tái lập kết quả trên ảnh Sinh học 12 trang 7.
- Hai lần Replay cho kết quả giống nhau.
- Liên kết hình học caption với V2.
- Mã nguồn nền được bảo toàn.

Chưa xác minh:
- Hồi quy toàn bộ các trang Vật lí nghiệm thu.
- Chất lượng tổng quát trên nhiều trang/môn học.
- Chạy trên môi trường BTC độc lập.
- Chất lượng câu hỏi sinh tự động từ trang Sinh học.

### 7. Question Generation
Sinh câu hỏi phải tuân thủ cơ chế kiểm tra nguồn,
Human Component Review và các bước phê duyệt liên quan.

Kết quả phân đoạn trang Sinh học không tự động
cấp quyền phát hành câu hỏi.

Bộ kiểm thử câu hỏi mức nhận biết sẽ được bổ sung
sau khi xác minh module QG và nguồn được phê duyệt.

### 8. Quy tắc bảo toàn lịch sử
Không thay đổi:
- Hai repository lịch sử.
- Nhánh main và các tag nghiệm thu.
- Frozen checkpoint và governance.
- Minh chứng giải thưởng trước đây.

Mọi cải tiến của cuộc thi KHKT được phát triển
trong nhánh riêng và có lịch sử Git riêng.

### 9. Trạng thái
REPLAY_PILOT: PASS
PHYSICS_REGRESSION: PENDING
QUESTION_GENERATION: PENDING
PRODUCTION_APPROVAL: HOLD
BTC_INDEPENDENT_REPLAY: PENDING
