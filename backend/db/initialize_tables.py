from db.session import engine
from db.tables_phase1 import Base

# Import every model module so the metadata registry includes all current
# tables. This is required when the live database is newer/older than the
# latest model definitions.
import db.tables_phase1  # noqa: F401
import db.tables_phase2  # noqa: F401


Base.metadata.create_all(bind=engine)

print("Đã tạo/đồng bộ tất cả các bảng của model hiện tại.")