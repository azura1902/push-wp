import json
from openai import OpenAI
from app.config import get_settings

settings = get_settings()


def _client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


SYSTEM_PROMPT_VI = """Bạn là chuyên gia viết nội dung SEO. Hãy viết bài viết blog hoàn chỉnh bằng tiếng Việt dựa theo từ khóa được cung cấp.

Yêu cầu:
- Tiêu đề hấp dẫn, chứa từ khóa chính
- Nội dung dài 800-1200 từ, cấu trúc rõ ràng (có heading H2, H3)
- Viết dưới dạng HTML (chỉ phần body, không có <html>/<body> tag)
- Tối ưu SEO tự nhiên
- Giọng văn thân thiện, dễ đọc

Trả về JSON theo định dạng:
{
  "title": "...",
  "excerpt": "...(150 ký tự tóm tắt)...",
  "content": "...(HTML content)..."
}"""

SYSTEM_PROMPT_EN = """You are an expert SEO content writer. Write a complete blog post in English based on the given keyword.

Requirements:
- Compelling title containing the main keyword
- 800-1200 words, clear structure (H2, H3 headings)
- HTML format (body content only, no <html>/<body> tags)
- Natural SEO optimization
- Friendly, readable tone

Return JSON in this format:
{
  "title": "...",
  "excerpt": "...(150 char summary)...",
  "content": "...(HTML content)..."
}"""


def generate_post(keyword: str, description: str = "", language: str = "vi") -> dict:
    """
    Sinh bài viết từ keyword.
    Trả về dict: {title, excerpt, content}
    """
    system_prompt = SYSTEM_PROMPT_VI if language == "vi" else SYSTEM_PROMPT_EN

    user_message = f"Từ khóa: {keyword}"
    if description:
        user_message += f"\nHướng dẫn thêm: {description}"

    client = _client()
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    result = json.loads(response.choices[0].message.content)
    return {
        "title": result.get("title", keyword),
        "excerpt": result.get("excerpt", ""),
        "content": result.get("content", ""),
    }
