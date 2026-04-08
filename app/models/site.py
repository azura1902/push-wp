from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)          # https://example.com
    username = Column(String, nullable=False)
    app_password = Column(String, nullable=False)  # WP Application Password
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
