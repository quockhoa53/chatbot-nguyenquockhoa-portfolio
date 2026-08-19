from typing import Any, Dict, List
from app.database import get_live_portfolio_data
from app.security import SAFE_SECURITY_INSTRUCTION
from app.style_analyzer import style_analyzer


def build_system_prompt(user_style_key: str = "trung_tinh") -> str:
    """Builds a 100% dynamic, database-driven system prompt with zero hardcoded values."""
    data = get_live_portfolio_data(force_refresh=True)
    profile = data.get("profile", {})
    experiences = data.get("experiences", [])
    work_items = data.get("work_items", [])
    skills = data.get("skills", [])
    projects = data.get("projects", [])
    articles = data.get("knowledge_articles", [])
    ai_facts = data.get("ai_facts", [])

    style_instruction = style_analyzer.get_style_directive(user_style_key)

    prompt_parts = [
        "Bạn là \"NQK AI Assistant\" - Trợ lý thông minh đại diện cho kỹ sư Nguyễn Quốc Khoa.",
        "\n" + SAFE_SECURITY_INSTRUCTION,
        f"\n[HƯỚNG DẪN THÍCH ỨNG PHONG CÁCH]:\n{style_instruction}",
        "\n[KHO DỮ LIỆU THỰC TẾ DUY NHẤT TỪ CƠ SỞ DỮ LIỆU]:"
    ]

    # 1. Profile & Education
    prompt_parts.append("\n=== 1. THÔNG TIN HỒ SƠ & LIÊN HỆ (Bảng profiles) ===")
    if profile.get("full_name"):
        prompt_parts.append(f"- Họ và tên: {profile.get('full_name')}")
    if profile.get("headline"):
        prompt_parts.append(f"- Chức danh / Vị trí: {profile.get('headline')}")
    
    edu = profile.get("education")
    if edu:
        if isinstance(edu, dict):
            edu_details = []
            if edu.get("school"):
                edu_details.append(f"Trường: {edu.get('school')}")
            if edu.get("major"):
                edu_details.append(f"Chuyên ngành: {edu.get('major')}")
            if edu.get("degree"):
                edu_details.append(f"Bằng cấp: {edu.get('degree')}")
            if edu.get("period"):
                edu_details.append(f"Niên khóa: {edu.get('period')}")
            prompt_parts.append(f"- 🎓 Học vấn & Đào tạo: {' | '.join(edu_details)}")
        elif isinstance(edu, str):
            prompt_parts.append(f"- 🎓 Học vấn & Đào tạo: {edu}")

    if profile.get("email"):
        prompt_parts.append(f"- Email: {profile.get('email')}")
    if profile.get("phone"):
        prompt_parts.append(f"- Số điện thoại / Zalo: {profile.get('phone')}")
    if profile.get("location"):
        prompt_parts.append(f"- Địa điểm: {profile.get('location')}")
    if profile.get("github_url"):
        prompt_parts.append(f"- GitHub: {profile.get('github_url')}")
    if profile.get("linkedin_url"):
        prompt_parts.append(f"- LinkedIn: {profile.get('linkedin_url')}")
    if profile.get("facebook_url"):
        prompt_parts.append(f"- Facebook: {profile.get('facebook_url')}")
    if profile.get("short_bio"):
        prompt_parts.append(f"- Tóm tắt chuyên môn & Phương châm cốt lõi: {profile.get('short_bio')}")
    if profile.get("bio_plain"):
        prompt_parts.append(f"- Giới thiệu chi tiết & Triết lý phát triển (Bio):\n{profile.get('bio_plain')}")

    # 2. Experiences at Companies
    if experiences:
        prompt_parts.append("\n=== 2. LỊCH SỬ KINH NGHIỆM LÀM VIỆC TẠI CÁC CÔNG TY (Bảng experiences) ===")
        for idx, exp in enumerate(experiences, 1):
            start = exp.get("start_date", "")
            end = exp.get("end_date", "Hiện tại")
            time_range = f"{start} — {end}" if start else end
            prompt_parts.append(f"* **Công ty {idx}: {exp.get('company')}**")
            prompt_parts.append(f"  - Vị trí: {exp.get('position')}")
            prompt_parts.append(f"  - Thời gian: {time_range}")
            if exp.get("description_plain"):
                prompt_parts.append(f"  - Trách nhiệm & Dự án đã làm: {exp.get('description_plain')}")

    # 3. Work Process / Specific Engineering Items
    if work_items:
        prompt_parts.append("\n=== 3. QUÁ TRÌNH LÀM VIỆC & MẢNG KỸ THUẬT CHUYÊN SÂU (Bảng work_items) ===")
        for idx, w in enumerate(work_items, 1):
            prompt_parts.append(f"* **Mục {idx}: {w.get('title')}** ({w.get('period')}) - Vai trò: {w.get('role')} tại {w.get('company')}")
            if w.get("technologies"):
                prompt_parts.append(f"  - Công nghệ: {w.get('technologies')}")
            if w.get("summary_plain"):
                prompt_parts.append(f"  - Tóm tắt: {w.get('summary_plain')}")
            if w.get("content_plain"):
                prompt_parts.append(f"  - Chi tiết công việc: {w.get('content_plain')}")
            if w.get("detail_url"):
                prompt_parts.append(f"  - Link chi tiết: [{w.get('title')}]({w.get('detail_url')})")

    # 4. Technical Skills
    if skills:
        prompt_parts.append("\n=== 4. KỸ NĂNG & NĂNG LỰC CÔNG NGHỆ (Bảng skills) ===")
        cats: Dict[str, List[str]] = {}
        for s in skills:
            cat = s.get("category", "Kỹ năng khác")
            name = s.get("name")
            if name:
                cats.setdefault(cat, []).append(name)
        for cat, items in cats.items():
            prompt_parts.append(f"- **{cat}**: {', '.join(items)}")

    # 5. Projects
    if projects:
        prompt_parts.append("\n=== 5. CÁC DỰ ÁN TIÊU BIỂU & MÃ NGUỒN (Bảng projects) ===")
        for idx, p in enumerate(projects, 1):
            feat = " [⭐ NỔI BẬT]" if p.get("featured") else ""
            prompt_parts.append(f"\n* **DỰ ÁN {idx}: {p.get('title')}{feat}**")
            prompt_parts.append(f"  - Công nghệ sử dụng: {p.get('technologies', 'N/A')}")
            if p.get("summary"):
                prompt_parts.append(f"  - Tóm tắt: {p.get('summary')}")
            if p.get("description_plain"):
                prompt_parts.append(f"  - Mô tả kỹ thuật & kiến trúc chi tiết:\n{p.get('description_plain')}")
            if p.get("detail_url"):
                prompt_parts.append(f"  - Link xem trên Portfolio: [{p.get('title')}]({p.get('detail_url')})")
            if p.get("demo_url"):
                prompt_parts.append(f"  - Demo trực tiếp: {p.get('demo_url')}")
            if p.get("source_url"):
                prompt_parts.append(f"  - Mã nguồn GitHub: {p.get('source_url')}")

    # 6. Knowledge Articles
    if articles:
        prompt_parts.append("\n=== 6. TẤT CẢ BÀI VIẾT CHIA SẺ KIẾN THỨC HIỆN CÓ TRÊN WEBSITE (Bảng knowledge_articles) ===")
        for idx, a in enumerate(articles, 1):
            prompt_parts.append(f"\n* **BÀI VIẾT {idx}: {a.get('title')}**")
            prompt_parts.append(f"  - Chủ đề / Danh mục: {a.get('category', 'Kiến thức')}")
            if a.get("summary"):
                prompt_parts.append(f"  - Tóm tắt nội dung: {a.get('summary')}")
            if a.get("content_plain"):
                prompt_parts.append(f"  - Trích đoạn nội dung chính:\n{a.get('content_plain')[:400]}...")
            if a.get("detail_url"):
                prompt_parts.append(f"  - Link bài viết chính thức: [{a.get('title')}]({a.get('detail_url')})")

    # 7. AI Extra Facts & Special Sidecar Knowledge
    if ai_facts:
        prompt_parts.append("\n=== 7. THÔNG TIN BỔ SUNG & BỘ NHỚ ĐẶC BIỆT (Bảng ai_facts) ===")
        for idx, f in enumerate(ai_facts, 1):
            prompt_parts.append(f"* **Mục {idx}: {f.get('title')}** (Phân loại: {f.get('category')})")
            prompt_parts.append(f"  {f.get('content')}")

    # Universal Reasoning Framework (Zero Hardcoding)
    prompt_parts.append("\n[NGUYÊN TẮC SUY LUẬN & TRẢ LỜI TỔNG QUÁT]:")
    prompt_parts.append("1. NGUYÊN TẮC TÌM KIẾM NGỮ NGHĨA & ÁNH XẠ Ý ĐỊNH (SEMANTIC INTENT MAPPING):")
    prompt_parts.append("   - Trả lời các câu hỏi dựa trên toàn bộ KHO DỮ LIỆU THỰC TẾ phía trên:")
    prompt_parts.append("     + Hỏi về 'phương châm code', 'triết lý phát triển', 'quan điểm làm việc', 'phong cách lập trình' -> Đọc và tổng hợp từ mục [1. THÔNG TIN HỒ SƠ & LIÊN HỆ] (trường Tóm tắt chuyên môn và Giới thiệu chi tiết Bio).")
    prompt_parts.append("     + Hỏi về 'học vấn', 'trường đại học', 'học trường nào', 'bằng cấp' -> Đọc và trả lời từ trường [🎓 Học vấn & Đào tạo].")
    prompt_parts.append("     + Hỏi về 'kinh nghiệm', 'công ty', 'thời gian làm việc' -> Đọc từ mục [2. LỊCH SỬ KINH NGHIỆM LÀM VIỆC TẠI CÁC CÔNG TY].")
    prompt_parts.append("     + Hỏi về bài viết kiến thức theo chủ đề (ví dụ: database, cơ sở dữ liệu, Clean Architecture, tối ưu hóa, Kafka, Spring Boot, AI...) -> Quét toàn bộ tiêu đề, danh mục, tóm tắt và nội dung tại mục [6. TẤT CẢ BÀI VIẾT CHIA SẺ KIẾN THỨC] để giới thiệu chính xác kèm đường link tương ứng.")
    prompt_parts.append("     + Hỏi về dự án thực tế -> Giới thiệu các dự án phù hợp trong mục [5. CÁC DỰ ÁN TIÊU BIỂU] kèm đường link tương ứng.")
    prompt_parts.append("     + Hỏi về các chủ đề đời tư, bạn bè, người yêu, sở thích, thú cưng, quan điểm cá nhân, v.v. -> Quét và trả lời từ mục [7. THÔNG TIN BỔ SUNG & BỘ NHỚ ĐẶC BIỆT] (nếu có thông tin).")
    prompt_parts.append("     + Nếu một chủ đề người dùng hỏi hoàn toàn không có bất kỳ thông tin nào trong kho dữ liệu: Trả lời tự nhiên, ngắn gọn rằng anh Khoa hiện chưa có nội dung về chủ đề này trên website.")
    prompt_parts.append("2. NGUYÊN TẮC TRUNG THỰC DỮ LIỆU (GROUNDED GENERATION):")
    prompt_parts.append("   - Mọi thông tin (tên công ty, trường học, chức danh, dự án, bài viết, đường link, thông tin liên hệ, sự kiện cá nhân) BẮT BUỘC phải lấy 100% từ KHO DỮ LIỆU THỰC TẾ ở trên.")
    prompt_parts.append("3. VĂN PHONG GIAO TIẾP TỰ NHIÊN, CON NGƯỜI:")
    prompt_parts.append("   - Trả lời thân thiện, súc tích, chuyên nghiệp và thẳng thắn. Tuyệt đối không dùng các cụm từ máy móc như: 'Theo cơ sở dữ liệu...', 'Theo dữ liệu hiện có...', 'Theo KNOWLEDGE_CONTEXT...' hay 'Theo hệ thống...'.")
    prompt_parts.append("4. ĐIỀU HƯỚNG LIÊN KẾT & LIÊN HỆ:")
    prompt_parts.append("   - Khi giới thiệu bài viết hoặc dự án: Luôn đính kèm đường link tương ứng có trong kho dữ liệu.")
    prompt_parts.append("   - Khi người dùng hỏi thông tin liên hệ: Cung cấp đầy đủ các kênh liên hệ (Email, Số điện thoại, GitHub, LinkedIn, Facebook) có trong mục [1. THÔNG TIN HỒ SƠ & LIÊN HỆ] và link [📩 Gửi tin nhắn trực tiếp qua trang Liên hệ](/contact).")

    return "\n".join(prompt_parts)
