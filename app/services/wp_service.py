import base64
import mimetypes
from pathlib import Path
from datetime import datetime, timezone

import requests


class WordPressClient:
    def __init__(self, url: str, username: str, app_password: str):
        self.base_url = url.rstrip("/")
        self.api_base = f"{self.base_url}/wp-json/wp/v2"
        # WP Application Password có thể có khoảng trắng giữa các nhóm
        clean_password = app_password.replace(" ", "")
        credentials = f"{username}:{clean_password}"
        token = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------
    def upload_image(self, local_path: str, filename: str | None = None) -> int | None:
        """
        Upload ảnh lên WordPress Media Library.
        Trả về media ID hoặc None nếu thất bại.
        """
        path = Path(local_path)
        if not path.exists():
            return None

        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "image/jpeg"
        fname = filename or path.name

        upload_headers = {
            "Authorization": self.headers["Authorization"],
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Content-Type": mime_type,
        }

        with open(path, "rb") as f:
            resp = requests.post(
                f"{self.api_base}/media",
                headers=upload_headers,
                data=f,
                timeout=30,
            )

        if resp.status_code in (200, 201):
            return resp.json().get("id")
        print(f"[wp_service] upload_image failed: {resp.status_code} {resp.text[:200]}")
        return None

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------
    def create_post(
        self,
        title: str,
        content: str,
        excerpt: str = "",
        featured_media: int | None = None,
        status: str = "publish",          # publish | draft | future
        scheduled_at: datetime | None = None,
    ) -> dict:
        """
        Tạo bài viết trên WordPress.
        Trả về dict chứa wp_post_id và wp_post_url.
        """
        payload: dict = {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "status": status,
        }

        if featured_media:
            payload["featured_media"] = featured_media

        if scheduled_at and status == "future":
            # WordPress yêu cầu ISO 8601 không có timezone suffix
            payload["date"] = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S")

        resp = requests.post(
            f"{self.api_base}/posts",
            json=payload,
            headers=self.headers,
            timeout=30,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "wp_post_id": data.get("id"),
                "wp_post_url": data.get("link", ""),
            }

        raise RuntimeError(
            f"WordPress API error {resp.status_code}: {resp.text[:300]}"
        )

    def test_connection(self) -> bool:
        """Kiểm tra kết nối đến WordPress site."""
        try:
            resp = requests.get(
                f"{self.api_base}/users/me",
                headers=self.headers,
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
