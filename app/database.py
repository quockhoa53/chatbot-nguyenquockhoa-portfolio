import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
import psycopg2
import psycopg2.extras
import requests
from app.config import settings

logger = logging.getLogger("database")
logging.basicConfig(level=logging.INFO)

# In-memory knowledge cache
_KNOWLEDGE_CACHE: Dict[str, Any] = {}
_KNOWLEDGE_TIMESTAMP = 0


import html


def strip_html_tags(text: str) -> str:
    """Removes HTML markup, decodes entities, and keeps structured line breaks for LLM ingestion."""
    if not text:
        return ""
    # Convert block elements to line breaks
    text = re.sub(r"<(?:h[1-6]|p|div|tr|li|br)[^>]*>", "\n", str(text), flags=re.IGNORECASE)
    # Strip remaining HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities like &nbsp;, &amp;, &lt;, &gt;
    clean = html.unescape(clean).replace("\xa0", " ").replace("&nbsp;", " ")
    # Normalize whitespace
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n\s*\n+", "\n", clean)
    return clean.strip()


def get_db_connection():
    """Establishes direct PostgreSQL connection to read safe tables."""
    try:
        ssl_mode = os.getenv("DB_SSL", "require" if "neon.tech" in settings.DB_HOST else "prefer")
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            sslmode=ssl_mode,
            connect_timeout=6,
        )
        return conn
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed ({e}). Attempting REST API fallback.")
        return None


def fetch_from_postgres() -> Optional[Dict[str, Any]]:
    """Queries whitelisted public tables directly from PostgreSQL."""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1. Profile
        cursor.execute("""
            SELECT id, full_name, headline, bio, short_bio, email, phone, location, 
                   github_url, linkedin_url, facebook_url, avatar_url
            FROM profiles LIMIT 1;
        """)
        profile = cursor.fetchone() or {}
        if profile.get("bio"):
            profile["bio_plain"] = strip_html_tags(profile["bio"])

        # 2. Projects (Safe columns)
        cursor.execute("""
            SELECT id, title, description, technologies, featured, demo_url, source_url
            FROM projects ORDER BY featured DESC, id ASC;
        """)
        raw_projects = cursor.fetchall() or []
        projects = []
        for p in raw_projects:
            desc_plain = strip_html_tags(p.get("description", ""))
            pid = p.get("id")
            projects.append({
                "id": pid,
                "title": p.get("title"),
                "technologies": p.get("technologies"),
                "featured": p.get("featured"),
                "summary": desc_plain[:180] + "..." if len(desc_plain) > 180 else desc_plain,
                "description_plain": desc_plain,
                "demo_url": p.get("demo_url"),
                "source_url": p.get("source_url"),
                "detail_url": f"/projects/{pid}",
            })

        # 3. Skills
        cursor.execute("""
            SELECT id, name, category, proficiency, display_order
            FROM skills ORDER BY display_order ASC, name ASC;
        """)
        skills = cursor.fetchall() or []

        # 4. Knowledge Articles
        cursor.execute("""
            SELECT a.id, a.title, a.slug, a.summary, a.content, a.published_at, c.name as category_name
            FROM knowledge_articles a
            LEFT JOIN knowledge_categories c ON a.category_id = c.id
            WHERE a.status = 'PUBLISHED'
            ORDER BY a.published_at DESC LIMIT 15;
        """)
        raw_articles = cursor.fetchall() or []
        articles = []
        for a in raw_articles:
            slug = a.get("slug")
            articles.append({
                "id": a.get("id"),
                "title": a.get("title"),
                "slug": slug,
                "category": a.get("category_name"),
                "summary": a.get("summary") or strip_html_tags(a.get("content", ""))[:180],
                "content_plain": strip_html_tags(a.get("content", ""))[:600],
                "detail_url": f"/knowledge/{slug}" if slug else "/knowledge",
            })

        # 5. Work Experience Items
        cursor.execute("""
            SELECT id, slug, company, role, period, title, summary, content, technologies, display_order
            FROM work_items 
            WHERE published = TRUE
            ORDER BY display_order ASC;
        """)
        raw_work = cursor.fetchall() or []
        work_items = []
        for w in raw_work:
            slug = w.get("slug")
            work_items.append({
                "id": w.get("id"),
                "slug": slug,
                "company": w.get("company"),
                "role": w.get("role"),
                "period": w.get("period"),
                "title": w.get("title"),
                "summary_plain": strip_html_tags(w.get("summary", "")),
                "content_plain": strip_html_tags(w.get("content", "")),
                "technologies": w.get("technologies"),
                "detail_url": f"/work-process/{slug}" if slug else "/work-process",
            })

        cursor.close()
        conn.close()

        return {
            "profile": profile,
            "projects": projects,
            "skills": skills,
            "knowledge_articles": articles,
            "work_items": work_items,
        }

    except Exception as e:
        logger.error(f"Error querying PostgreSQL database: {e}")
        if conn:
            conn.close()
        return None


def fetch_from_rest_api() -> Dict[str, Any]:
    """Fallback fetcher querying public endpoints from Portfolio Backend REST API."""
    base_url = settings.PORTFOLIO_BE_URL.rstrip("/")
    result = {
        "profile": {},
        "projects": [],
        "skills": [],
        "knowledge_articles": [],
        "work_items": [],
    }

    # 1. Profile
    try:
        res = requests.get(f"{base_url}/profile", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            p = payload.get("data", payload)
            if isinstance(p, dict):
                bio = p.get("bio", "")
                result["profile"] = {
                    "id": p.get("id"),
                    "full_name": p.get("fullName") or p.get("full_name") or "Nguyễn Quốc Khoa",
                    "headline": p.get("headline") or "Full-stack Developer",
                    "short_bio": p.get("shortBio") or p.get("short_bio"),
                    "bio_plain": strip_html_tags(bio),
                    "email": p.get("email") or "nguyenquockhoa5549@gmail.com",
                    "phone": p.get("phone") or "0969895549",
                    "location": p.get("location") or "Việt Nam",
                    "avatar_url": p.get("avatarUrl") or p.get("avatar_url"),
                    "github_url": p.get("githubUrl") or p.get("github_url") or "https://github.com/quockhoa53",
                    "linkedin_url": p.get("linkedinUrl") or p.get("linkedin_url") or "https://www.linkedin.com/in/quockhoa",
                    "facebook_url": p.get("facebookUrl") or p.get("facebook_url"),
                }
    except Exception as e:
        logger.warning(f"Failed to fetch profile from REST API: {e}")

    # 2. Projects
    try:
        res = requests.get(f"{base_url}/projects", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            raw_projects = payload.get("data", payload)
            if isinstance(raw_projects, list):
                for p in raw_projects:
                    pid = p.get("id")
                    desc = p.get("description", "")
                    desc_plain = strip_html_tags(desc)
                    result["projects"].append({
                        "id": pid,
                        "title": p.get("title"),
                        "technologies": p.get("technologies"),
                        "featured": p.get("featured", False),
                        "summary": desc_plain[:180] + "..." if len(desc_plain) > 180 else desc_plain,
                        "description_plain": desc_plain,
                        "demo_url": p.get("demoUrl") or p.get("demo_url"),
                        "source_url": p.get("sourceUrl") or p.get("source_url"),
                        "detail_url": f"/projects/{pid}",
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch projects from REST API: {e}")

    # 3. Skills
    try:
        res = requests.get(f"{base_url}/skills", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            raw_skills = payload.get("data", payload)
            if isinstance(raw_skills, list):
                result["skills"] = raw_skills
    except Exception as e:
        logger.warning(f"Failed to fetch skills from REST API: {e}")

    # 4. Knowledge Articles
    try:
        res = requests.get(f"{base_url}/knowledge/articles", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            raw_articles = payload.get("data", payload)
            if isinstance(raw_articles, list):
                for a in raw_articles:
                    slug = a.get("slug")
                    content = a.get("content", "")
                    result["knowledge_articles"].append({
                        "id": a.get("id"),
                        "title": a.get("title"),
                        "slug": slug,
                        "category": a.get("categoryName") or a.get("category_name") or (a.get("category", {}).get("name") if isinstance(a.get("category"), dict) else ""),
                        "summary": a.get("summary") or strip_html_tags(content)[:180],
                        "content_plain": strip_html_tags(content)[:600],
                        "detail_url": f"/knowledge/{slug}" if slug else "/knowledge",
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch knowledge articles from REST API: {e}")

    # 5. Work Items
    try:
        res = requests.get(f"{base_url}/work-items", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            raw_work = payload.get("data", payload)
            if isinstance(raw_work, list):
                for w in raw_work:
                    slug = w.get("slug")
                    summary = w.get("summary", "")
                    content = w.get("content", "")
                    result["work_items"].append({
                        "id": w.get("id"),
                        "slug": slug,
                        "company": w.get("company"),
                        "role": w.get("role"),
                        "period": w.get("period"),
                        "title": w.get("title"),
                        "summary_plain": strip_html_tags(summary),
                        "content_plain": strip_html_tags(content),
                        "technologies": w.get("technologies"),
                        "detail_url": f"/work-process/{slug}" if slug else "/work-process",
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch work items from REST API: {e}")

    return result


FALLBACK_PORTFOLIO_DATA: Dict[str, Any] = {
    "profile": {
        "id": 1,
        "full_name": "Nguyễn Quốc Khoa",
        "headline": "Full-stack Developer & Backend AI Engineer",
        "short_bio": "Software Engineer đam mê xây dựng hệ thống Backend quy mô lớn, Clean Architecture, DDD, Microservices và tích hợp AI/LLMs.",
        "bio_plain": "Nguyễn Quốc Khoa – Software Engineer đam mê xây dựng hệ thống Backend quy mô lớn, Clean Architecture, DDD, Microservices và tích hợp AI/LLMs.",
        "email": "nguyenquockhoa5549@gmail.com",
        "phone": "0969895549",
        "location": "Việt Nam",
        "avatar_url": "",
        "github_url": "https://github.com/quockhoa53",
        "linkedin_url": "https://www.linkedin.com/in/quockhoa",
        "facebook_url": "",
    },
    "projects": [
        {
            "id": 1,
            "title": "Hệ thống đặt vé xem phim có tích hợp ChatBot hỗ trợ khách hàng",
            "technologies": "Java, Spring Boot, SQL Server, Python, ChatBot AI, HTML, CSS, JavaScript",
            "featured": True,
            "summary": "Hệ thống đặt vé xem phim trực tuyến tích hợp ChatBot AI hỗ trợ đặt vé, đề xuất phim và giải đáp thắc mắc 24/7.",
            "description_plain": (
                "I. TỔNG QUAN\n"
                "Dự án nhóm: 3 người\n"
                "Hệ thống đặt vé: Frontend: HTML, CSS, JavaScript. Backend: Java, Spring Boot. Cơ sở dữ liệu: SQL Server.\n"
                "Hệ thống ChatBot: Python.\n\n"
                "CÁC TÍNH NĂNG CHÍNH CỦA HỆ THỐNG:\n"
                "1. Phần Chatbot:\n"
                "- Sử dụng Deep Learning với Neural Network 3 lớp để nhận dạng văn bản và sử dụng nltk để xử lý ngôn ngữ tự nhiên.\n"
                "- Sử dụng Content-Based Filtering (CBF) kết hợp với Time-Based Analysis để đề xuất phim dựa trên thể loại yêu thích, nội dung phim và thời gian xem phim phổ biến của người dùng.\n"
                "- Sử dụng 3 phương pháp chính (TF-IDF, Word2Vec, và Bag of Words) để phân tích nội dung phim dựa trên mô tả và thể loại, nhằm tính toán độ tương đồng giữa các phim và đưa ra gợi ý phim phù hợp.\n\n"
                "2. Ngữ cảnh hoạt động của Chatbot:\n"
                "- Ngữ cảnh chào hỏi, tạm biệt.\n"
                "- Ngữ cảnh đặt vé.\n"
                "- Ngữ cảnh đề xuất phim: Đề xuất dựa trên tất cả vé người dùng đã đặt để biết thể loại và khung giờ yêu thích. "
                "Có đăng nhập: đề xuất theo sở thích + độ phổ biến của phim (số lượng vé đặt nhiều tỉ lệ 0.7, đánh giá khách hàng tốt tỉ lệ 0.3). "
                "Không đăng nhập: đề xuất theo độ phổ biến (vé đặt nhiều tỉ lệ 0.7, đánh giá tỉ lệ 0.3).\n"
                "- 2 dạng đề xuất: (1) Theo câu lệnh người dùng nhập (ví dụ: 'Suggest a movie that you think I\\'ll like') và (2) Đề xuất tự động qua các nút kêu gọi ('You might love my suggest', 'Booking ticket Smile', 'Suggest a movie').\n"
                "- Ngữ cảnh đề xuất phim tương tự: Dựa trên tên phim, nội dung, thể loại phim.\n\n"
                "3. Phần Hệ Thống Đặt Vé (Khách Hàng):\n"
                "- Đăng nhập, Đăng ký.\n"
                "- Trang chủ: 3 Banner phim hot (vé bán + đánh giá), 6 phim mới nhất, sự kiện rạp, danh mục Đang chiếu & Sắp chiếu (4 phim/mục, nút View All), Top 1 phòng vé (video youtube + đánh giá 2-5 sao), Danh sách 6 đạo diễn doanh thu cao nhất.\n"
                "- Danh sách suất chiếu: 7 ngày theo thời gian thực (suất đã qua tự ẩn).\n"
                "- Chọn ghế: 3 loại ghế (Ghế thường: 45.000đ, Ghế VIP: 50.000đ, Ghế đôi: 100.000đ). 3 trạng thái ghế (Trống - xanh lá, Đã đặt - đỏ, Đang chọn - xám).\n"
                "- Giữ ghế: Giữ ghế trong 5 phút, hết 5 phút tự động hủy, có nút Cancel Booking.\n"
                "- Đánh giá phim (1-5 sao).\n\n"
                "4. Phần Quản Trị (Admin):\n"
                "- Dashboard: Tổng số người dùng, tổng số vé bán theo chi nhánh, tổng số phim, tổng doanh thu, Top phim hot.\n"
                "- Quản lý khách hàng (xem chi tiết, thêm mới).\n"
                "- Quản lý phim (chi tiết, thêm, sửa).\n"
                "- Quản lý đạo diễn, diễn viên (chi tiết vai diễn, thêm, sửa).\n"
                "- Quản lý loại ghế (thêm, sửa).\n"
                "- Quản lý vé đặt (chi tiết vé).\n"
                "- Quản lý phòng chiếu, lịch chiếu (thông tin, thêm mới).\n"
                "- Quản lý thể loại phim (thêm, sửa)."
            ),
            "demo_url": None,
            "source_url": "https://github.com/quockhoa53/WebCinema_Chatbot",
            "detail_url": "/projects/1",
        }
    ],
    "skills": [
        {"name": "Java & Spring Boot", "category": "Backend Development"},
        {"name": "Python & Machine Learning", "category": "AI & Data Science"},
        {"name": "PostgreSQL & SQL Server", "category": "Databases"},
        {"name": "React & JavaScript", "category": "Frontend Development"},
        {"name": "Docker & Cloud", "category": "DevOps & Infrastructure"},
    ],
    "knowledge_articles": [
        {
            "id": 1,
            "title": "Clean Architecture trong Spring Boot",
            "slug": "clean-architecture-spring-boot",
            "category": "Backend Architecture",
            "summary": "Hướng dẫn áp dụng Clean Architecture, Domain-Driven Design trong các dự án Spring Boot quy mô lớn.",
            "content_plain": "Hướng dẫn áp dụng Clean Architecture, Domain-Driven Design trong các dự án Spring Boot quy mô lớn.",
            "detail_url": "/knowledge/clean-architecture-spring-boot",
        }
    ],
    "work_items": [],
}


def get_live_portfolio_data(force_refresh: bool = False) -> Dict[str, Any]:
    """Returns cached portfolio knowledge with TTL expiration, guaranteeing rich fallback."""
    global _KNOWLEDGE_CACHE, _KNOWLEDGE_TIMESTAMP

    now = time.time()
    ttl_seconds = settings.KNOWLEDGE_CACHE_TTL_MINUTES * 60
    if not force_refresh and _KNOWLEDGE_CACHE and (now - _KNOWLEDGE_TIMESTAMP < ttl_seconds):
        if _KNOWLEDGE_CACHE.get("projects") and len(_KNOWLEDGE_CACHE.get("projects", [])) > 0:
            return _KNOWLEDGE_CACHE

    data = fetch_from_postgres()
    if not data or not data.get("projects") or len(data.get("projects", [])) == 0:
        rest_data = fetch_from_rest_api()
        if rest_data and rest_data.get("projects") and len(rest_data.get("projects", [])) > 0:
            data = rest_data

    if data and data.get("projects") and len(data.get("projects", [])) > 0:
        _KNOWLEDGE_CACHE = data
        _KNOWLEDGE_TIMESTAMP = now
        return _KNOWLEDGE_CACHE

    # Return robust fallback if both live sources are cold-starting or unavailable
    return FALLBACK_PORTFOLIO_DATA
