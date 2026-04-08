# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Tìm .env từ gốc project (2 cấp trên file này: ui/pages/ → ui/ → root)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)
API = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(layout="wide", page_title="Manager – Push-WP")
st.title("📋 Trung tâm Quản lý Bài viết")

# ──────────────────────────────────────────────────────────────────
# Helpers – cache API calls (TTL 30s, clear sau mỗi action)
# ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def fetch_posts():
    return requests.get(f"{API}/api/posts/", timeout=10).json()

@st.cache_data(ttl=60, show_spinner=False)
def fetch_sites():
    return requests.get(f"{API}/api/sites/", timeout=10).json()

def invalidate():
    fetch_posts.clear()
    fetch_sites.clear()

def api_post(path, payload):
    return requests.post(f"{API}/api{path}", json=payload, timeout=120)

def api_put(path, payload):
    return requests.put(f"{API}/api{path}", json=payload, timeout=30)

def api_delete(path):
    return requests.delete(f"{API}/api{path}", timeout=10)

STATUS_LABEL = {
    "draft":      "🟡 Nháp",
    "ready":      "🔵 Sẵn sàng",
    "publishing": "🔄 Đang đăng",
    "published":  "🟢 Đã đăng",
    "failed":     "🔴 Lỗi",
}
LANG_OPTIONS = ["vi", "en"]

# ──────────────────────────────────────────────────────────────────
# Load dữ liệu (cached)
# ──────────────────────────────────────────────────────────────────
try:
    posts_raw = fetch_posts()
    sites_raw = fetch_sites()
except Exception:
    st.error("❌ Không kết nối được backend. Hãy chạy: `uvicorn app.main:app --reload`")
    st.stop()

site_id_to_name = {s["id"]: s["name"] for s in sites_raw}
site_name_to_id = {s["name"]: s["id"] for s in sites_raw}
site_names = ["—"] + [s["name"] for s in sites_raw]

# ──────────────────────────────────────────────────────────────────
# Thống kê nhanh
# ──────────────────────────────────────────────────────────────────
total  = len(posts_raw)
drafts = sum(1 for p in posts_raw if p["status"] == "draft")
ready  = sum(1 for p in posts_raw if p["status"] == "ready")
done   = sum(1 for p in posts_raw if p["status"] == "published")

c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])
c1.metric("Tổng", total)
c2.metric("🟡 Nháp", drafts)
c3.metric("🔵 Sẵn sàng", ready)
c4.metric("🟢 Đã đăng", done)
if c5.button("🔄 Làm mới"):
    invalidate()
    st.rerun()

st.divider()

# ──────────────────────────────────────────────────────────────────
# Form thêm dòng mới
# ──────────────────────────────────────────────────────────────────
if "form_counter" not in st.session_state:
    st.session_state["form_counter"] = 0

with st.expander("➕ Thêm dòng mới", expanded=(total == 0)):
    with st.form(f"add_draft_{st.session_state['form_counter']}", clear_on_submit=True):
        fc1, fc2, fc3 = st.columns([3, 1, 2])
        kw_text  = fc1.text_input(
            "Keyword / Tên bài hát *",
            placeholder="Albert Hammond – It Never Rains in Southern California",
        )
        lang     = fc2.selectbox("Ngôn ngữ", LANG_OPTIONS, index=0)
        site_sel = fc3.selectbox("Site", site_names, index=0)

        description = st.text_area(
            "Hướng dẫn thêm cho AI (tùy chọn)",
            placeholder="Ví dụ: Write about the story behind this 1972 classic, its lyrics meaning...",
            height=70,
        )
        fb_urls_input = st.text_area(
            "Link ảnh CDN Facebook (mỗi dòng 1 link, tùy chọn)",
            placeholder="https://scontent.fhan20-1.fna.fbcdn.net/v/...",
            height=70,
        )
        youtube_url_input = st.text_input(
            "🎬 Link YouTube (tùy chọn – sẽ chèn vào cuối bài viết)",
            placeholder="https://www.youtube.com/watch?v=...",
        )
        submit = st.form_submit_button("➕ Thêm vào danh sách", use_container_width=True, type="primary")

    if submit:
        if not kw_text.strip():
            st.warning("Vui lòng nhập keyword.")
        else:
            fb_urls = [u.strip() for u in fb_urls_input.splitlines() if u.strip()]
            yt = youtube_url_input.strip() or None
            r = api_post("/posts/draft", {
                "keyword_text": kw_text.strip(),
                "description": description.strip() or None,
                "language": lang,
                "site_id": site_name_to_id.get(site_sel),
                "fb_image_urls": fb_urls or None,
                "youtube_url": yt,
            })
            if r.status_code == 201:
                st.success(f"✅ Đã thêm: {kw_text.strip()}")
                st.session_state["form_counter"] += 1
                invalidate()
                st.rerun()
            else:
                st.error(f"Lỗi: {r.text}")

st.divider()

# ──────────────────────────────────────────────────────────────────
# Bảng chính
# ──────────────────────────────────────────────────────────────────
if not posts_raw:
    st.info("Chưa có bài viết nào. Hãy thêm dòng mới bên trên.")
    st.stop()

st.markdown("### 📋 Danh sách bài viết")
st.caption(f"Tổng {total} bài – Tick ☑ vào bài muốn thao tác")


def build_df(posts):
    rows = []
    for p in posts:
        n_imgs = 0
        for key in ("images_local_json", "fb_image_urls"):
            if p.get(key):
                try:
                    n_imgs = len(json.loads(p[key]))
                    break
                except Exception:
                    pass

        sched = None
        if p.get("schedule_publish_at"):
            try:
                sched = pd.Timestamp(p["schedule_publish_at"])
            except Exception:
                pass

        rows.append({
            "✓": False,
            "ID": p["id"],
            "Keyword": p.get("keyword_text") or "—",
            "Hướng dẫn AI": p.get("description") or "",
            "Lang": (p.get("language") or "vi").lower(),
            "Site": site_id_to_name.get(p.get("site_id"), "—"),
            "🖼": n_imgs,
            "🎬 YT": "✔" if p.get("youtube_url") else "",
            "Tiêu đề": p.get("title") or "",
            "Trạng thái": STATUS_LABEL.get(p["status"], p["status"]),
            "⏰ Lịch đăng": sched,
            "🔗 WP": p.get("wp_post_url") or "",
        })
    return pd.DataFrame(rows)


df = build_df(posts_raw)
post_ids = [p["id"] for p in posts_raw]

edited = st.data_editor(
    df,
    use_container_width=True,
    height=min(80 + len(df) * 38, 600),
    hide_index=True,
    column_config={
        "✓":            st.column_config.CheckboxColumn("✓", width=40),
        "ID":           st.column_config.NumberColumn("ID", disabled=True, width=55),
        "Keyword":      st.column_config.TextColumn("Keyword", width=200),
        "Hướng dẫn AI": st.column_config.TextColumn("Hướng dẫn AI", width=200),
        "Lang":         st.column_config.SelectboxColumn("Lang", options=LANG_OPTIONS, width=70),
        "Site":         st.column_config.SelectboxColumn("Site", options=site_names, width=130),
        "🖼":           st.column_config.NumberColumn("🖼", disabled=True, width=45),
        "🎬 YT":        st.column_config.TextColumn("🎬 YT", disabled=True, width=55),
        "Tiêu đề":     st.column_config.TextColumn("Tiêu đề", disabled=True, width=200),
        "Trạng thái":  st.column_config.TextColumn("Trạng thái", disabled=True, width=120),
        "⏰ Lịch đăng": st.column_config.DatetimeColumn("⏰ Lịch đăng", format="DD/MM/YYYY HH:mm", width=145),
        "🔗 WP":        st.column_config.LinkColumn("🔗 WP", width=280),
    },
    key="main_table",
)

selected_mask = edited["✓"].tolist()
selected_ids  = [post_ids[i] for i, sel in enumerate(selected_mask) if sel]
selected_posts_map = {p["id"]: p for p in posts_raw}

# ──────────────────────────────────────────────────────────────────
# Action bar
# ──────────────────────────────────────────────────────────────────

a1, a2, a3, a4, a5 = st.columns([2, 2, 3, 2, 2])
btn_save     = a1.button("💾 Lưu thay đổi",  use_container_width=True)
btn_publish  = a2.button("🚀 Đăng ngay",     disabled=not selected_ids, use_container_width=True)
schedule_dt   = a3.date_input("📅 Ngày", value=None, key="sched_date")
schedule_time = a3.time_input("⏰ Giờ",  value=None, key="sched_time", step=60)
btn_schedule  = a4.button("📅 Đặt lịch",     disabled=not selected_ids, use_container_width=True)
btn_delete    = a5.button("🗑️ Xóa đã chọn",  disabled=not selected_ids, use_container_width=True)

# ──────────────────────────────────────────────────────────────────
# Xử lý actions
# ──────────────────────────────────────────────────────────────────
if btn_save:
    for idx, row in edited.iterrows():
        post_id   = post_ids[idx]
        new_kw    = row["Keyword"] if row["Keyword"] != "—" else None
        new_desc  = row["Hướng dẫn AI"] or None
        new_lang  = row["Lang"]
        new_site  = site_name_to_id.get(row["Site"])
        new_sched = row["⏰ Lịch đăng"]
        new_sched_str = new_sched.isoformat() if pd.notna(new_sched) and new_sched else None
        api_put(f"/posts/{post_id}", {
            "keyword_text": new_kw,
            "description": new_desc,
            "language": new_lang,
            "site_id": new_site,
            "schedule_publish_at": new_sched_str,
        })
    st.success(f"✅ Đã lưu {len(edited)} bài")
    invalidate()
    st.rerun()

if btn_publish:
    progress = st.progress(0, text="Đang sinh bài...")
    errors = []
    for i, post_id in enumerate(selected_ids):
        post = selected_posts_map.get(post_id, {})
        site_id = post.get("site_id")
        if not site_id:
            errors.append(f"#{post_id}: chưa chọn Site")
            progress.progress((i + 1) / len(selected_ids))
            continue
        if post.get("status") == "publishing":
            errors.append(f"#{post_id}: đang đăng, bỏ qua")
            progress.progress((i + 1) / len(selected_ids))
            continue
        # Sinh bài trước
        progress.progress((i + 1) / len(selected_ids), text=f"Sinh bài {i+1}/{len(selected_ids)}...")
        rg = api_post(f"/posts/{post_id}/generate", {})
        if rg.status_code not in (200, 201):
            errors.append(f"#{post_id} sinh bài lỗi: {rg.text[:80]}")
            continue
        # Đăng ngay
        r = api_post("/posts/publish", {"post_id": post_id, "site_id": site_id})
        if r.status_code not in (200, 202):
            errors.append(f"#{post_id} đăng lỗi: {r.text[:80]}")
    progress.empty()
    if errors:
        st.warning(" | ".join(errors))
    else:
        st.success(f"✅ Đã sinh và gửi lệnh đăng {len(selected_ids)} bài!")
    invalidate()
    st.rerun()

if btn_schedule:
    if not schedule_dt:
        st.warning("Chưa chọn ngày lịch đăng.")
    else:
        sched_dt  = datetime.combine(schedule_dt, schedule_time if schedule_time else datetime.min.time())
        sched_str = sched_dt.isoformat()
        progress = st.progress(0, text="Đang sinh bài...")
        errors = []
        for i, post_id in enumerate(selected_ids):
            progress.progress((i + 1) / len(selected_ids), text=f"Sinh bài {i+1}/{len(selected_ids)}...")
            rg = api_post(f"/posts/{post_id}/generate", {})
            if rg.status_code not in (200, 201):
                errors.append(f"#{post_id} sinh bài lỗi: {rg.text[:80]}")
                continue
            api_put(f"/posts/{post_id}", {"schedule_publish_at": sched_str})
        progress.empty()
        if errors:
            st.warning(" | ".join(errors))
        else:
            st.success(f"✅ Đã sinh và đặt lịch {len(selected_ids)} bài → {sched_dt.strftime('%d/%m/%Y %H:%M')}")
        invalidate()
        st.rerun()

if btn_delete:
    for post_id in selected_ids:
        api_delete(f"/posts/{post_id}")
    st.success(f"✅ Đã xóa {len(selected_ids)} bài")
    invalidate()
    st.rerun()

st.divider()

# ──────────────────────────────────────────────────────────────────
# Chi tiết bài được chọn (chỉ khi chọn đúng 1 bài)
# ──────────────────────────────────────────────────────────────────
if len(selected_ids) == 1:
    detail_id = selected_ids[0]
    detail = next((p for p in posts_raw if p["id"] == detail_id), None)
    if not detail:
        detail = requests.get(f"{API}/api/posts/{detail_id}", timeout=10).json()

    st.subheader(f"📄 {detail.get('title') or detail.get('keyword_text') or f'Bài #{detail_id}'}")

    tab_prev, tab_html, tab_images, tab_edit = st.tabs(
        ["👁️ Preview", "🔧 HTML", "🖼️ Ảnh", "✏️ Cập nhật ảnh & YouTube"]
    )

    with tab_prev:
        if detail.get("content"):
            st.markdown(detail["content"], unsafe_allow_html=True)
            if detail.get("youtube_url"):
                st.markdown("---")
                st.video(detail["youtube_url"])
        else:
            st.info("Chưa sinh nội dung. Tick bài này → bấm **🤖 Sinh bài**.")

    with tab_html:
        if detail.get("content"):
            st.code(detail["content"], language="html")
        else:
            st.info("Chưa có nội dung.")

    with tab_images:
        images = []
        if detail.get("images_local_json"):
            try:
                images = json.loads(detail["images_local_json"])
            except Exception:
                pass
        if images:
            cols = st.columns(min(len(images), 4))
            for i, img_path in enumerate(images):
                try:
                    cols[i % 4].image(img_path, use_container_width=True)
                except Exception:
                    cols[i % 4].caption(f"❌ {img_path}")
        else:
            st.info("Chưa có ảnh local.")

    with tab_edit:
        with st.form("update_media"):
            existing_urls = ""
            if detail.get("fb_image_urls"):
                try:
                    existing_urls = "\n".join(json.loads(detail["fb_image_urls"]))
                except Exception:
                    pass
            new_fb  = st.text_area(
                "Link ảnh CDN (mỗi dòng 1 link)",
                value=existing_urls,
                height=100,
            )
            dl      = st.checkbox("Tải ảnh về ngay sau khi lưu", value=True)
            new_yt  = st.text_input(
                "🎬 Link YouTube (để trống nếu không thay đổi)",
                value=detail.get("youtube_url") or "",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            save_media = st.form_submit_button("💾 Lưu ảnh & YouTube", use_container_width=True)

        if save_media:
            fb_list  = [u.strip() for u in new_fb.splitlines() if u.strip()]
            yt_clean = new_yt.strip() or None
            payload  = {"fb_image_urls": fb_list, "download_images": dl, "youtube_url": yt_clean}
            r = api_put(f"/posts/{detail_id}", payload)
            if r.status_code == 200:
                st.success("✅ Đã cập nhật!")
                invalidate()
                st.rerun()
            else:
                st.error(f"Lỗi: {r.text}")

elif len(selected_ids) > 1:
    st.info(f"Đang chọn {len(selected_ids)} bài — chọn 1 bài để xem chi tiết/preview.")
