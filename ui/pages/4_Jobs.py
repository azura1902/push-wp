import streamlit as st
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")
API = os.getenv("API_BASE_URL", "http://localhost:8000")

st.title("📋 Publish Jobs")

STATUS_COLOR = {
    "pending": "🟡",
    "running": "🔵",
    "done": "🟢",
    "failed": "🔴",
}

if st.button("🔄 Làm mới"):
    st.rerun()

try:
    jobs = requests.get(f"{API}/api/jobs/", timeout=10).json()
    posts = {p["id"]: p for p in requests.get(f"{API}/api/posts/", timeout=10).json()}
    sites = {s["id"]: s["name"] for s in requests.get(f"{API}/api/sites/", timeout=10).json()}
except Exception:
    st.error("Không kết nối được backend.")
    st.stop()

if not jobs:
    st.info("Chưa có job nào.")
else:
    for job in jobs:
        icon = STATUS_COLOR.get(job["status"], "⚪")
        post = posts.get(job["post_id"], {})
        site_name = sites.get(job["site_id"], str(job["site_id"]))
        post_title = post.get("title", f"Post #{job['post_id']}")

        col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 2])
        col1.markdown(f"{icon} **{job['id']}**")
        col2.markdown(f"{post_title[:60]}")
        col3.text(site_name)
        col4.text(job["status"])
        col5.caption(str(job.get("finished_at") or job.get("started_at") or job["created_at"])[:19])

        if job.get("error_message"):
            st.error(f"Job #{job['id']} — {job['error_message']}")

        if post.get("wp_post_url"):
            st.markdown(f"🔗 [Xem bài đã đăng]({post['wp_post_url']})")
