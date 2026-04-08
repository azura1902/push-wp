from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")


def _check_and_publish():
    """Chạy mỗi phút: tìm post đến lịch đăng và publish."""
    from app.database import SessionLocal
    from app.models.post import Post
    from app.models.job import Job

    db = SessionLocal()
    try:
        # So sánh naive local time – đúng với giờ user nhập vào
        now = datetime.now()
        due_posts = (
            db.query(Post)
            .filter(
                Post.schedule_publish_at <= now,
                Post.status == "ready",
                Post.site_id.isnot(None),
            )
            .all()
        )

        print(f"[scheduler] tick @ {now.strftime('%H:%M:%S')} – {len(due_posts)} bài cần đăng")

        for post in due_posts:
            post.status = "publishing"
            db.commit()

            job = Job(post_id=post.id, site_id=post.site_id, scheduled_at=post.schedule_publish_at)
            db.add(job)
            db.commit()
            db.refresh(job)

            from app.api.posts import _do_publish
            _do_publish(job.id)

    except Exception as e:
        print(f"[scheduler] error: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(_check_and_publish, "interval", minutes=1, id="auto_publish", replace_existing=True)
        scheduler.start()
        print("[scheduler] started — checking every 1 minute")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
