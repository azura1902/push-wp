
# Push-WP — Hệ thống đăng bài WordPress tự động

Hệ thống tự động tạo nội dung bằng AI và đăng lên WordPress, kèm giao diện quản lý web.

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| **Quản lý Keyword** | Nhập key → AI sinh bài viết hoàn chỉnh |
| **Lấy ảnh từ Facebook** | Nhập link post/album Facebook → tải ảnh về |
| **Đăng WordPress** | Đẩy bài + ảnh lên WP qua REST API |
| **Lên lịch đăng** | Đặt giờ đăng tự động theo queue |
| **Dashboard** | Giao diện web quản lý toàn bộ luồng |

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit Dashboard                 │
│  (Quản lý keyword, sites, posts, lịch đăng)         │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI Backend                     │
│  /api/keywords  /api/posts  /api/sites  /api/jobs   │
└──────┬──────────────┬────────────────┬──────────────┘
       │              │                │
┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
│  AI Service  │ │Image Svc   │ │  WP Service  │
│  (OpenAI)    │ │(FB Scraper)│ │ (REST API)   │
└─────────────┘ └────────────┘ └─────────────┘
       │              │                │
┌──────▼──────────────▼────────────────▼──────────────┐
│               SQLite Database                        │
│   keywords | posts | sites | jobs | images           │
└─────────────────────────────────────────────────────┘
```

---

## Cấu trúc thư mục

```
push-wp/
├── .env.example             ← Mẫu biến môi trường
├── .env                     ← Biến môi trường thực (tự tạo)
├── requirements.txt         ← Python dependencies
├── docker-compose.yml       ← Chạy bằng Docker (tùy chọn)
├── app/
│   ├── main.py              ← FastAPI entry point
│   ├── config.py            ← Cấu hình ứng dụng
│   ├── database.py          ← SQLAlchemy setup
│   ├── models/
│   │   ├── post.py          ← Model: Post
│   │   ├── keyword.py       ← Model: Keyword
│   │   ├── site.py          ← Model: WP Site
│   │   └── job.py           ← Model: Publish Job
│   ├── services/
│   │   ├── ai_service.py    ← Sinh nội dung bằng OpenAI
│   │   ├── image_service.py ← Lấy ảnh từ Facebook
│   │   └── wp_service.py    ← Đăng bài lên WordPress
│   ├── api/
│   │   ├── keywords.py      ← CRUD keyword
│   │   ├── posts.py         ← CRUD post + generate
│   │   ├── sites.py         ← CRUD WP site config
│   │   └── jobs.py          ← Quản lý publish jobs
│   └── scheduler/
│       └── tasks.py         ← APScheduler tasks
└── ui/
    ├── dashboard.py         ← Streamlit app entry
    └── pages/
        ├── 1_Keywords.py
        ├── 2_Posts.py
        ├── 3_Sites.py
        └── 4_Schedule.py
```

---

## Luồng hoạt động

```
1. Cấu hình WordPress Site
   └── URL + username + application password

2. Nhập Keyword
   └── Ví dụ: "chứng khoán cơ sở", "phân tích kỹ thuật"

3. (Tùy chọn) Nhập link ảnh Facebook
   └── Hệ thống tải ảnh về local

4. Tạo bài viết
   └── AI (GPT-4) sinh tiêu đề + nội dung dựa theo keyword
   └── Preview bài viết trên dashboard

5. Đặt lịch hoặc đăng ngay
   └── Đăng lên WP → status: published/scheduled

6. Theo dõi kết quả
   └── Link bài đăng, status, log lỗi
```

---

## Cài đặt nhanh

```bash
# 1. Clone/copy thư mục
cd D:\tttn\push-wp

# 2. Tạo virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Tạo file .env từ mẫu
copy .env.example .env
# Sửa .env: điền OPENAI_API_KEY

# 5. Khởi động backend
uvicorn app.main:app --reload --port 8000

# 6. Khởi động dashboard (terminal khác)
streamlit run ui/dashboard.py
```

---

## Cấu hình WordPress

Tạo **Application Password** trên WordPress:
1. Vào `WP Admin → Users → Profile`
2. Cuộn xuống mục **Application Passwords**
3. Nhập tên app → Generate → Copy password
4. Điền vào Dashboard trong phần **Cấu hình Sites**

---

## Biến môi trường (.env)

| Biến | Ý nghĩa |
|---|---|
| `OPENAI_API_KEY` | API key của OpenAI |
| `OPENAI_MODEL` | Model dùng (mặc định: `gpt-4o-mini`) |
| `DATABASE_URL` | SQLite path (mặc định: `./data.db`) |
| `SECRET_KEY` | JWT secret (nếu thêm auth sau) |
