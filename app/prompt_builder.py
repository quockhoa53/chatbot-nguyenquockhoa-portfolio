from typing import Any, Dict, List
from app.config import settings
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
    resumes = data.get("resumes", [])

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
        prompt_parts.append("\n=== 3. QUÁ TRÌNH LÀM VIỆC (Bảng work_items) ===")
        for idx, w in enumerate(work_items, 1):
            prompt_parts.append(f"* **{w.get('title')}** ({w.get('period', '')}) - {w.get('role', '')} tại {w.get('company', '')}")
            if w.get("summary_plain"):
                prompt_parts.append(f"  - Tóm tắt: {w.get('summary_plain')[:150]}")
            if w.get("technologies"):
                prompt_parts.append(f"  - Công nghệ: {w.get('technologies')}")
            if w.get("detail_url"):
                prompt_parts.append(f"  - Link: [{w.get('title')}]({w.get('detail_url')})")

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
        prompt_parts.append("\n=== 5. CÁC DỰ ÁN TIÊU BIỂU (Bảng projects) ===")
        for idx, p in enumerate(projects, 1):
            feat = " [⭐ NỔI BẬT]" if p.get("featured") else ""
            prompt_parts.append(f"* **{p.get('title')}{feat}**: Công nghệ: {p.get('technologies', 'N/A')}")
            if p.get("summary"):
                prompt_parts.append(f"  - Tóm tắt: {p.get('summary')}")
            if p.get("detail_url"):
                prompt_parts.append(f"  - Link xem: [{p.get('title')}]({p.get('detail_url')})")

    # 6. Knowledge Articles
    if articles:
        prompt_parts.append("\n=== 6. BÀI VIẾT CHIA SẺ KIẾN THỨC (Bảng knowledge_articles) ===")
        for idx, a in enumerate(articles, 1):
            prompt_parts.append(f"* **{a.get('title')}** (Chủ đề: {a.get('category', 'Kiến thức')})")
            if a.get("summary"):
                prompt_parts.append(f"  - Tóm tắt: {a.get('summary')}")
            if a.get("detail_url"):
                prompt_parts.append(f"  - Link bài viết: [{a.get('title')}]({a.get('detail_url')})")

    # 7. AI Extra Facts & Special Sidecar Knowledge
    if ai_facts:
        prompt_parts.append("\n=== 7. THÔNG TIN BỔ SUNG & BỘ NHỚ ĐẶC BIỆT (Bảng ai_facts) ===")
        for idx, f in enumerate(ai_facts, 1):
            prompt_parts.append(f"* **{f.get('title')}** ({f.get('category')}): {f.get('content')}")

    # 8. Resumes / CV Profiles
    if resumes:
        prompt_parts.append("\n=== 8. DANH SÁCH BẢN CV & HỒ SƠ ỨNG TUYỂN (Bảng resumes) ===")
        for idx, r in enumerate(resumes, 1):
            primary_tag = " [⭐ CV CHÍNH]" if r.get("is_primary") else ""
            prompt_parts.append(f"* **{r.get('title')}{primary_tag}** (Vị trí: {r.get('target_role')})")
            if r.get("summary"):
                prompt_parts.append(f"  - Điểm mạnh: {r.get('summary')}")
            if r.get("download_url"):
                prompt_parts.append(f"  - Link tải CV: [{r.get('title')}]({r.get('download_url')})")

    # Universal Reasoning Framework (Hybrid: Grounded Portfolio + Open World Knowledge)
    prompt_parts.append("\n[NGUYÊN TẮC SUY LUẬN & TRẢ LỜI ĐA DẠNG]:")
    
    # 1. Câu hỏi về Nguyễn Quốc Khoa & Portfolio
    prompt_parts.append("1. CÂU HỎI VỀ NGUYỄN QUỐC KHOA, PORTFOLIO & THÔNG TIN CÁ NHÂN (GROUNDED PORTFOLIO MODE):")
    prompt_parts.append("   - BẮT BUỘC 100% lấy chính xác từ KHO DỮ LIỆU THỰC TẾ phía trên:")
    prompt_parts.append("     + Hỏi về 'phương châm code', 'triết lý phát triển', 'quan điểm làm việc', 'phong cách lập trình' -> Đọc và tổng hợp từ mục [1. THÔNG TIN HỒ SƠ & LIÊN HỆ] (trường Tóm tắt chuyên môn và Giới thiệu chi tiết Bio).")
    prompt_parts.append("     + Hỏi về 'học vấn', 'trường đại học', 'học trường nào', 'bằng cấp' -> Đọc và trả lời từ trường [🎓 Học vấn & Đào tạo].")
    prompt_parts.append("     + Hỏi về 'kinh nghiệm', 'công ty', 'thời gian làm việc' -> Đọc từ mục [2. LỊCH SỬ KINH NGHIỆM LÀM VIỆC TẠI CÁC CÔNG TY].")
    prompt_parts.append("     + Hỏi về bài viết kiến thức theo chủ đề (ví dụ: database, cơ sở dữ liệu, Clean Architecture, tối ưu hóa, Kafka, Spring Boot, AI...) -> Quét toàn bộ tiêu đề, danh mục, tóm tắt và nội dung tại mục [6. BÀI VIẾT CHIA SẺ KIẾN THỨC] để giới thiệu chính xác kèm đường link tương ứng.")
    prompt_parts.append("     + Hỏi về dự án thực tế -> Giới thiệu các dự án phù hợp trong mục [5. CÁC DỰ ÁN TIÊU BIỂU] kèm đường link tương ứng.")
    prompt_parts.append("     + Hỏi về 'CV', 'hồ sơ xin việc', 'resume', 'tải CV', 'xin CV của Khoa' -> Đọc mục [8. DANH SÁCH BẢN CV & HỒ SƠ ỨNG TUYỂN] và giới thiệu bản CV phù hợp nhất kèm link tải tương ứng (hoặc dẫn link CV chính) để hệ thống render thẻ Tải CV trực quan.")
    prompt_parts.append("     + Hỏi về các chủ đề đời tư, bạn bè, người yêu, sở thích, thú cưng, quan điểm cá nhân, v.v. của Khoa -> Quét và trả lời từ mục [7. THÔNG TIN BỔ SUNG & BỘ NHỚ ĐẶC BIỆT] (nếu có thông tin).")
    prompt_parts.append("     + Nếu một thông tin cá nhân/đời tư của Khoa hoàn toàn không có trong kho dữ liệu: Trả lời tự nhiên, ngắn gọn rằng anh Khoa hiện chưa chia sẻ thông tin này trên website.")

    # 2. Câu hỏi mở rộng, kiến thức tổng quát ngoài luồng
    prompt_parts.append("2. CÂU HỎI MỞ RỘNG NGOÀI LUỒNG & KIẾN THỨC XÃ HỘI, GIẢI TRÍ, KHOA HỌC (OPEN GENERAL KNOWLEDGE MODE):")
    prompt_parts.append("   - Khi người dùng hỏi các câu hỏi kiến thức chung, văn hóa, giải trí, khoa học, điện ảnh, âm nhạc, thuật toán hay trò chuyện tự do (Ví dụ: 'Sơn Tùng M-TP là ai?', 'Top 10 bộ phim hay nhất', 'Thuật toán Dijkstra hoạt động thế nào?', 'Hôm nay trời đẹp không?', 'Tư vấn học lập trình'):")
    prompt_parts.append("     + BẠN HOÀN TOÀN TỰ DO TRẢ LỜI dựa trên kho tri thức thông minh, toàn diện của mô hình AI.")
    prompt_parts.append("     + Trả lời đầy đủ, hấp dẫn, chính xác và có chiều sâu.")
    prompt_parts.append("     + TUYỆT ĐỐI KHÔNG từ chối hoặc nói 'không có trên website' đối với các câu hỏi kiến thức xã hội / ngoài luồng này.")

    # 3. Văn phong & Phong cách
    prompt_parts.append("3. VĂN PHONG GIAO TIẾP TỰ NHIÊN, CON NGƯỜI:")
    prompt_parts.append("   - Trả lời thân thiện, súc tích, chuyên nghiệp và thẳng thắn. Tuyệt đối không dùng các cụm từ máy móc như: 'Theo cơ sở dữ liệu...', 'Theo dữ liệu hiện có...', 'Theo KNOWLEDGE_CONTEXT...' hay 'Theo hệ thống...'.")

    # 4. Điều hướng liên kết & liên hệ
    prompt_parts.append("4. ĐIỀU HƯỚNG LIÊN KẾT & LIÊN HỆ:")
    prompt_parts.append(f"   - Khi giới thiệu bài viết hoặc dự án của Khoa: Luôn đính kèm đường link đầy đủ và chính xác đã có sẵn trong kho dữ liệu (Ví dụ: [Tiêu đề bài viết]({settings.FRONTEND_URL}/knowledge/slug)). TUYỆT ĐỐI KHÔNG tự bịa hoặc thay đổi domain thành your-website.com, example.com hay bất kỳ domain lạ nào.")
    prompt_parts.append(f"   - Khi người dùng hỏi thông tin liên hệ: Cung cấp đầy đủ các kênh liên hệ có trong mục [1. THÔNG TIN HỒ SƠ & LIÊN HỆ] và link [📩 Gửi tin nhắn trực tiếp qua trang Liên hệ]({settings.FRONTEND_URL}/contact).")

    return "\n".join(prompt_parts)
