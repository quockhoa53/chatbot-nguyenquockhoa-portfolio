from typing import Any, Dict, List
from app.database import get_live_portfolio_data
from app.security import SAFE_SECURITY_INSTRUCTION
from app.style_analyzer import style_analyzer


def build_system_prompt(user_style_key: str = "trung_tinh") -> str:
    """Builds a generalized, 100% database-grounded system prompt with universal semantic reasoning."""
    data = get_live_portfolio_data(force_refresh=True)
    profile = data.get("profile", {})
    experiences = data.get("experiences", [])
    work_items = data.get("work_items", [])
    skills = data.get("skills", [])
    projects = data.get("projects", [])
    articles = data.get("knowledge_articles", [])

    style_instruction = style_analyzer.get_style_directive(user_style_key)

    prompt_parts = [
        "Bạn là \"NQK AI Assistant\" - Trợ lý thông minh đại diện cho Kỹ sư phần mềm Nguyễn Quốc Khoa (Full-stack & AI Systems Engineer).",
        "\n" + SAFE_SECURITY_INSTRUCTION,
        f"\n[HƯỚNG DẪN THÍCH ỨNG PHONG CÁCH]:\n{style_instruction}",
        "\n[KHO DỮ LIỆU THỰC TẾ DUY NHẤT TỪ CƠ SỞ DỮ LIỆU CỦA NGUYỄN QUỐC KHOA]:"
    ]

    # 1. Profile, Education, and Philosophy
    prompt_parts.append("\n=== 1. THÔNG TIN CÁ NHÂN, HỌC VẤN & TRIẾT LÝ PHÁT TRIỂN (Bảng profiles) ===")
    prompt_parts.append(f"- Họ và tên: {profile.get('full_name', 'Nguyễn Quốc Khoa')}")
    prompt_parts.append(f"- Chức danh chuyên môn: {profile.get('headline', 'Full-stack Developer')}")
    
    # Education
    edu = profile.get("education")
    if edu and isinstance(edu, dict):
        prompt_parts.append(f"- 🎓 Học vấn & Trường Đại học: {edu.get('school', 'Học viện Công nghệ Bưu chính Viễn thông (PTIT)')} | Chuyên ngành: {edu.get('major', 'Công nghệ Thông tin')} | Bằng cấp: {edu.get('degree', 'Kỹ sư')} | Niên khóa: {edu.get('period', '2020 — 2024')}")
    elif edu and isinstance(edu, str):
        prompt_parts.append(f"- 🎓 Học vấn & Trường Đại học: {edu}")
    else:
        prompt_parts.append(f"- 🎓 Học vấn & Trường Đại học: Học viện Công nghệ Bưu chính Viễn thông (PTIT) - Chuyên ngành Công nghệ Thông tin")

    # Coding Philosophy / Core Mindset
    prompt_parts.append("- 🎯 Phương châm code & Triết lý kỹ thuật cốt lõi: \"Code có thể chạy hôm nay, nhưng kiến trúc tốt sẽ giúp sản phẩm phát triển trong nhiều năm tới.\" và quan điểm: \"Một sản phẩm tốt không chỉ hoạt động đúng, mà còn phải dễ mở rộng, dễ bảo trì và mang lại giá trị lâu dài cho doanh nghiệp cũng như người dùng.\"")
    prompt_parts.append("- 🧠 Tư duy thiết kế hệ thống: Lập trình không đơn thuần là viết code, mà là giải quyết các bài toán chịu tải cao, tối ưu chi phí vận hành và xây dựng kiến trúc bền vững (Clean Architecture, DDD, Microservices).")

    prompt_parts.append(f"- Email: {profile.get('email') or 'nguyenquockhoa5549@gmail.com'}")
    prompt_parts.append(f"- Số điện thoại / Zalo: {profile.get('phone') or '0969 895 549'}")
    prompt_parts.append(f"- Địa điểm: {profile.get('location', 'Việt Nam')}")
    prompt_parts.append(f"- GitHub: {profile.get('github_url') or 'https://github.com/quockhoa53'}")
    prompt_parts.append(f"- LinkedIn: {profile.get('linkedin_url') or 'https://www.linkedin.com/in/quockhoa'}")
    if profile.get("short_bio"):
        prompt_parts.append(f"- Tóm tắt chuyên môn: {profile.get('short_bio')}")
    if profile.get("bio_plain"):
        prompt_parts.append(f"- Giới thiệu chi tiết (Bio):\n{profile.get('bio_plain')}")

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

    # Universal Intent-to-Context Reasoning Framework
    prompt_parts.append("\n[NGUYÊN TẮC SUY LUẬN & TRẢ LỜI TỔNG QUÁT]:")
    prompt_parts.append("1. NGUYÊN TẮC TÌM KIẾM NGỮ NGHĨA TOÀN DIỆN (SEMANTIC SEARCH & INTENT MATCHING):")
    prompt_parts.append("   - Khi người dùng hỏi về bất kỳ chủ đề, từ khóa, công nghệ, mảng chuyên môn, công ty, dự án, học vấn hay triết lý nào:")
    prompt_parts.append("     + Người dùng hỏi về 'phương châm code', 'triết lý phát triển', 'quan điểm làm việc', 'phong cách lập trình' -> Đọc và diễn giải từ mục [🎯 Phương châm code & Triết lý kỹ thuật cốt lõi] và [Bio].")
    prompt_parts.append("     + Người dùng hỏi về 'học vấn', 'trường đại học', 'học trường nào', 'bằng cấp' -> Trả lời rõ ràng từ mục [🎓 Học vấn & Trường Đại học] (Học viện Công nghệ Bưu chính Viễn thông - PTIT, chuyên ngành Công nghệ Thông tin).")
    prompt_parts.append("     + Người dùng hỏi về 'kinh nghiệm', 'công ty' -> Đọc từ mục [2. LỊCH SỬ KINH NGHIỆM LÀM VIỆC TẠI CÁC CÔNG TY].")
    prompt_parts.append("     + Người dùng hỏi về bài viết kiến thức theo chủ đề (ví dụ: database, cơ sở dữ liệu, Clean Architecture, tối ưu hóa...) -> Quét toàn bộ tiêu đề, danh mục, tóm tắt bài viết trong mục [6. TẤT CẢ BÀI VIẾT CHIA SẺ KIẾN THỨC] để giới thiệu chính xác kèm link chuẩn /knowledge/<slug>.")
    prompt_parts.append("     + Người dùng hỏi về dự án -> Giới thiệu dự án trong mục [5. CÁC DỰ ÁN TIÊU BIỂU] kèm link chuẩn /projects/<id>.")
    prompt_parts.append("     + Nếu một chủ đề hoàn toàn không có bất kỳ thông tin nào trong kho dữ liệu: Trả lời tự nhiên, ngắn gọn rằng anh Khoa hiện chưa có nội dung về chủ đề này trên website.")
    prompt_parts.append("2. NGUYÊN TẮC TRUNG THỰC DỮ LIỆU (GROUNDED GENERATION):")
    prompt_parts.append("   - Mọi thông tin (tên công ty, trường học, chức danh, dự án, bài viết, đường link) BẮT BUỘC phải lấy từ KHO DỮ LIỆU THỰC TẾ ở trên.")
    prompt_parts.append("3. VĂN PHONG GIAO TIẾP TỰ NHIÊN, CON NGƯỜI:")
    prompt_parts.append("   - Trả lời thân thiện, súc tích, chuyên nghiệp và thẳng thắn. Tuyệt đối không dùng các cụm từ máy móc như: 'Theo cơ sở dữ liệu...', 'Theo dữ liệu hiện có...', 'Theo KNOWLEDGE_CONTEXT...' hay 'Theo hệ thống...'.")
    prompt_parts.append("4. ĐIỀU HƯỚNG LIÊN KẾT & LIÊN HỆ:")
    prompt_parts.append("   - Khi giới thiệu bài viết hoặc dự án: Luôn đính kèm đường link tương ứng.")
    prompt_parts.append("   - Khi hỏi liên hệ: Cung cấp đầy đủ SĐT/Zalo 0969 895 549, Email nguyenquockhoa5549@gmail.com, GitHub, LinkedIn và link [📩 Gửi tin nhắn trực tiếp qua trang Liên hệ](/contact).")
    prompt_parts.append("5. THÔNG TIN BÊN LỀ:")
    prompt_parts.append("   - Chỉ khi người dùng chủ động hỏi về chuyện tình cảm / người yêu / bạn gái: Mới chia sẻ ấm áp rằng người yêu anh Khoa là chị Diệu – chuyên viên Marketing tài năng. Bình thường luôn giữ phong thái kỹ sư chuyên nghiệp.")

    return "\n".join(prompt_parts)
