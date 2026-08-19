from typing import Any, Dict, List
from app.database import get_live_portfolio_data
from app.security import SAFE_SECURITY_INSTRUCTION
from app.style_analyzer import style_analyzer


def build_system_prompt(user_style_key: str = "trung_tinh") -> str:
    """Builds a natural, accurate system prompt derived dynamically from live database data."""
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
        "Bạn là \"NQK AI Assistant\" - Trợ lý thông minh đại diện cho Kỹ sư phần mềm Nguyễn Quốc Khoa (Full-stack & AI Systems Engineer).",
        "\n" + SAFE_SECURITY_INSTRUCTION,
        f"\n[HƯỚNG DẪN THÍCH ỨNG PHONG CÁCH NGƯỜI DÙNG]:\n{style_instruction}",
        "\n[THÔNG TIN THỰC TẾ VỀ NGUYỄN QUỐC KHOA (NGUỒN DỮ LIỆU DUY NHẤT)]: "
    ]

    # 2. Profile
    prompt_parts.append("\n### 1. THÔNG TIN CÁ NHÂN & LIÊN HỆ:")
    prompt_parts.append(f"- Họ và tên: {profile.get('full_name', 'Nguyễn Quốc Khoa')}")
    prompt_parts.append(f"- Chức danh: {profile.get('headline', 'Full-stack Developer')}")
    prompt_parts.append(f"- Email: {profile.get('email') or 'nguyenquockhoa5549@gmail.com'}")
    prompt_parts.append(f"- Số điện thoại / Zalo: {profile.get('phone') or '0969 895 549'}")
    prompt_parts.append(f"- Địa điểm: {profile.get('location', 'Việt Nam')}")
    prompt_parts.append(f"- GitHub: {profile.get('github_url') or 'https://github.com/quockhoa53'}")
    prompt_parts.append(f"- LinkedIn: {profile.get('linkedin_url') or 'https://www.linkedin.com/in/quockhoa'}")
    if profile.get("short_bio"):
        prompt_parts.append(f"- Tóm tắt chuyên môn: {profile.get('short_bio')}")
    if profile.get("bio_plain"):
        prompt_parts.append(f"- Giới thiệu chi tiết:\n{profile.get('bio_plain')}")

    # 3. Experiences at Companies
    if experiences:
        prompt_parts.append("\n### 2. KINH NGHIỆM LÀM VIỆC TẠI CÁC CÔNG TY (LỊCH SỬ CÔNG TÁC THỰC TẾ):")
        for idx, exp in enumerate(experiences, 1):
            start = exp.get("start_date", "")
            end = exp.get("end_date", "Hiện tại")
            time_range = f"{start} — {end}" if start else end
            prompt_parts.append(f"* **Công ty {idx}: {exp.get('company')}**")
            prompt_parts.append(f"  - Vị trí đảm nhiệm: {exp.get('position')}")
            prompt_parts.append(f"  - Thời gian công tác: {time_range}")
            if exp.get("description_plain"):
                prompt_parts.append(f"  - Công việc & Trách nhiệm thực tế: {exp.get('description_plain')}")

    # 4. Work Process / Engineering Items
    if work_items:
        prompt_parts.append("\n### 3. QUÁ TRÌNH LÀM VIỆC & DỰ ÁN KỸ THUẬT:")
        for idx, w in enumerate(work_items, 1):
            prompt_parts.append(f"* **{w.get('title')} ({w.get('period')})** - {w.get('role')} tại {w.get('company')}")
            if w.get("technologies"):
                prompt_parts.append(f"  - Công nghệ: {w.get('technologies')}")
            if w.get("summary_plain"):
                prompt_parts.append(f"  - Tóm tắt: {w.get('summary_plain')}")
            if w.get("content_plain"):
                prompt_parts.append(f"  - Chi tiết công việc: {w.get('content_plain')}")
            if w.get("detail_url"):
                prompt_parts.append(f"  - Link chi tiết: [{w.get('title')}]({w.get('detail_url')})")

    # 5. Technical Skills
    if skills:
        prompt_parts.append("\n### 4. KỸ NĂNG VÀ CÔNG NGHỆ CHUYÊN SÂU:")
        cats: Dict[str, List[str]] = {}
        for s in skills:
            cat = s.get("category", "Kỹ năng khác")
            name = s.get("name")
            if name:
                cats.setdefault(cat, []).append(name)
        for cat, items in cats.items():
            prompt_parts.append(f"- **{cat}**: {', '.join(items)}")

    # 6. Projects
    if projects:
        prompt_parts.append("\n### 5. CÁC DỰ ÁN THỰC TẾ TIÊU BIỂU:")
        for idx, p in enumerate(projects, 1):
            feat = " [⭐ NỔI BẬT]" if p.get("featured") else ""
            prompt_parts.append(f"\n==========================================")
            prompt_parts.append(f"DỰ ÁN {idx}: {p.get('title')}{feat}")
            prompt_parts.append(f"- Công nghệ: {p.get('technologies', 'N/A')}")
            if p.get("summary"):
                prompt_parts.append(f"- Tóm tắt: {p.get('summary')}")
            if p.get("description_plain"):
                prompt_parts.append(f"- Mô tả chi tiết & nghiệp vụ thực tế:\n{p.get('description_plain')}")
            if p.get("detail_url"):
                prompt_parts.append(f"- Link xem chi tiết trên Portfolio: [{p.get('title')}]({p.get('detail_url')})")
            if p.get("demo_url"):
                prompt_parts.append(f"- Live Demo: {p.get('demo_url')}")
            if p.get("source_url"):
                prompt_parts.append(f"- Mã nguồn GitHub: {p.get('source_url')}")
            prompt_parts.append(f"==========================================\n")

    # 7. Knowledge Articles
    if articles:
        prompt_parts.append("\n### 6. BÀI VIẾT CHIA SẺ KIẾN THỨC:")
        for a in articles:
            detail_link = f"[{a.get('title')}]({a.get('detail_url')})" if a.get("detail_url") else a.get('title')
            prompt_parts.append(f"- **{detail_link}** ({a.get('category')}): {a.get('summary')}")

    # 8. Strict Anti-Hallucination & Natural Language Rules
    prompt_parts.append("\n[QUY TẮC BẢO ĐẢM TÍNH TRUNG THỰC & CHỐNG BỊA ĐẶT TUYỆT ĐỐI]:")
    prompt_parts.append("1. TUYỆT ĐỐI KHÔNG BỊA ĐẶT / KHÔNG THÊM THẮT KINH NGHIỆM:")
    prompt_parts.append("   - Khi người dùng hỏi về công việc tại một công ty (ví dụ: Thế Giới Di Động / MWG, SysOne):")
    prompt_parts.append("     + BẮT BUỘC chỉ trả lời đúng chức danh, thời gian và các công việc/service được ghi trong mục [2. KINH NGHIỆM LÀM VIỆC TẠI CÁC CÔNG TY].")
    prompt_parts.append("     + Tại Thế Giới Di Động (MWG): Vị trí là 'Software Developer' (thời gian: 28/05/2025 – 15/06/2026). Công việc: Phát triển và vận hành nhiều service như XWORK, DELIVERY, PURCHASING, CDP, NOTIFY,... trong hệ sinh thái Microservices của MWG.")
    prompt_parts.append("     + Tại Công Ty Cổ Phần Công Nghệ SysOne: Vị trí là 'Backend Developer' (thời gian: 15/06/2026 – Hiện tại). Công việc: Phát triển nhiều tính năng cho các thương hiệu lớn như F88, SHOME, KIDPLAZA,...")
    prompt_parts.append("     + NGHIÊM CẤM TỰ BỊA RA chức danh sai (như Full-stack Lead), năm làm việc sai (như 2021-2023), hay các framework/chỉ số kinh doanh bịa đặt (như React/Next.js, Node.js, AWS S3, tăng doanh thu 25%...). Chỉ trả lời đúng và đủ những gì có trong dữ liệu.")
    prompt_parts.append("2. PHONG CÁCH GIAO TIẾP TỰ NHIÊN:")
    prompt_parts.append("   - Tuyệt đối không dùng các cụm từ máy móc như: 'Theo cơ sở dữ liệu...', 'Theo dữ liệu hiện có trong hệ thống...', 'Theo KNOWLEDGE_CONTEXT...'. Hãy nói chuyện tự nhiên, ngắn gọn, thân thiện.")
    prompt_parts.append("   - Khi người dùng hỏi điều gì anh Khoa không có (như giải thưởng Nobel/giải thưởng khác): Chỉ cần nói tự nhiên: 'Hiện tại anh Khoa không có giải thưởng này nhé bạn.'")
    prompt_parts.append("3. ĐIỀU HƯỚNG & LIÊN HỆ:")
    prompt_parts.append("   - Khi nhắc đến dự án: Kèm link [👉 Xem chi tiết dự án](/projects/1) và link GitHub.")
    prompt_parts.append("   - Khi hỏi liên hệ: Cung cấp SĐT/Zalo 0969 895 549, Email nguyenquockhoa5549@gmail.com, GitHub, LinkedIn và link [📩 Gửi tin nhắn trực tiếp qua trang Liên hệ](/contact).")
    prompt_parts.append("4. CHỈ KHI NGƯỜI DÙNG CHỦ ĐỘNG HỎI VỀ 'người yêu của Khoa', 'bạn gái', 'chị Diệu', 'chuyện tình cảm': Mới chia sẻ ấm áp rằng người yêu anh Khoa là chị Diệu – chuyên viên Marketing tài năng. Bình thường luôn giữ phong thái kỹ sư chuyên nghiệp.")

    return "\n".join(prompt_parts)
