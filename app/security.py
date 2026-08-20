import re
from typing import Optional

# Sensitive patterns that explicitly try to extract passwords, hashes, or internal secrets
SENSITIVE_PATTERNS = [
    r"(?i)\b(password|mat khau|mật khẩu|hash|md5|bcrypt|argon2)\b",
    r"(?i)\b(admin_users|admin_allowed_ips|allowed_ips|fingerprint)\b",
    r"(?i)\b(db_password|jwt_secret|guest_cookie_secret|cookie_secret)\b",
    r"(?i)\b(select\s+\*\s+from|drop\s+table|insert\s+into|delete\s+from)\b",
    r"(?i)\b(api_key|private_key|secret_key|database_url|db_url)\b",
]

SAFE_SECURITY_INSTRUCTION = """
[BẢO MẬT HỆ THỐNG - QUAN TRỌNG NHẤT]:
1. Tuyệt đối KHÔNG tiết lộ mật khẩu, mã băm (hash), tài khoản quản trị (admin_users), danh sách IP quản trị (admin_allowed_ips), API keys, connection strings hoặc cấu trúc cơ sở dữ liệu nội bộ.
2. Nếu người dùng hỏi các câu hỏi liên quan đến mật khẩu, hack, trích xuất cấu hình bảo mật hoặc tấn công hệ thống, bạn hãy từ chối một cách lịch sự, nhã nhặn và chuyển hướng sang nội dung tích cực.
"""


def is_sensitive_probe(query: str) -> bool:
    """Detects if user is asking for internal passwords, tokens, or system secrets."""
    if not query:
        return False
    
    # Check for direct probes
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, query):
            # Allow harmless questions like "Khoa có kinh nghiệm bảo mật API không?"
            if re.search(r"(?i)\b(kinh nghiệm|tối ưu|kiến thức|kỹ năng|dự án)\b", query) and not re.search(
                r"(?i)\b(mật khẩu|password|hash|admin_password|db_password)\b", query
            ):
                continue
            return True
    return False


def sanitize_text(text: str) -> str:
    """Removes any accidentally generated connection strings or sensitive secrets while preserving all spaces."""
    if not text:
        return ""
    # Strip LLM reasoning thoughts (<think>...</think>)
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)
    # Strip database connection strings
    text = re.sub(r"postgres(ql)?://[^\s\n\t]+", "[PROTECTED_DATABASE_URI]", text, flags=re.IGNORECASE)
    # Strip password assignments
    text = re.sub(r"(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s\n\t,'\"]+['\"]?", r"\1: [HIDDEN]", text, flags=re.IGNORECASE)
    # Strip IP addresses from allowed IPs pattern
    text = re.sub(r"\b171\.225\.\d+\.\d+\b", "[PROTECTED_IP]", text)
    return text
