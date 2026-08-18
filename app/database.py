import logging
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
    """Removes HTML markup from content for clean LLM ingestion."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", str(text))
    return re.sub(r"\s+", " ", clean).strip()


def get_db_connection():
    """Establishes direct PostgreSQL connection to read safe tables."""
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            connect_timeout=3,
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

    try:
        res = requests.get(f"{base_url}/api/profile", timeout=3)
        if res.status_code == 200:
            p = res.json()
            p["bio_plain"] = strip_html_tags(p.get("bio", ""))
            result["profile"] = p
    except Exception:
        pass

    try:
        res = requests.get(f"{base_url}/api/projects", timeout=3)
        if res.status_code == 200:
            result["projects"] = [
                {**p, "description_plain": strip_html_tags(p.get("description", ""))}
                for p in res.json()
            ]
    except Exception:
        pass

    try:
        res = requests.get(f"{base_url}/api/skills", timeout=3)
        if res.status_code == 200:
            result["skills"] = res.json()
    except Exception:
        pass

    try:
        res = requests.get(f"{base_url}/api/knowledge/articles", timeout=3)
        if res.status_code == 200:
            result["knowledge_articles"] = [
                {**a, "content_plain": strip_html_tags(a.get("content", ""))[:600]}
                for a in res.json()
            ]
    except Exception:
        pass

    try:
        res = requests.get(f"{base_url}/api/work", timeout=3)
        if res.status_code == 200:
            result["work_items"] = [
                {**w, "summary_plain": strip_html_tags(w.get("summary", ""))}
                for w in res.json()
            ]
    except Exception:
        pass

    return result


def get_live_portfolio_data(force_refresh: bool = False) -> Dict[str, Any]:
    """Returns cached portfolio knowledge with TTL expiration."""
    global _KNOWLEDGE_CACHE, _KNOWLEDGE_TIMESTAMP

    now = time.time()
    ttl_seconds = settings.KNOWLEDGE_CACHE_TTL_MINUTES * 60
    if not force_refresh and _KNOWLEDGE_CACHE and (now - _KNOWLEDGE_TIMESTAMP < ttl_seconds):
        return _KNOWLEDGE_CACHE

    data = fetch_from_postgres()
    if not data:
        data = fetch_from_rest_api()

    if data:
        _KNOWLEDGE_CACHE = data
        _KNOWLEDGE_TIMESTAMP = now

    return _KNOWLEDGE_CACHE
