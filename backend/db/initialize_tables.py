from db.session import engine
from db.tables_phase1 import Base


Base.metadata.create_all(engine)

print("Đã tạo tất cả các bảng.")