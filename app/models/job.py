from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)

    # pending | running | done | failed
    status = Column(String, default="pending")
    scheduled_at = Column(DateTime, nullable=True)   # None = đăng ngay
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
