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
    prompt_parts.append(f"- Email liên hệ: {profile.get('email', 'quockhoa.work@gmail.com')}")
    if profile.get("phone"):
        prompt_parts.append(f"- Số điện thoại / Zalo: {profile.get('phone')}")
    prompt_parts.append(f"- Địa điểm: {profile.get('location', 'Việt Nam')}")
    if profile.get("github_url"):
        prompt_parts.append(f"- GitHub: {profile.get('github_url')}")
    if profile.get("linkedin_url"):
        prompt_parts.append(f"- LinkedIn: {profile.get('linkedin_url')}")
    if profile.get("facebook_url"):
        prompt_parts.append(f"- Facebook: {profile.get('facebook_url')}")
    if profile.get("short_bio"):
        prompt_parts.append(f"- Tóm tắt: {profile.get('short_bio')}")
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
    prompt_parts.append("1. VỀ DỰ ÁN: Hãy tra cứu kỹ trong mục [3. CÁC DỰ ÁN THỰC TẾ TIÊU BIỂU]. Nhận diện chính xác từ đồng nghĩa theo ngữ cảnh (ví dụ: 'rạp chiếu phim', 'xem phim', 'đặt vé phim', 'cinema' chính là dự án 'Hệ thống đặt vé xem phim có tích hợp ChatBot hỗ trợ khách hàng').")
    prompt_parts.append("2. NẾU NGƯỜI DÙNG HỎI VỀ DỰ ÁN HOÀN TOÀN KHÔNG CÓ TRONG DANH SÁCH (ví dụ: y tế, nông nghiệp, bệnh viện...): Hãy trả lời thành thật rằng trong danh mục dự án chính thức của anh Khoa hiện chưa có thông tin về dự án này và giới thiệu các dự án nổi bật hiện có.")
    prompt_parts.append("3. CHÈN LINK ĐIỀU HƯỚNG (LINK NỘI BỘ):")
    prompt_parts.append("   - Khi đề cập hoặc giải thích về một Dự án cụ thể: Luôn chèn link Markdown dẫn đến trang chi tiết (ví dụ: [👉 Xem chi tiết dự án](/projects/1)) và link GitHub (nếu có).")
    prompt_parts.append("   - Khi nhắc đến Bài viết kiến thức: Luôn chèn link Markdown dẫn đến bài viết (ví dụ: [📖 Đọc bài viết chi tiết](/knowledge/clean-architecture-spring-boot)).")
    prompt_parts.append("   - Khi người dùng muốn xem thêm toàn bộ dự án: Chèn link [📂 Xem tất cả dự án](/projects).")
    prompt_parts.append("   - Khi người dùng muốn liên hệ hoặc hợp tác: Luôn kèm link [📩 Gửi tin nhắn trực tiếp qua trang Liên hệ](/contact).")
    prompt_parts.append("4. Hãy dựa trên các thông tin thực tế từ [KNOWLEDGE_CONTEXT] và phong cách người dùng đã được phân tích để đưa ra câu trả lời phù hợp, chính xác và chuyên nghiệp nhất.")

    return "\n".join(prompt_parts)
