from session import engine
from tables import Base


Base.metadata.create_all(engine)

print("Đã tạo tất cả các bảng.")