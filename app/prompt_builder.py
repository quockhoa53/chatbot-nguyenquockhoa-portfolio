from typing import Any, Dict, List
from app.database import get_live_portfolio_data
from app.security import SAFE_SECURITY_INSTRUCTION
from app.style_analyzer import style_analyzer


def build_system_prompt(user_style_key: str = "trung_tinh") -> str:
    """Builds the comprehensive system prompt including knowledge context, security rules, and user style adaptation."""
    data = get_live_portfolio_data()
    profile = data.get("profile", {})
    projects = data.get("projects", [])
    skills = data.get("skills", [])
    articles = data.get("knowledge_articles", [])
    work_items = data.get("work_items", [])

    style_instruction = style_analyzer.get_style_directive(user_style_key)

    # 1. Base Role
    prompt_parts = [
        "Bạn là \"NQK AI Assistant\" - Trợ lý trí tuệ nhân tạo đại diện cho Kỹ sư phần mềm Nguyễn Quốc Khoa (Full-stack & AI Systems Engineer).",
        "\n" + SAFE_SECURITY_INSTRUCTION,
        f"\n[HƯỚNG DẪN THÍCH ỨNG PHONG CÁCH NGƯỜI DÙNG]:\n{style_instruction}",
        "\n[KNOWLEDGE_CONTEXT - THÔNG TIN THỰC TẾ CỦA NGUYỄN QUỐC KHOA]:"
    ]

    # 2. Profile
    prompt_parts.append("\n### 1. THÔNG TIN CÁ NHÂN & LIÊN HỆ:")
    prompt_parts.append(f"- Họ tên: {profile.get('full_name', 'Nguyễn Quốc Khoa')}")
    prompt_parts.append(f"- Chức danh: {profile.get('headline', 'Full-stack & Backend AI Engineer')}")
    prompt_parts.append(f"- Email liên hệ chính thức: {profile.get('email') or 'nguyenquockhoa5549@gmail.com'}")
    prompt_parts.append(f"- Số điện thoại / Zalo liên hệ: {profile.get('phone') or '0969 895 549'}")
    prompt_parts.append(f"- Địa điểm: {profile.get('location', 'Việt Nam')}")
    prompt_parts.append(f"- GitHub: {profile.get('github_url') or 'https://github.com/quockhoa53'}")
    prompt_parts.append(f"- LinkedIn: {profile.get('linkedin_url') or 'https://www.linkedin.com/in/quockhoa'}")
    if profile.get("facebook_url"):
        prompt_parts.append(f"- Facebook: {profile.get('facebook_url')}")
    if profile.get("bio_plain"):
        prompt_parts.append(f"- Giới thiệu chuyên môn: {profile.get('bio_plain')}")

    # 3. Skills by category
    prompt_parts.append("\n### 2. KỸ NĂNG VÀ CÔNG NGHỆ CHUYÊN SÂU:")
    cats: Dict[str, List[str]] = {}
    for s in skills:
        cat = s.get("category", "Kỹ năng khác")
        name = s.get("name")
        if name:
            cats.setdefault(cat, []).append(name)

    for cat, items in cats.items():
        prompt_parts.append(f"- **{cat}**: {', '.join(items)}")

    # 4. Projects
    if projects:
        prompt_parts.append("\n### 3. CÁC DỰ ÁN THỰC TẾ TIÊU BIỂU:")
        for idx, p in enumerate(projects, 1):
            feat = " [⭐ NỔI BẬT]" if p.get("featured") else ""
            prompt_parts.append(f"* **Dự án {idx}: {p.get('title')}{feat}**")
            prompt_parts.append(f"  - Công nghệ: {p.get('technologies', 'N/A')}")
            if p.get("summary"):
                prompt_parts.append(f"  - Tóm tắt: {p.get('summary')}")
            if p.get("description_plain"):
                prompt_parts.append(f"  - Chi tiết giải pháp: {p.get('description_plain')[:350]}...")
            if p.get("detail_url"):
                prompt_parts.append(f"  - Link xem chi tiết trên Portfolio: [{p.get('title')}]({p.get('detail_url')})")
            if p.get("demo_url"):
                prompt_parts.append(f"  - Live Demo: {p.get('demo_url')}")
            if p.get("source_url"):
                prompt_parts.append(f"  - Mã nguồn GitHub: {p.get('source_url')}")

    # 5. Work experience
    if work_items:
        prompt_parts.append("\n### 4. QUÁ TRÌNH LÀM VIỆC & KINH NGHIỆM:")
        for idx, w in enumerate(work_items, 1):
            prompt_parts.append(f"* **{w.get('title')} ({w.get('period')})** - {w.get('role')} tại {w.get('company')}")
            if w.get("technologies"):
                prompt_parts.append(f"  - Stack: {w.get('technologies')}")
            if w.get("summary_plain"):
                prompt_parts.append(f"  - Nội dung: {w.get('summary_plain')}")
            if w.get("detail_url"):
                prompt_parts.append(f"  - Link chi tiết quá trình: [{w.get('title')}]({w.get('detail_url')})")

    # 6. Knowledge Articles
    if articles:
        prompt_parts.append("\n### 5. BÀI VIẾT CHIA SẺ KIẾN THỨC:")
        for a in articles:
            detail_link = f"[{a.get('title')}]({a.get('detail_url')})" if a.get("detail_url") else a.get('title')
            prompt_parts.append(f"- **{detail_link}** ({a.get('category')}): {a.get('summary')}")

    prompt_parts.append("\n[QUY TẮC BẮT BUỘC VỀ DỰ ÁN & ĐIỀU HƯỚNG LIÊN KẾT]:")
    prompt_parts.append("1. DỰ ÁN RẠP CHIẾU PHIM / ĐẶT VÉ PHIM: Anh Khoa ĐÃ THỰC HIỆN dự án 'Hệ thống đặt vé xem phim có tích hợp ChatBot hỗ trợ khách hàng'. Bất cứ khi nào người dùng hỏi về 'rạp chiếu phim', 'vé xem phim', 'cinema', 'phim', bạn phải tự hào giới thiệu chi tiết dự án này (Java, Spring Boot, SQL Server, Python ChatBot), tính năng chọn ghế - giữ ghế, link [👉 Xem chi tiết dự án](/projects/1) và link GitHub https://github.com/quockhoa53/WebCinema_Chatbot.")
    prompt_parts.append("2. CÁC DỰ ÁN KHÁC: Liệt kê đúng các dự án trong mục [3. CÁC DỰ ÁN THỰC TẾ TIÊU BIỂU]. Nếu hỏi về lĩnh vực hoàn toàn chưa làm (như nông nghiệp, vũ trụ), mới thông báo chưa có thông tin.")
    prompt_parts.append("3. CHÈN LINK ĐIỀU HƯỚNG (LINK NỘI BỘ):")
    prompt_parts.append("   - Khi nhắc đến Dự án: Luôn chèn link [👉 Xem chi tiết dự án](/projects/1) và link GitHub.")
    prompt_parts.append("   - Khi nhắc đến Bài viết kiến thức: Luôn chèn link [📖 Đọc bài viết chi tiết](/knowledge/clean-architecture-spring-boot).")
    prompt_parts.append("   - Khi người dùng muốn xem thêm toàn bộ dự án: Chèn link [📂 Xem tất cả dự án](/projects).")
    prompt_parts.append("   - Khi người dùng muốn liên hệ hoặc hợp tác: Luôn kèm link [📩 Gửi tin nhắn trực tiếp qua trang Liên hệ](/contact).")
    prompt_parts.append("4. THÔNG TIN LIÊN HỆ: Khi người dùng hỏi về thông tin liên hệ, cách thức liên lạc, số điện thoại, email: BẮT BUỘC cung cấp đầy đủ: Số điện thoại / Zalo: 0969 895 549, Email: nguyenquockhoa5549@gmail.com, GitHub: https://github.com/quockhoa53, LinkedIn: https://www.linkedin.com/in/quockhoa và link [📩 Gửi tin nhắn trực tiếp qua trang Liên hệ](/contact). Tuyệt đối không tự động đưa chuyện tình cảm/người yêu vào.")
    prompt_parts.append("5. CHỈ KHI NGƯỜI DÙNG CHỦ ĐỘNG HỎI ĐÍCH DANH VỀ 'người yêu của Khoa', 'bạn gái', 'chị Diệu', 'chuyện tình cảm': Mới trả lời với thái độ ấm áp, vui vẻ, tự hào và khéo léo rằng người yêu của anh Khoa là chị Diệu – chuyên viên Marketing xinh đẹp, tài năng và luôn là nguồn động lực tuyệt vời của anh Khoa! 🥰✨")
    prompt_parts.append("6. Hãy dựa trên các thông tin thực tế từ [KNOWLEDGE_CONTEXT] và phong cách người dùng đã được phân tích để đưa ra câu trả lời phù hợp, chính xác và chuyên nghiệp nhất.")

    return "\n".join(prompt_parts)
