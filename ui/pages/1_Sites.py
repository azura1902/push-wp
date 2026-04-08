import streamlit as st
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")
API = os.getenv("API_BASE_URL", "http://localhost:8000")

st.title("⚙️ Quản lý WordPress Sites")


def get_sites():
    return requests.get(f"{API}/api/sites/", timeout=10).json()


# --- Thêm site mới ---
with st.expander("➕ Thêm site mới", expanded=False):
    with st.form("add_site"):
        name = st.text_input("Tên site *")
        url = st.text_input("URL WordPress *", placeholder="https://example.com  (không kèm /wp-admin)")
        username = st.text_input("Username *")
        app_password = st.text_input("Application Password *", type="password")
        is_active = st.checkbox("Kích hoạt", value=True)
        submitted = st.form_submit_button("💾 Lưu")

    if submitted:
        if not all([name, url, username, app_password]):
            st.warning("Vui lòng điền đầy đủ thông tin bắt buộc.")
        else:
            resp = requests.post(f"{API}/api/sites/", json={
                "name": name, "url": url,
                "username": username, "app_password": app_password,
                "is_active": is_active,
            }, timeout=10)
            if resp.status_code == 201:
                st.success(f"✅ Đã thêm site: {name}")
                st.rerun()
            else:
                st.error(f"Lỗi: {resp.text}")

# --- Danh sách sites ---
st.subheader("Danh sách sites")
try:
    sites = get_sites()
except Exception:
    st.error("Không kết nối được backend.")
    st.stop()

if not sites:
    st.info("Chưa có site nào. Hãy thêm site bên trên.")
else:
    for site in sites:
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        col1.markdown(f"**{site['name']}**  \n`{site['url']}`")
        col2.text(site["username"])
        status_icon = "🟢" if site["is_active"] else "🔴"
        col3.markdown(status_icon)

        with col4:
            if st.button("🔌 Test", key=f"test_{site['id']}"):
                resp = requests.post(f"{API}/api/sites/{site['id']}/test", timeout=15)
                result = resp.json()
                if result.get("connected"):
                    st.success("Kết nối OK ✅")
                else:
                    st.error("Kết nối thất bại ❌")

            if st.button("🗑️ Xóa", key=f"del_{site['id']}"):
                requests.delete(f"{API}/api/sites/{site['id']}", timeout=10)
                st.rerun()
