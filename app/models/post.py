from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)

    # Keyword nhập inline (không cần qua bảng keywords)
    keyword_text = Column(String, nullable=True)
    description = Column(Text, nullable=True)          # Hướng dẫn thêm cho AI
    language = Column(String, default="vi")            # vi / en
    fb_image_urls = Column(Text, nullable=True)        # JSON list URLs gốc từ FB

    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)
    featured_image_url = Column(String, nullable=True)
    featured_image_local = Column(String, nullable=True)
    images_local_json = Column(Text, nullable=True)

    # WordPress response
    wp_post_id = Column(Integer, nullable=True)
    wp_post_url = Column(String, nullable=True)

    # YouTube video embed
    youtube_url = Column(String, nullable=True)

    # Lên lịch tự động đăng
    schedule_publish_at = Column(DateTime, nullable=True)

    # draft | ready | publishing | published | failed
    status = Column(String, default="draft")
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    published_at = Column(DateTime, nullable=True)
