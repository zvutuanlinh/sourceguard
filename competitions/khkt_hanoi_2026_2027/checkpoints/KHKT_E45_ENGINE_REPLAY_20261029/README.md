# KHKT E45 - Engine Replay Checkpoint

## Mục đích

Lưu bản sao engine, SourceIndex FROZEN, trang ảnh nguồn
và đầu vào đã được kiểm duyệt để tái kiểm chứng câu hỏi BIO12.

Đây là checkpoint bổ sung cho E44, không thay thế
checkpoint E42 hay kết quả replay KHKT trước đó.

## Cách kiểm tra

1. Kiểm tra SHA256 và CRC trong REPLAY_MANIFEST.json.
2. Giải nén archive vào thư mục làm việc độc lập.
3. Khôi phục môi trường Python và các tệp nguồn tại
   đúng đường dẫn mà SourceIndex bất biến tham chiếu.
4. Nạp engine từ REPLAY/engine.
5. Nạp SourceIndex từ REPLAY/frozen_index.
6. Sao chép REPLAY/replay_input ra working directory.
7. Gọi Pipeline.verify('QC_PILOT_01', llm_cross_check=False)
   với LLM bị vô hiệu hóa và kiểm tra verdict PASS.
8. Không chạy decide(APPROVE) để tạo phê duyệt giả;
   đối chiếu quyết định E41 nguyên bản trong checkpoint E44.

## Giới hạn

- E45 đã chạy một lượt verifier gốc trong Colab và ghi kết quả.
- SourceIndex và mã engine được giữ nguyên, không sửa governance.
- Các đường dẫn nguồn tuyệt đối cần được khôi phục đúng khi
  chuyển sang máy khác; SOURCE_PATH_MAP.json ghi các ánh xạ.
- Chưa chứng nhận tự động portable trên máy sạch.
- Chưa tái sinh câu hỏi bằng Gemini.
- Việc gọi API mới không bảo đảm đầu ra giống lịch sử.
- Không đồng nghĩa phê duyệt triển khai sản phẩm chính thức.
