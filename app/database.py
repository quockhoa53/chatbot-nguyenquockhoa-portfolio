import html
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


def strip_html_tags(text: str) -> str:
    """Removes HTML markup, decodes entities, and keeps structured line breaks for clean LLM ingestion."""
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
    # 1. Try environment DATABASE_URL or DB_URL if set
    db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if db_url:
        try:
            return psycopg2.connect(
                db_url,
                sslmode="require" if "neon.tech" in db_url else "prefer",
                connect_timeout=10,
            )
        except Exception as e:
            logger.warning(f"PostgreSQL connection via DATABASE_URL failed ({e}).")

    # Determine credentials with auto-fallback to Neon cloud production if local dummy credentials on cloud
    db_user = settings.DB_USER
    db_pass = settings.DB_PASSWORD
    db_host = settings.DB_HOST
    db_name = settings.DB_NAME
    db_port = settings.DB_PORT

    if "neon.tech" in db_host:
        db_user = "neondb_owner"
        db_pass = "npg_4LRx7pFVeDnr"
        db_name = "neondb"

    # 2. Try direct Neon PostgreSQL URI (100% reliable across Docker/Render/Cloud environments)
    try:
        uri = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?sslmode=require"
        return psycopg2.connect(uri, connect_timeout=10)
    except Exception as e:
        logger.warning(f"PostgreSQL direct URI connection failed ({e}). Trying keyword params...")

    # 3. Try standard keyword arguments
    try:
        ssl_mode = "require" if "neon.tech" in db_host else "prefer"
        return psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_pass,
            sslmode=ssl_mode,
            connect_timeout=10,
        )
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed ({e}). Attempting REST API fallback.")
        return None


def fetch_from_postgres() -> Optional[Dict[str, Any]]:
    """Queries safe public portfolio tables directly from PostgreSQL."""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1. Profile (Table: profiles)
        cursor.execute("""
            SELECT id, full_name, headline, bio, short_bio, email, phone, location, 
                   github_url, linkedin_url, facebook_url, avatar_url, education
            FROM profiles LIMIT 1;
        """)
        profile = cursor.fetchone() or {}
        if profile.get("bio"):
            profile["bio_plain"] = strip_html_tags(profile["bio"])

        # 2. Experiences at companies (Table: experiences)
        cursor.execute("""
            SELECT id, company, position, start_date, end_date, description, display_order
            FROM experiences 
            ORDER BY display_order ASC, start_date DESC;
        """)
        raw_exp = cursor.fetchall() or []
        experiences = []
        for e in raw_exp:
            experiences.append({
                "id": e.get("id"),
                "company": e.get("company"),
                "position": e.get("position"),
                "start_date": str(e.get("start_date")) if e.get("start_date") else "",
                "end_date": str(e.get("end_date")) if e.get("end_date") else "Hiện tại",
                "description_plain": strip_html_tags(e.get("description", "")),
                "display_order": e.get("display_order"),
            })

        # 3. Work process items (Table: work_items)
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

        # 4. Technical Skills (Table: skills)
        cursor.execute("""
            SELECT id, name, category, proficiency, display_order
            FROM skills 
            ORDER BY display_order ASC, name ASC;
        """)
        skills = cursor.fetchall() or []

        # 5. Projects (Table: projects)
        cursor.execute("""
            SELECT id, title, description, technologies, featured, demo_url, source_url, display_order
            FROM projects 
            ORDER BY featured DESC, display_order ASC, id ASC;
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
                "detail_url": f"{settings.FRONTEND_URL}/projects/{pid}",
            })

        # 6. Knowledge Articles (Table: knowledge_articles)
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
                "detail_url": f"{settings.FRONTEND_URL}/knowledge/{slug}" if slug else f"{settings.FRONTEND_URL}/knowledge",
            })

        # 7. AI Extra Facts & Sidecar Knowledge (Table: ai_facts)
        try:
            cursor.execute("""
                SELECT id, category, title, content, is_active, display_order
                FROM ai_facts
                WHERE is_active = TRUE
                ORDER BY display_order ASC, id ASC;
            """)
            raw_facts = cursor.fetchall() or []
            ai_facts = []
            for f in raw_facts:
                ai_facts.append({
                    "id": f.get("id"),
                    "category": f.get("category", "Khác"),
                    "title": f.get("title"),
                    "content": strip_html_tags(f.get("content", "")),
                    "display_order": f.get("display_order", 0),
                })
        except Exception:
            ai_facts = []

        # 8. Resumes / CV (Table: resumes)
        try:
            cursor.execute("""
                SELECT id, title, target_role, file_url, file_name, file_size, summary, is_primary, is_active, download_count
                FROM resumes
                WHERE is_active = TRUE
                ORDER BY is_primary DESC, updated_at DESC;
            """)
            raw_resumes = cursor.fetchall() or []
            resumes = []
            for r in raw_resumes:
                rid = r.get("id")
                resumes.append({
                    "id": rid,
                    "title": r.get("title"),
                    "target_role": r.get("target_role", "GENERAL"),
                    "file_url": r.get("file_url"),
                    "file_name": r.get("file_name"),
                    "summary": r.get("summary", ""),
                    "is_primary": r.get("is_primary", False),
                    "download_url": f"{settings.FRONTEND_URL}/resumes/{rid}",
                })
        except Exception:
            resumes = []

        cursor.close()
        conn.close()

        return {
            "profile": profile,
            "experiences": experiences,
            "work_items": work_items,
            "skills": skills,
            "projects": projects,
            "knowledge_articles": articles,
            "ai_facts": ai_facts,
            "resumes": resumes,
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
        "experiences": [],
        "work_items": [],
        "skills": [],
        "projects": [],
        "knowledge_articles": [],
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

    # 2. Experiences
    try:
        res = requests.get(f"{base_url}/experiences", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            raw_exp = payload.get("data", payload)
            if isinstance(raw_exp, list):
                for e in raw_exp:
                    result["experiences"].append({
                        "id": e.get("id"),
                        "company": e.get("company"),
                        "position": e.get("position"),
                        "start_date": str(e.get("startDate") or e.get("start_date") or ""),
                        "end_date": str(e.get("endDate") or e.get("end_date") or "Hiện tại"),
                        "description_plain": strip_html_tags(e.get("description", "")),
                        "display_order": e.get("displayOrder") or e.get("display_order"),
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch experiences from REST API: {e}")

    # 3. Work Items
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

    # 4. Skills
    try:
        res = requests.get(f"{base_url}/skills", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            raw_skills = payload.get("data", payload)
            if isinstance(raw_skills, list):
                result["skills"] = raw_skills
    except Exception as e:
        logger.warning(f"Failed to fetch skills from REST API: {e}")

    # 5. Projects
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
                        "detail_url": f"{settings.FRONTEND_URL}/projects/{pid}",
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch projects from REST API: {e}")

    # 6. Knowledge Articles
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
                        "detail_url": f"{settings.FRONTEND_URL}/knowledge/{slug}" if slug else f"{settings.FRONTEND_URL}/knowledge",
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch knowledge articles from REST API: {e}")

    # 7. AI Extra Facts & Sidecar Knowledge
    result["ai_facts"] = []
    try:
        res = requests.get(f"{base_url}/ai-facts", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            raw_facts = payload.get("data", payload)
            if isinstance(raw_facts, list):
                for f in raw_facts:
                    result["ai_facts"].append({
                        "id": f.get("id"),
                        "category": f.get("category", "Khác"),
                        "title": f.get("title"),
                        "content": strip_html_tags(f.get("content", "")),
                        "display_order": f.get("displayOrder", 0) or f.get("display_order", 0),
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch ai_facts from REST API: {e}")

    # 8. Resumes / CV
    result["resumes"] = []
    try:
        res = requests.get(f"{base_url}/resumes", timeout=30)
        if res.status_code == 200:
            payload = res.json()
            raw_resumes = payload.get("data", payload)
            if isinstance(raw_resumes, list):
                for r in raw_resumes:
                    rid = r.get("id")
                    result["resumes"].append({
                        "id": rid,
                        "title": r.get("title"),
                        "target_role": r.get("targetRole", "GENERAL") or r.get("target_role", "GENERAL"),
                        "file_url": r.get("fileUrl") or r.get("file_url"),
                        "file_name": r.get("fileName") or r.get("file_name"),
                        "summary": r.get("summary", ""),
                        "is_primary": r.get("isPrimary", False) or r.get("is_primary", False),
                        "download_url": f"{settings.FRONTEND_URL}/resumes/{rid}",
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch resumes from REST API: {e}")

    return result


def get_live_portfolio_data(force_refresh: bool = False) -> Dict[str, Any]:
    """Returns cached portfolio knowledge directly from live PostgreSQL database or live REST API (100% dynamic)."""
    global _KNOWLEDGE_CACHE, _KNOWLEDGE_TIMESTAMP

    now = time.time()
    ttl_seconds = settings.KNOWLEDGE_CACHE_TTL_MINUTES * 60
    if not force_refresh and _KNOWLEDGE_CACHE and _KNOWLEDGE_CACHE.get("profile") and (now - _KNOWLEDGE_TIMESTAMP < ttl_seconds):
        return _KNOWLEDGE_CACHE

    data = fetch_from_postgres()
    if not data or not data.get("profile"):
        rest_data = fetch_from_rest_api()
        if rest_data and rest_data.get("profile"):
            data = rest_data

    if data and data.get("profile"):
        _KNOWLEDGE_CACHE = data
        _KNOWLEDGE_TIMESTAMP = now
        return _KNOWLEDGE_CACHE

    if _KNOWLEDGE_CACHE and _KNOWLEDGE_CACHE.get("profile"):
        return _KNOWLEDGE_CACHE

    return {
        "profile": {},
        "experiences": [],
        "work_items": [],
        "skills": [],
        "projects": [],
        "knowledge_articles": [],
        "ai_facts": [],
    }
