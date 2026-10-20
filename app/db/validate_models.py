from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401
from app.db.base import Base

configure_mappers()

print("All SQLAlchemy relationships configured successfully.")
print(f"Registered tables: {len(Base.metadata.tables)}")

for table_name in sorted(Base.metadata.tables):
    print(f"- {table_name}")