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
    """Removes HTML markup from content for clean LLM ingestion."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", str(text))
    return re.sub(r"\s+", " ", clean).strip()


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
        res = requests.get(f"{base_url}/profile", timeout=5)
        if res.status_code == 200:
            payload = res.json()
            p = payload.get("data", payload)
            if isinstance(p, dict):
                bio = p.get("bio", "")
                result["profile"] = {
                    "id": p.get("id"),
                    "full_name": p.get("fullName") or p.get("full_name"),
                    "headline": p.get("headline"),
                    "short_bio": p.get("shortBio") or p.get("short_bio"),
                    "bio_plain": strip_html_tags(bio),
                    "email": p.get("email"),
                    "phone": p.get("phone"),
                    "location": p.get("location"),
                    "avatar_url": p.get("avatarUrl") or p.get("avatar_url"),
                    "github_url": p.get("githubUrl") or p.get("github_url"),
                    "linkedin_url": p.get("linkedinUrl") or p.get("linkedin_url"),
                    "facebook_url": p.get("facebookUrl") or p.get("facebook_url"),
                }
    except Exception as e:
        logger.warning(f"Failed to fetch profile from REST API: {e}")

    # 2. Projects
    try:
        res = requests.get(f"{base_url}/projects", timeout=5)
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
        res = requests.get(f"{base_url}/skills", timeout=5)
        if res.status_code == 200:
            payload = res.json()
            raw_skills = payload.get("data", payload)
            if isinstance(raw_skills, list):
                result["skills"] = raw_skills
    except Exception as e:
        logger.warning(f"Failed to fetch skills from REST API: {e}")

    # 4. Knowledge Articles
    try:
        res = requests.get(f"{base_url}/knowledge/articles", timeout=5)
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
        res = requests.get(f"{base_url}/work-items", timeout=5)
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


def get_live_portfolio_data(force_refresh: bool = False) -> Dict[str, Any]:
    """Returns cached portfolio knowledge with TTL expiration, never serving empty projects."""
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

    return data or _KNOWLEDGE_CACHE or {
        "profile": {},
        "projects": [],
        "skills": [],
        "knowledge_articles": [],
        "work_items": [],
    }
