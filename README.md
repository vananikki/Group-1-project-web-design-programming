# 🛒 [Tên Dự Án] - E-Commerce Platform

> **Môn học:** Web Design and Programming  
> **Kiến trúc:** Client-Server decoupled (Vanilla Frontend + FastAPI Backend RESTful API)  
> **Nhóm thực hiện:** Group 1   
> **Giảng viên hướng dẫn:** [Tên giảng viên]

---

## 📌 1. Giới Thiệu & Mục Tiêu Dự Án
Hệ thống thương mại điện tử trực tuyến cho phép người dùng tìm kiếm, xem chi tiết, quản lý giỏ hàng và đặt mua sản phẩm. Ứng dụng xây dựng theo chuẩn kiến trúc Web hiện đại:
- **Frontend độc lập:** Viết bằng HTML5 chuẩn ngữ nghĩa (Semantic & Accessibility), CSS3 Responsive (Grid/Flexbox) và Vanilla JS xử lý DOM/Async Fetch.
- **Backend API:** FastAPI hiệu năng cao, quản lý quan hệ thực thể với SQLModel & PostgreSQL, tích hợp xác thực JWT, Dependency Injection và Auto-generated Swagger Docs.

---

## 🛠️ 2. Công Nghệ Sử Dụng (Tech Stack)

| Tầng | Công nghệ / Thư viện | Ghi chú kỹ thuật |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+) | Semantic tags, ARIA attributes, Flexbox/Grid, Responsive Mobile-first, DOM API, Fetch API / AJAX |
| **Backend** | Python 3.11+, FastAPI, Uvicorn | Pydantic validation, FastAPI Routing, Middlewares, Dependency Injection |
| **Database & ORM** | PostgreSQL, SQLModel | Data Modeling, Foreign Keys, Relationships, Migrations (Alembic) |
| **Auth & Security** | Passlib (Bcrypt), PyJWT, OAuth2PasswordBearer | Hashing mật khẩu, JWT Token, Role-based Access (Customer/Admin), Session Middleware |
| **Testing & Docs** | Pytest, HTTPX, FastAPI TestClient, Swagger UI | REST API auto-docs (`/docs`), Unit Test & Integration Test |
| **Deployment** | Docker, Uvicorn, Render / Railway / Docker Compose | Môi trường container hóa phục vụ Production |

---

## 📂 3. Cấu Trúc Thư Mục (Project Architecture)

```text
├── frontend/                   # Frontend tĩnh (HTML5, CSS3, Vanilla JS)
│   ├── index.html              # Trang chủ & danh sách sản phẩm
│   ├── product-detail.html     # Chi tiết sản phẩm & đánh giá
│   ├── cart.html               # Giỏ hàng & thanh toán
│   ├── admin.html              # Trang quản trị sản phẩm & đơn hàng
│   ├── css/
│   │   ├── base.css            # Reset, biến CSS, typography
│   │   ├── layout.css          # Grid, Flexbox, Responsive rules
│   │   └── components.css      # Card, button, modal, form
│   └── js/
│       ├── api.js              # Wrapper hàm fetch() gọi Backend REST API
│       ├── auth.js             # Quản lý token, trạng thái đăng nhập
│       ├── app.js              # Xử lý DOM, render dữ liệu, event listeners
│       └── cart.js             # Quản lý state giỏ hàng (LocalStorage + API sync)
│
├── backend/                    # FastAPI Backend Service
│   ├── app/
│   │   ├── core/               # Cấu hình môi trường, bảo mật (security.py, config.py)
│   │   ├── db/                 # Kết nối DB engine, session factory (database.py)
│   │   ├── models/             # SQLModel schemas (User, Product, Order, OrderItem)
│   │   ├── routers/            # API Endpoints chia module (auth, products, orders)
│   │   ├── middlewares/        # Custom logging, CORS, session middlewares
│   │   ├── dependencies/       # Dependency Injection (get_db, get_current_user)
│   │   └── main.py             # Entrypoint FastAPI app
│   ├── tests/                  # Kiểm thử tự động (pytest, test_client)
│   ├── requirements.txt        # Thư viện Python
│   └── Dockerfile              # Containerize Backend
│
├── .gitignore
├── docker-compose.yml          # Triển khai FastAPI + PostgreSQL một lệnh
└── README.md

## ✨ 4. Tính Năng Chi Tiết (Detailed Features & Technical Implementation)

Hệ thống được thiết kế theo kiến trúc Client-Server tách rời, bám sát các chuẩn kỹ thuật trong chương trình môn học:

### 4.1. Phía Khách Hàng (Customer Experience)

* **Semantic UI & Accessibility (HTML5/CSS3 - Tuần 2 & 3):**
  * Giao diện bố cục chuẩn Semantic Web: `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`.
  * Hỗ trợ Accessibility (A11y): Thuộc tính `aria-label`, `aria-expanded`, thẻ `label` liên kết chặt chẽ với `input`, văn bản thay thế `alt` cho toàn bộ hình ảnh sản phẩm.
  * Thiết kế Responsive: Hệ thống Layout sử dụng CSS Grid (danh mục, lưới sản phẩm) và Flexbox (thanh điều hướng, thẻ sản phẩm, footer), tối ưu hiển thị mượt mà trên Mobile, Tablet và Desktop.

* **Khám phá Sản phẩm & Tải bất đồng bộ (DOM & Fetch/AJAX - Tuần 4 & 5):**
  * **Render dữ liệu động:** Sử dụng JavaScript DOM API để khởi tạo và cập nhật danh sách thẻ sản phẩm (Card) từ dữ liệu API.
  * **Bộ lọc không tải lại trang (Single-Page Experience):** Lọc theo khoảng giá, phân loại danh mục và sắp xếp (giá tăng/giảm, mới nhất) thông qua `fetch()` bất đồng bộ (`async/await`), hiển thị trạng thái Loading Skeleton trong lúc chờ phản hồi.
  * **Tìm kiếm Real-time (Debounce Search):** Kỹ thuật trì hoãn gửi request khi người dùng nhập từ khóa tìm kiếm, giảm tải số lượng query đến Backend.

* **Giỏ Hàng & Đặt Hàng (Cart & Checkout Flow):**
  * **Quản lý trạng thái giỏ hàng (Cart State):** Lưu trữ giỏ hàng tạm thời ở `LocalStorage` đối với khách vãng lai và đồng bộ tự động với Database sau khi đăng nhập.
  * **Tương tác trực quan:** Tăng/giảm số lượng sản phẩm, tự động tính toán tổng tiền, VAT và phí giao hàng trực tiếp trên giao diện.
  * **Xác thực biểu mẫu (Client-side Validation):** Kiểm tra tính hợp lệ của số điện thoại, email, địa chỉ nhận hàng bằng Regex và Event Listener trước khi gửi đơn.

* **Tài khoản & Lịch sử Đơn hàng:**
  * Xem trạng thái các đơn hàng cá nhân (Chờ xử lý, Đang giao, Hoàn tất, Đã hủy).
  * Chi tiết hóa đơn: Danh sách mặt hàng, số tiền, ngày tạo đơn và địa chỉ nhận hàng.

---

### 4.2. Phía Quản Trị Viên (Admin Management)

* **Bảng điều khiển & Thống kê (Dashboard Analytics):**
  * Thống kê tổng doanh thu, số lượng đơn hàng mới, số lượng khách hàng đăng ký và cảnh báo mặt hàng sắp hết hàng trong kho.
* **Quản lý Danh mục & Sản phẩm (Product CRUD):**
  * Thêm mới sản phẩm có đính kèm ảnh đại diện (hỗ trợ Image URL hoặc tải file qua `UploadFile` của FastAPI).
  * Chỉnh sửa thông tin, cập nhật giá bán, số lượng tồn kho (Inventory tracking).
  * Xóa/vô hiệu hóa hiển thị sản phẩm (Soft Delete).
* **Quản lý Đơn hàng (Order Processing):**
  * Xem danh sách đơn hàng toàn hệ thống với bộ lọc trạng thái.
  * Cập nhật tiến độ đơn hàng theo chu trình: `Pending` ➔ `Confirmed` ➔ `Shipping` ➔ `Completed` / `Cancelled`.

---

### 4.3. Kiến Trúc Backend & Kỹ Thuật Hệ Thống (Backend Architecture)

* **RESTful API & Routing (FastAPI - Tuần 6 & 7):**
  * Phân chia Router mô-đun hóa: `/api/v1/auth`, `/api/v1/products`, `/api/v1/categories`, `/api/v1/orders`.
  * Chuẩn hóa Request/Response thông qua Pydantic Schemas (`UserCreate`, `ProductRead`, `OrderResponse`), tự động kiểm tra kiểu dữ liệu và sinh mã lỗi chuẩn 422 Unprocessable Entity.

* **Middlewares & Context (Tuần 8):**
  * **CORS Middleware:** Cấu hình nguồn gốc hợp lệ (`allow_origins`), method và headers để Frontend giao tiếp an toàn với API.
  * **Process Time Middleware:** Gắn header `X-Process-Time` vào mọi response để theo dõi hiệu năng xử lý request của server.
  * **Exception Handling Middleware:** Bắt và chuẩn hóa các ngoại lệ nội bộ (500) thành thông báo JSON thân thiện với Client.

* **Cơ sở Dữ liệu & Mô hình Quan hệ (PostgreSQL + SQLModel - Tuần 9):**
  * Thiết kế bảng quan hệ chặt chẽ:
    * `User` (1) ── (N) `Order`
    * `Category` (1) ── (N) `Product`
    * `Order` (N) ── (M) `Product` (thông qua bảng liên kết `OrderItem`).
  * Khóa ngoại (`foreign_key`), kiểm tra ràng buộc (Constraint) và xử lý Transaction khi tạo đơn: Đảm bảo số lượng hàng tồn kho được trừ đồng thời với việc tạo `Order` và `OrderItem`.

* **Xác thực, Phân quyền & Bảo mật (Auth & Security - Tuần 11):**
  * Băm mật khẩu một chiều an toàn bằng thuật toán `bcrypt` (`passlib`).
  * Cơ chế cấp phát và giải mã **JWT Token (JSON Web Token)** với thời gian hết hạn (`exp`).
  * **Dependency Injection & RBAC:**
    * `get_current_user`: Dependency trích xuất và xác thực Token từ Header `Authorization: Bearer <token>`.
    * `require_admin_role`: Dependency chặn truy cập trái phép vào các endpoint CRUD sản phẩm và quản lý đơn hàng.

* **Kiểm Thử & Tài liệu API (Testing & Auto-docs - Tuần 10):**
  * Tài liệu tương tác tự động chuẩn OpenAPI tại `/docs` (Swagger UI) và `/redoc`.
  * Bộ test tự động viết bằng `pytest` và `httpx.AsyncClient` kiểm thử các luồng quan trọng: Đăng ký/Đăng nhập, Tạo sản phẩm và Quy trình đặt hàng.
