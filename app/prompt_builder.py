from typing import Any, Dict, List
from app.database import get_live_portfolio_data
from app.security import SAFE_SECURITY_INSTRUCTION
from app.style_analyzer import style_analyzer


def build_system_prompt(user_style_key: str = "trung_tinh") -> str:
    """Builds the comprehensive system prompt derived 100% dynamically from live database tables."""
    data = get_live_portfolio_data()
    profile = data.get("profile", {})
    experiences = data.get("experiences", [])
    work_items = data.get("work_items", [])
    skills = data.get("skills", [])
    projects = data.get("projects", [])
    articles = data.get("knowledge_articles", [])

    style_instruction = style_analyzer.get_style_directive(user_style_key)

    # 1. Base Role
    prompt_parts = [
        "Bạn là \"NQK AI Assistant\" - Trợ lý trí tuệ nhân tạo đại diện cho Kỹ sư phần mềm Nguyễn Quốc Khoa (Full-stack & AI Systems Engineer).",
        "\n" + SAFE_SECURITY_INSTRUCTION,
        f"\n[HƯỚNG DẪN THÍCH ỨNG PHONG CÁCH NGƯỜI DÙNG]:\n{style_instruction}",
        "\n[KNOWLEDGE_CONTEXT - TOÀN BỘ DỮ LIỆU ĐƯỢC TRUY VẤN TRỰC TIẾP TỪ CƠ SỞ DỮ LIỆU CỦA NGUYỄN QUỐC KHOA]:"
    ]

    # 2. Profile (Table: profiles)
    prompt_parts.append("\n### 1. THÔNG TIN CÁ NHÂN & LIÊN HỆ (Bảng profiles):")
    prompt_parts.append(f"- Họ và tên: {profile.get('full_name', 'Nguyễn Quốc Khoa')}")
    prompt_parts.append(f"- Chức danh chuyên môn: {profile.get('headline', 'Full-stack Developer')}")
    prompt_parts.append(f"- Email: {profile.get('email') or 'nguyenquockhoa5549@gmail.com'}")
    prompt_parts.append(f"- Số điện thoại / Zalo: {profile.get('phone') or '0969 895 549'}")
    prompt_parts.append(f"- Địa điểm: {profile.get('location', 'Việt Nam')}")
    prompt_parts.append(f"- GitHub: {profile.get('github_url') or 'https://github.com/quockhoa53'}")
    prompt_parts.append(f"- LinkedIn: {profile.get('linkedin_url') or 'https://www.linkedin.com/in/quockhoa'}")
    if profile.get("short_bio"):
        prompt_parts.append(f"- Tóm tắt chuyên môn: {profile.get('short_bio')}")
    if profile.get("bio_plain"):
        prompt_parts.append(f"- Giới thiệu chi tiết (Bio):\n{profile.get('bio_plain')}")

    # 3. Experiences at Companies (Table: experiences)
    if experiences:
        prompt_parts.append("\n### 2. KINH NGHIỆM LÀM VIỆC TẠI CÁC CÔNG TY (Bảng experiences):")
        for idx, exp in enumerate(experiences, 1):
            start = exp.get("start_date", "")
            end = exp.get("end_date", "Hiện tại")
            time_range = f"{start} — {end}" if start else end
            prompt_parts.append(f"* **Công ty {idx}: {exp.get('company')}**")
            prompt_parts.append(f"  - Vị trí: {exp.get('position')}")
            prompt_parts.append(f"  - Thời gian làm việc: {time_range}")
            if exp.get("description_plain"):
                prompt_parts.append(f"  - Trách nhiệm & Dự án đã làm: {exp.get('description_plain')}")

    # 4. Work process / Specific Engineering Items (Table: work_items)
    if work_items:
        prompt_parts.append("\n### 3. QUÁ TRÌNH LÀM VIỆC & DỰ ÁN KỸ THUẬT (Bảng work_items):")
        for idx, w in enumerate(work_items, 1):
            prompt_parts.append(f"* **{w.get('title')} ({w.get('period')})** - {w.get('role')} tại {w.get('company')}")
            if w.get("technologies"):
                prompt_parts.append(f"  - Công nghệ sử dụng: {w.get('technologies')}")
            if w.get("summary_plain"):
                prompt_parts.append(f"  - Tóm tắt: {w.get('summary_plain')}")
            if w.get("content_plain"):
                prompt_parts.append(f"  - Chi tiết công việc: {w.get('content_plain')}")
            if w.get("detail_url"):
                prompt_parts.append(f"  - Link chi tiết trên web: [{w.get('title')}]({w.get('detail_url')})")

    # 5. Technical Skills (Table: skills)
    if skills:
        prompt_parts.append("\n### 4. KỸ NĂNG VÀ CÔNG NGHỆ CHUYÊN SÂU (Bảng skills):")
        cats: Dict[str, List[str]] = {}
        for s in skills:
            cat = s.get("category", "Kỹ năng khác")
            name = s.get("name")
            if name:
                cats.setdefault(cat, []).append(name)
        for cat, items in cats.items():
            prompt_parts.append(f"- **{cat}**: {', '.join(items)}")

    # 6. Projects (Table: projects)
    if projects:
        prompt_parts.append("\n### 5. CÁC DỰ ÁN THỰC TẾ TIÊU BIỂU (Bảng projects):")
        for idx, p in enumerate(projects, 1):
            feat = " [⭐ NỔI BẬT]" if p.get("featured") else ""
            prompt_parts.append(f"\n==========================================")
            prompt_parts.append(f"DỰ ÁN {idx}: {p.get('title')}{feat}")
            prompt_parts.append(f"- Công nghệ: {p.get('technologies', 'N/A')}")
            if p.get("summary"):
                prompt_parts.append(f"- Tóm tắt: {p.get('summary')}")
            if p.get("description_plain"):
                prompt_parts.append(f"- Toàn bộ tài liệu mô tả chi tiết & kiến trúc nghiệp vụ thực tế:\n{p.get('description_plain')}")
            if p.get("detail_url"):
                prompt_parts.append(f"- Link xem chi tiết trên Portfolio: [{p.get('title')}]({p.get('detail_url')})")
            if p.get("demo_url"):
                prompt_parts.append(f"- Live Demo: {p.get('demo_url')}")
            if p.get("source_url"):
                prompt_parts.append(f"- Mã nguồn GitHub: {p.get('source_url')}")
            prompt_parts.append(f"==========================================\n")

    # 7. Knowledge Articles (Table: knowledge_articles)
    if articles:
        prompt_parts.append("\n### 6. BÀI VIẾT CHIA SẺ KIẾN THỨC (Bảng knowledge_articles):")
        for a in articles:
            detail_link = f"[{a.get('title')}]({a.get('detail_url')})" if a.get("detail_url") else a.get('title')
            prompt_parts.append(f"- **{detail_link}** ({a.get('category')}): {a.get('summary')}")

    # 8. Core Business Rules
    prompt_parts.append("\n[QUY TẮC PHẢN HỒI BẮT BUỘC]:")
    prompt_parts.append("1. NGUYÊN TẮC TRUNG THỰC VỚI CƠ SỞ DỮ LIỆU:")
    prompt_parts.append("   - Luôn trả lời dựa 100% trên dữ liệu thực tế từ các bảng ở trên.")
    prompt_parts.append("   - Khi người dùng hỏi về kinh nghiệm làm việc tại công ty: Lấy chính xác từ mục [2. KINH NGHIỆM LÀM VIỆC TẠI CÁC CÔNG TY (Bảng experiences)] (ví dụ: Thế Giới Di Động - MWG, SysOne, thời gian bắt đầu - kết thúc, các service đã phụ trách).")
    prompt_parts.append("   - Khi người dùng hỏi về thông tin mà trong toàn bộ cơ sở dữ liệu trên không có (ví dụ: giải thưởng, chứng chỉ chưa cập nhật): Bắt buộc trả lời lịch sự rằng thông tin này chưa được cập nhật trong cơ sở dữ liệu của hệ thống, không được tự suy diễn hoặc bịa đặt.")
    prompt_parts.append("2. DỰ ÁN & ĐIỀU HƯỚNG LIÊN KẾT:")
    prompt_parts.append("   - Khi nhắc đến dự án: Luôn kèm link [👉 Xem chi tiết dự án](/projects/1) và link GitHub.")
    prompt_parts.append("   - Khi người dùng hỏi về toàn bộ danh mục dự án: Gửi link [📂 Xem tất cả dự án](/projects).")
    prompt_parts.append("   - Khi người dùng hỏi về liên hệ: Cung cấp đầy đủ SĐT/Zalo 0969 895 549, Email nguyenquockhoa5549@gmail.com, GitHub, LinkedIn và link [📩 Gửi tin nhắn trực tiếp qua trang Liên hệ](/contact).")
    prompt_parts.append("3. CHỈ KHI NGƯỜI DÙNG CHỦ ĐỘNG HỎI VỀ 'người yêu của Khoa', 'bạn gái', 'chị Diệu', 'chuyện tình cảm': Mới chia sẻ ấm áp rằng người yêu anh Khoa là chị Diệu – chuyên viên Marketing tài năng. Bình thường luôn giữ phong thái kỹ sư chuyên nghiệp.")

    return "\n".join(prompt_parts)
