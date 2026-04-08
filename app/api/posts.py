from datetime import datetime, timezone
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.post import Post
from app.models.site import Site
from app.models.keyword import Keyword
from app.models.job import Job
from app.schemas import PostRead, GenerateRequest, PublishRequest, PostDraftCreate, PostUpdate
from app.services.ai_service import generate_post
from app.services.image_service import download_images
from app.services.wp_service import WordPressClient

router = APIRouter(prefix="/posts", tags=["posts"])


def _do_publish(job_id: int):
    """Background task: thực hiện publish một Job."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        post = db.get(Post, job.post_id)
        site = db.get(Site, job.site_id)

        client = WordPressClient(site.url, site.username, site.app_password)

        # Upload ảnh nếu có
        media_id = None
        if post.featured_image_local:
            media_id = client.upload_image(post.featured_image_local)

        wp_status = "publish"
        if job.scheduled_at and job.scheduled_at > datetime.now():
            wp_status = "future"

        # Chèn YouTube embed vào cuối content nếu có
        content = post.content or ""
        if post.youtube_url:
            yt_url = post.youtube_url.strip()
            # Chuẩn hóa URL: chỉ giữ watch?v=VIDEO_ID (bỏ playlist, start_radio...)
            import re as _re
            vid_match = _re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", yt_url)
            if vid_match:
                yt_url = f"https://www.youtube.com/watch?v={vid_match.group(1)}"
            content = content + (
                f'\n\n<!-- wp:embed {{"url":"{yt_url}","type":"video",'
                f'"providerNameSlug":"youtube","responsive":true,'
                f'"className":"wp-embed-aspect-16-9 wp-has-aspect-ratio"}} -->\n'
                f'<figure class="wp-block-embed is-type-video is-provider-youtube '
                f'wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio">'
                f'<div class="wp-block-embed__wrapper">\n{yt_url}\n</div></figure>\n'
                f'<!-- /wp:embed -->'
            )

        result = client.create_post(
            title=post.title,
            content=content,
            excerpt=post.excerpt or "",
            featured_media=media_id,
            status=wp_status,
            scheduled_at=job.scheduled_at,
        )

        post.wp_post_id = result["wp_post_id"]
        post.wp_post_url = result["wp_post_url"]
        post.status = "published"
        post.published_at = datetime.now()

        job.status = "done"
        job.finished_at = datetime.now()
        db.commit()

    except Exception as e:
        if "job" in dir():
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.now()
        if "post" in dir():
            post.status = "failed"
            post.error_message = str(e)
        db.commit()
    finally:
        db.close()


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/", response_model=list[PostRead])
def list_posts(db: Session = Depends(get_db)):
    return db.query(Post).order_by(Post.id.desc()).all()


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# ------------------------------------------------------------------
# Tạo draft nhanh từ Manager (không cần keyword table)
# ------------------------------------------------------------------
@router.post("/draft", response_model=PostRead, status_code=201)
def create_draft(req: PostDraftCreate, db: Session = Depends(get_db)):
    """Tạo bài draft mới chỉ với keyword text + site + ảnh."""
    local_images: list[str] = []
    if req.fb_image_urls:
        local_images = download_images(req.fb_image_urls)

    post = Post(
        keyword_text=req.keyword_text,
        description=req.description,
        language=req.language,
        site_id=req.site_id,
        youtube_url=req.youtube_url,
        featured_image_url=req.fb_image_urls[0] if req.fb_image_urls else None,
        featured_image_local=local_images[0] if local_images else None,
        images_local_json=json.dumps(local_images) if local_images else None,
        fb_image_urls=json.dumps(req.fb_image_urls) if req.fb_image_urls else None,
        status="draft",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


# ------------------------------------------------------------------
# Cập nhật thông tin post (keyword, site, schedule, ảnh)
# ------------------------------------------------------------------
@router.put("/{post_id}", response_model=PostRead)
def update_post(post_id: int, req: PostUpdate, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if req.description is not None:
        post.description = req.description
    if req.keyword_text is not None:
        post.keyword_text = req.keyword_text
    if req.language is not None:
        post.language = req.language
    if req.site_id is not None:
        post.site_id = req.site_id
    if req.schedule_publish_at is not None:
        post.schedule_publish_at = req.schedule_publish_at
        # Nếu bài đang failed/published, reset về ready để scheduler có thể đăng lại
        if post.status in ("failed", "published"):
            post.status = "ready"
            post.error_message = None
    if req.fb_image_urls is not None:
        post.fb_image_urls = json.dumps(req.fb_image_urls)
        post.featured_image_url = req.fb_image_urls[0] if req.fb_image_urls else None
        if req.download_images:
            local_images = download_images(req.fb_image_urls)
            post.featured_image_local = local_images[0] if local_images else None
            post.images_local_json = json.dumps(local_images) if local_images else None
    if req.youtube_url is not None:
        post.youtube_url = req.youtube_url or None

    db.commit()
    db.refresh(post)
    return post


# ------------------------------------------------------------------
# Sinh nội dung cho 1 post đã có (dùng keyword_text hoặc keyword_id)
# ------------------------------------------------------------------
@router.post("/{post_id}/generate", response_model=PostRead)
def generate_for_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Xác định keyword, language, description
    keyword = post.keyword_text
    language = post.language or "vi"
    description = post.description or ""

    if not keyword and post.keyword_id:
        kw = db.get(Keyword, post.keyword_id)
        if kw:
            keyword = kw.keyword
            description = kw.description or ""
            language = kw.language

    if not keyword:
        raise HTTPException(status_code=400, detail="Post chưa có keyword")

    # Tải ảnh nếu chưa có local path
    if not post.featured_image_local and post.fb_image_urls:
        try:
            urls = json.loads(post.fb_image_urls)
            local_images = download_images(urls)
            if local_images:
                post.featured_image_local = local_images[0]
                post.images_local_json = json.dumps(local_images)
        except Exception:
            pass

    result = generate_post(keyword, description, language)
    post.title = result["title"]
    post.content = result["content"]
    post.excerpt = result["excerpt"]
    post.status = "ready"
    post.error_message = None
    db.commit()
    db.refresh(post)
    return post


@router.post("/generate", response_model=PostRead, status_code=201)
def generate_and_save(req: GenerateRequest, db: Session = Depends(get_db)):
    """Gọi AI sinh bài từ keyword, lưu vào DB với status=ready."""
    kw = db.get(Keyword, req.keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    # Sinh nội dung
    result = generate_post(kw.keyword, kw.description or "", kw.language)

    # Tải ảnh FB
    local_images: list[str] = []
    if req.facebook_image_urls:
        local_images = download_images(req.facebook_image_urls)

    featured_local = local_images[0] if local_images else None
    featured_url = req.facebook_image_urls[0] if req.facebook_image_urls else None

    post = Post(
        keyword_id=kw.id,
        site_id=req.site_id,
        title=result["title"],
        content=result["content"],
        excerpt=result["excerpt"],
        featured_image_url=featured_url,
        featured_image_local=featured_local,
        images_local_json=json.dumps(local_images) if local_images else None,
        status="ready",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/publish", status_code=202)
def publish_post(
    req: PublishRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Tạo Job đăng bài và chạy ngầm."""
    post = db.get(Post, req.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    site = db.get(Site, req.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    job = Job(post_id=post.id, site_id=site.id, scheduled_at=req.scheduled_at)
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_do_publish, job.id)
    return {"job_id": job.id, "message": "Publishing started"}


@router.delete("/{post_id}", status_code=204)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    import os as _os
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Xóa ảnh local đi kèm
    images_to_delete: list[str] = []
    if post.featured_image_local:
        images_to_delete.append(post.featured_image_local)
    if post.images_local_json:
        try:
            extra = json.loads(post.images_local_json)
            images_to_delete.extend(extra)
        except Exception:
            pass
    for img_path in set(images_to_delete):
        try:
            if img_path and _os.path.isfile(img_path):
                _os.remove(img_path)
        except Exception:
            pass

    db.delete(post)
    db.commit()
