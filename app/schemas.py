from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class SiteCreate(BaseModel):
    name: str
    url: str
    username: str
    app_password: str
    is_active: bool = True


class SiteRead(BaseModel):
    id: int
    name: str
    url: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KeywordCreate(BaseModel):
    keyword: str
    description: Optional[str] = None
    language: str = "vi"


class KeywordRead(BaseModel):
    id: int
    keyword: str
    description: Optional[str]
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PostRead(BaseModel):
    id: int
    keyword_id: Optional[int]
    keyword_text: Optional[str]
    description: Optional[str]
    language: Optional[str]
    site_id: Optional[int]
    title: Optional[str]
    content: Optional[str]
    excerpt: Optional[str]
    featured_image_url: Optional[str]
    featured_image_local: Optional[str]
    images_local_json: Optional[str]
    fb_image_urls: Optional[str]
    youtube_url: Optional[str]
    wp_post_id: Optional[int]
    wp_post_url: Optional[str]
    schedule_publish_at: Optional[datetime]
    status: str
    error_message: Optional[str]
    created_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}


# Tạo draft mới trực tiếp từ manager (không cần keyword table)
class PostDraftCreate(BaseModel):
    keyword_text: str
    description: Optional[str] = None
    language: str = "vi"
    site_id: Optional[int] = None
    fb_image_urls: Optional[list[str]] = None
    youtube_url: Optional[str] = None


# Cập nhật draft (keyword, site, schedule, images)
class PostUpdate(BaseModel):
    keyword_text: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    site_id: Optional[int] = None
    schedule_publish_at: Optional[datetime] = None
    fb_image_urls: Optional[list[str]] = None
    download_images: bool = False   # True = tải ảnh về luôn khi update
    youtube_url: Optional[str] = None


# Request cũ (giữ backward compat)
class GenerateRequest(BaseModel):
    keyword_id: int
    site_id: Optional[int] = None
    facebook_image_urls: Optional[list[str]] = None


class PublishRequest(BaseModel):
    post_id: int
    site_id: int
    scheduled_at: Optional[datetime] = None


class JobRead(BaseModel):
    id: int
    post_id: int
    site_id: int
    status: str
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
