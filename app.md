# Luồng giao diện

Tài liệu này mô tả các trang HTML, điều hướng chính và cách các luồng người
dùng phối hợp với API. Frontend là HTML/CSS/JavaScript tĩnh; xác thực dựa trên
session cookie do backend FastAPI quản lý. Tổng quan dự án và hướng dẫn chạy
ứng dụng nằm trong [README.md](./README.md); schema và cách lưu dữ liệu nằm
trong [database.md](./database.md).

## Các trang chính

| Trang | Đường dẫn | Mục đích |
|---|---|---|
| Đăng nhập | `frontend/modules/login.html` | Đăng nhập và tạo phiên làm việc |
| Đăng ký | `frontend/modules/register.html` | Tạo tài khoản người dùng |
| Tài khoản | `frontend/modules/index.html` | Xem hồ sơ, sửa tên, xem feed bài nộp toàn server và mở các khu vực khác |
| Kho bài tập | `frontend/modules/problems.html` | Tìm bài public; admin còn có danh sách bài do mình tạo |
| Làm bài | `frontend/modules/problem_submit.html` | Đọc đề và nộp lời giải trong bố cục hai cột |
| Lịch sử bài nộp | `frontend/modules/submissions.html` | Xem lịch sử toàn server và lịch sử lọc theo bài/người |
| Lớp học | `frontend/modules/classroom.html` | Khám phá/tham gia lớp, xem bài và contest được giao, nộp bài trong lớp |
| Đề bài lớp học | `frontend/modules/problem_statement.html` | Mở riêng đề được giao trong lớp |
| Tạo/chỉnh sửa bài | `frontend/modules/create_problem.html` | Quản lý đề, giới hạn chấm và testcase của admin |
| Quản trị judge | `frontend/modules/judge_admin.html` | Quản lý lớp, contest, bài tập và quyền liên quan |
| Quản lý tài khoản | `frontend/modules/manage_accounts.html` | Quản lý tài khoản dành cho super admin |

Mọi trang cần đăng nhập sẽ chuyển người dùng chưa xác thực về trang đăng nhập.
Các thao tác quản trị được hiển thị theo vai trò và vẫn được backend kiểm tra
quyền; ẩn thành phần frontend không thay thế kiểm tra phân quyền phía server.

## Luyện tập bài public

```text
Kho bài tập
  ├─ lọc theo tên hoặc problem_id
  └─ chọn tên bài
       └─ problem_submit.html?problem_id=<id>&source=public
            ├─ đề bài ở nửa trái
            ├─ ngôn ngữ, mã nguồn và nút nộp ở nửa phải
            └─ liên kết lịch sử của bài
                 └─ submissions.html?problem_id=<id>
```

Trang kho bài tập giữ danh sách gọn, có ô lọc. Trang làm bài chia ngang thành
hai cột trên màn hình rộng: đề bên trái và form nộp bên phải. Trên màn hình
hẹp, hai cột xếp thành một cột.

Form lấy danh sách ngôn ngữ từ backend, gửi mã nguồn lên API chấm Judge0 và
hiển thị verdict, điểm, số testcase qua/tổng, runtime và bộ nhớ. Trang không
hiển thị feed bài nộp toàn server; dùng trang lịch sử riêng khi cần xem lịch sử.

## Bài private và bài của admin

- Bài public được mở từ kho bài tập với `source=public`.
- Admin có thể mở bài mình quản lý với `source=owner`. Chỉ chủ bài hoặc super
  admin có quyền đọc/chỉnh sửa testcase qua các API quản trị.
- Trang làm bài không cho nộp trực tiếp bài private. Bài private được nộp từ
  form trong ngữ cảnh lớp học được giao.
- Trong lớp, liên kết xem đề mở
  `problem_statement.html?problem_id=<id>&source=class&class_id=<id>`.
  Quyền truy cập lớp và việc bài có được giao trong lớp được backend xác minh.

## Lịch sử bài nộp

`frontend/modules/submissions.html` là trang lịch sử dùng lại được. Query
parameters có thể truyền trực tiếp trong URL:

| Tham số | Ý nghĩa |
|---|---|
| `problem_id` | Chỉ lấy bài nộp thuộc bài tập này |
| `account_id` | Chỉ lấy bài nộp của tài khoản này |

Ví dụ:

```text
modules/submissions.html
modules/submissions.html?problem_id=42
modules/submissions.html?account_id=7
modules/submissions.html?problem_id=42&account_id=7
```

Khi URL có ít nhất một bộ lọc, trang hiển thị kết quả lọc và đồng thời giữ
một feed **Bài nộp toàn server** độc lập, không bị lọc. Hai feed nằm cạnh nhau
trên màn hình đủ rộng; ở màn hình hẹp chúng xếp dọc. Mỗi feed phân trang riêng
và có nút tải các lượt cũ hơn. Form lọc trên trang cập nhật query parameters
khi gửi; nút xóa bộ lọc trở về trang không có query.

Feed toàn server hiển thị trạng thái của bài public và private cho người dùng
đã đăng nhập. Metadata gồm người nộp, bài, trạng thái và các chỉ số chấm; API
không trả mã nguồn trong danh sách. Nút xem mã chỉ có ở bài nộp của chính
người dùng, và endpoint lấy mã nguồn cũng xác minh quyền sở hữu.

## Dashboard và lớp học

- Dashboard có feed bài nộp toàn server dạng phân trang.
- Trang lớp hiển thị bài tập/contest theo lớp đang chọn và một feed lịch sử chỉ
  gồm các bài nộp được ghi nhận trong lớp đó. API yêu cầu người dùng là thành
  viên lớp; mã nguồn chỉ người nộp xem được.
- Lượt nộp public từ kho bài tập không gắn với lớp. Các lượt cũ không có thông
  tin lớp đáng tin cậy sẽ không được gán vào feed lớp một cách suy đoán.
- Admin lớp quản lý thành viên, yêu cầu tham gia, bài được giao và contest theo
  quyền của lớp.

## Điều hướng liên quan

Các trang tài khoản, kho bài tập và lớp học có liên kết đến trang lịch sử.
Trang làm bài có liên kết đến lịch sử riêng của bài đang mở; không đặt thêm
nút feed toàn server trong form nộp bài. Trang lịch sử luôn có feed toàn
server của riêng nó.
