# Online Judge

Ứng dụng luyện tập lập trình và tổ chức lớp/contest, gồm frontend HTML/CSS/JS,
API FastAPI, PostgreSQL và dịch vụ chấm Judge0.

## Tài liệu

- [app.md](./app.md): tính năng, giao diện và luồng thao tác người dùng.
- [database.md](./database.md): bảng, quan hệ, ràng buộc, migration và dữ liệu lưu.
- [backend.md](./backend.md): API, phân quyền, cấu hình, tích hợp và vận hành backend.

## Chạy local nhanh

Điều kiện: PostgreSQL và Python environment trong `backend/.venv` đã sẵn sàng;
các biến cấu hình backend được đặt trong `backend/.env`.

Terminal 1 — backend và migration:

```bash
cd backend
PYTHONPATH=. .venv/bin/python db/initialize_tables.py
PYTHONPATH=. .venv/bin/python db/migrate_judge_admin.py
PYTHONPATH=. .venv/bin/python -m src.serve
```

Terminal 2 — frontend:

```bash
python3 -m http.server 5500 --bind 0.0.0.0 --directory frontend
```

Mở `http://localhost:5500`. API mặc định ở `http://localhost:8000`; tài liệu
OpenAPI tại `/docs`. Hướng dẫn cấu hình, truy cập LAN và kiểm thử nằm
trong [backend.md](./backend.md).

> Migration judge xóa bảng cũ `solution` và dữ liệu trong bảng đó. Chi tiết
> schema và migration xem [database.md](./database.md).
