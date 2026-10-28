# KHKT E42 – Hướng dẫn kiểm chứng

Đây là checkpoint bổ sung, không thay thế replay thí điểm hoặc checkpoint lịch sử.

## Kiểm tra offline

Từ thư mục gốc repository, chạy:

```bash
python competitions/khkt_hanoi_2026_2027/checkpoints/KHKT_E42_BIO_PHY_20261028/scripts/verify_checkpoint.py
```

Kết quả PASS xác nhận tính toàn vẹn của bằng chứng và các trạng thái đã ghi.

## Giới hạn

- Không gọi Gemini.
- Không tái sinh câu hỏi từ đầu.
- Không tái chạy lịch sử Vật lí.
- Không chứng minh chất lượng tổng quát.
- Không đồng nghĩa phê duyệt triển khai sản phẩm.

Để tái sinh từ đầu cần snapshot engine, SourceIndex FROZEN, ảnh nguồn, môi trường và quyền truy cập Gemini tương ứng.
