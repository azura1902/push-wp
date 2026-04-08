from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import init_db
from app.api import sites, keywords, posts, jobs
from app.scheduler.tasks import start_scheduler, stop_scheduler

app = FastAPI(
    title="Push-WP API",
    description="Hệ thống đăng bài WordPress tự động với AI",
    version="1.0.0",
)

# Serve ảnh đã tải
Path("static/images").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(sites.router, prefix="/api")
app.include_router(keywords.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


@app.get("/")
def root():
    return {"message": "Push-WP API is running", "docs": "/docs"}
