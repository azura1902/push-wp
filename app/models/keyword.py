from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False)
    description = Column(Text, nullable=True)       # Hướng viết thêm (tùy chọn)
    language = Column(String, default="vi")         # vi / en
    created_at = Column(DateTime, server_default=func.now())
