import re
import uuid
import base64
import requests
from pathlib import Path
from urllib.parse import urlparse

IMAGES_DIR = Path("static/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Magic bytes để nhận diện file ảnh thật
IMAGE_SIGNATURES = [
    b"\xff\xd8\xff",          # JPEG
    b"\x89PNG\r\n\x1a\n",    # PNG
    b"GIF87a", b"GIF89a",    # GIF
    b"RIFF",                  # WEBP (RIFF....WEBP)
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.facebook.com/",
}


def _is_direct_image_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return (
        any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))
        or "scontent" in parsed.netloc   # Facebook CDN
        or "fbcdn.net" in parsed.netloc
    )


def _is_real_image(data: bytes) -> bool:
    """Kiểm tra magic bytes xem có phải ảnh thật không."""
    for sig in IMAGE_SIGNATURES:
        if data[:len(sig)] == sig:
            return True
    # WEBP: bytes 0-3 = RIFF, bytes 8-11 = WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


def _extract_og_image(url: str) -> str | None:
    """Cố lấy og:image từ trang Facebook."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        html = resp.text
        # og:image
        for pattern in [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)',
            r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'"og:image","content":"(https?://[^"]+?)"',
        ]:
            match = re.search(pattern, html)
            if match:
                img_url = match.group(1).replace("\\u0026", "&").replace("\\/", "/")
                if "scontent" in img_url or "fbcdn.net" in img_url:
                    return img_url
    except Exception:
        pass
    return None


def download_image(url: str) -> str | None:
    """
    Tải 1 ảnh về local. Chấp nhận:
      - Link CDN trực tiếp (scontent*.fbcdn.net)
      - Link trang FB photo (cố trích og:image)
    Trả về đường dẫn file local hoặc None nếu thất bại/không phải ảnh.
    """
    url = url.strip()
    if not url:
        return None

    # ── Xử lý data URI (data:image/jpeg;base64,...) ──────────────
    if url.startswith("data:image/"):
        try:
            header, b64data = url.split(",", 1)
            # Xác định extension từ mime type
            mime = header.split(";")[0].split(":")[1]   # vd: image/jpeg
            ext_map = {"image/jpeg": ".jpg", "image/png": ".png",
                       "image/webp": ".webp", "image/gif": ".gif"}
            ext = ext_map.get(mime, ".jpg")
            data = base64.b64decode(b64data)
            if not _is_real_image(data):
                print("[image_service] base64 data không phải ảnh hợp lệ")
                return None
            filename = f"{uuid.uuid4().hex}{ext}"
            local_path = IMAGES_DIR / filename
            local_path.write_bytes(data)
            return str(local_path)
        except Exception as e:
            print(f"[image_service] Giải mã base64 thất bại: {e}")
            return None
    # ─────────────────────────────────────────────────────────────

    image_url = url
    if "facebook.com" in url and not _is_direct_image_url(url):
        extracted = _extract_og_image(url)
        if extracted:
            image_url = extracted
        else:
            print(f"[image_service] Không trích được CDN URL từ: {url}")
            return None

    try:
        resp = requests.get(image_url, headers=HEADERS, timeout=20, stream=True)
        resp.raise_for_status()

        # Đọc toàn bộ nội dung
        data = resp.content

        # Validate là ảnh thật
        if not _is_real_image(data):
            print(f"[image_service] File tải về không phải ảnh (có thể bị redirect login): {image_url[:80]}")
            return None

        # Xác định extension
        content_type = resp.headers.get("Content-Type", "")
        ext = ".jpg"
        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"
        elif "gif" in content_type:
            ext = ".gif"

        filename = f"{uuid.uuid4().hex}{ext}"
        local_path = IMAGES_DIR / filename
        local_path.write_bytes(data)
        return str(local_path)

    except Exception as e:
        print(f"[image_service] download failed: {e}")
        return None


def download_images(urls: list[str]) -> list[str]:
    """
    Tải nhiều ảnh. Trả về list đường dẫn local (bỏ qua các URL thất bại).
    """
    results = []
    for url in urls:
        path = download_image(url)
        if path:
            results.append(path)
    return results

