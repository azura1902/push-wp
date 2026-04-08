import streamlit as st

st.set_page_config(
    page_title="Push-WP Dashboard",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
API = os.getenv("API_BASE_URL", "http://localhost:8000")

# ──────────────────────────────────────────────────────────────────
# Load data (cached)
# ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def fetch_posts():
    return requests.get(f"{API}/api/posts/", timeout=5).json()

@st.cache_data(ttl=60, show_spinner=False)
def fetch_sites():
    return requests.get(f"{API}/api/sites/", timeout=5).json()

@st.cache_data(ttl=30, show_spinner=False)
def fetch_jobs():
    return requests.get(f"{API}/api/jobs/",  timeout=5).json()

try:
    posts = fetch_posts()
    sites = fetch_sites()
    jobs  = fetch_jobs()
    backend_ok = True
except Exception:
    posts, sites, jobs = [], [], []
    backend_ok = False

# ──────────────────────────────────────────────────────────────────
# Header + quick metrics (full width)
# ──────────────────────────────────────────────────────────────────
st.title("📊 Dashboard – Push-WP")

if not backend_ok:
    st.error("❌ Không kết nối được Backend. Hãy chạy: `uvicorn app.main:app --reload`")
    st.stop()

total   = len(posts)
drafts  = sum(1 for p in posts if p["status"] == "draft")
ready   = sum(1 for p in posts if p["status"] == "ready")
done    = sum(1 for p in posts if p["status"] == "published")
failed  = sum(1 for p in posts if p["status"] == "failed")
sched   = sum(1 for p in posts if p.get("schedule_publish_at") and p["status"] == "ready")

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("🗂️ Tổng bài",     total)
m2.metric("🟡 Nháp",         drafts)
m3.metric("🔵 Sẵn sàng",     ready)
m4.metric("⏰ Đã lên lịch",  sched)
m5.metric("🟢 Đã đăng",      done)
m6.metric("🔴 Thất bại",     failed)

st.divider()

# site_map dùng chung cho cả hai cột
site_map = {s["id"]: s["name"] for s in sites}

# ──────────────────────────────────────────────────────────────────
# Hai cột chính: bảng gần đây (trái) + biểu đồ (phải)
# ──────────────────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="large")

# ── Cột trái: bài viết gần đây + jobs gần đây ──
with left:
    st.subheader("📝 Bài viết gần đây")
    if posts:
        STATUS_ICON = {"draft":"🟡","ready":"🔵","publishing":"🔄","published":"🟢","failed":"🔴"}
        rows = []
        for p in posts[:10]:
            rows.append({
                "": STATUS_ICON.get(p["status"], "⚪"),
                "Keyword": (p.get("keyword_text") or p.get("title") or "—")[:45],
                "Site": site_map.get(p.get("site_id"), "—"),
                "Trạng thái": p["status"],
                "Lịch đăng": str(p.get("schedule_publish_at") or "")[:16],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có bài viết nào. Vào Manager để thêm.")

    st.subheader("⚙️ Jobs gần đây")
    if jobs:
        job_rows = []
        post_map = {p["id"]: p for p in posts}
        for j in jobs[:8]:
            post = post_map.get(j["post_id"], {})
            job_rows.append({
                "Job": j["id"],
                "Bài": (post.get("keyword_text") or post.get("title") or f"#{j['post_id']}")[:40],
                "Trạng thái": j["status"],
                "Thời gian": str(j.get("finished_at") or j.get("started_at") or j["created_at"])[:16],
            })
        st.dataframe(pd.DataFrame(job_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có job nào.")

# ── Cột phải: biểu đồ ──
with right:
    st.subheader("📈 Trạng thái bài viết")

    # Pie chart trạng thái
    status_counts = {}
    for p in posts:
        status_counts[p["status"]] = status_counts.get(p["status"], 0) + 1

    if status_counts:
        df_status = pd.DataFrame(
            {"Trạng thái": list(status_counts.keys()),
             "Số bài": list(status_counts.values())}
        )
        st.bar_chart(df_status.set_index("Trạng thái"), use_container_width=True)
    else:
        st.caption("Chưa có dữ liệu.")

    st.subheader("📅 Bài đăng theo ngày")

    # Line chart số bài published theo ngày (30 ngày gần nhất)
    published_posts = [p for p in posts if p.get("published_at")]
    if published_posts:
        date_counts = {}
        for p in published_posts:
            day = str(p["published_at"])[:10]
            date_counts[day] = date_counts.get(day, 0) + 1

        # Fill ngày trống trong 14 ngày gần nhất
        today = datetime.now()
        all_days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
        df_timeline = pd.DataFrame({
            "Ngày": all_days,
            "Bài đăng": [date_counts.get(d, 0) for d in all_days],
        }).set_index("Ngày")
        st.line_chart(df_timeline, use_container_width=True)
    else:
        st.caption("Chưa có bài đã đăng.")

    st.subheader("🌐 Phân bổ theo Site")
    if posts and sites:
        site_post_count = {}
        for p in posts:
            name = site_map.get(p.get("site_id"), "Chưa chọn")
            site_post_count[name] = site_post_count.get(name, 0) + 1

        df_site = pd.DataFrame({
            "Site": list(site_post_count.keys()),
            "Số bài": list(site_post_count.values()),
        }).set_index("Site")
        st.bar_chart(df_site, use_container_width=True)
    else:
        st.caption("Chưa có dữ liệu.")



