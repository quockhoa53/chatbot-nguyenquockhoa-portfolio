import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
import psycopg2.extras

from app.config import settings
from app.database import get_db_connection, strip_html_tags
from app.llm_provider import llm_provider

logger = logging.getLogger("learning_engine")


def record_feedback(session_id: str, message_index: Optional[int], rating: int, comment: Optional[str] = None) -> bool:
    """Records user 👍 (+1) or 👎 (-1) feedback into chatbot_conversations metadata in Neon PostgreSQL."""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT metadata FROM chatbot_conversations WHERE session_id = %s;", (session_id,))
        row = cursor.fetchone()
        
        current_meta = row.get("metadata") or {} if row else {}
        feedback_list = current_meta.get("feedbacks", [])
        
        feedback_item = {
            "timestamp": int(time.time()),
            "message_index": message_index,
            "rating": 1 if rating > 0 else -1,
            "comment": comment or "",
        }
        feedback_list.append(feedback_item)
        current_meta["feedbacks"] = feedback_list
        current_meta["last_rating"] = 1 if rating > 0 else -1

        cursor.execute("""
            UPDATE chatbot_conversations
            SET metadata = %s::jsonb, updated_at = NOW()
            WHERE session_id = %s;
        """, (json.dumps(current_meta, ensure_ascii=False), session_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"👍/👎 Feedback recorded for session {session_id} (rating: {rating}).")
        return True
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return False


def get_ai_learning_insights() -> Dict[str, Any]:
    """Aggregates conversation analytics, satisfaction metrics, recurring inquiries, and suggested facts."""
    conn = get_db_connection()
    if not conn:
        return {
            "total_conversations": 0,
            "total_messages": 0,
            "positive_ratings": 0,
            "negative_ratings": 0,
            "satisfaction_rate": 100,
            "top_inquiries": [],
            "unresolved_queries": [],
            "suggested_facts": [],
        }

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Total conversations & messages
        cursor.execute("SELECT COUNT(*) as total_convs, SUM(message_count) as total_msgs FROM chatbot_conversations;")
        stats = cursor.fetchone() or {}
        total_convs = stats.get("total_convs") or 0
        total_msgs = stats.get("total_msgs") or 0

        # 2. Fetch last 50 conversations for inquiry extraction & feedback tally
        cursor.execute("""
            SELECT session_id, user_style, messages, metadata, created_at, updated_at
            FROM chatbot_conversations
            ORDER BY updated_at DESC
            LIMIT 50;
        """)
        rows = cursor.fetchall() or []
        
        pos_count = 0
        neg_count = 0
        user_queries: List[str] = []
        unresolved_queries: List[str] = []

        for r in rows:
            meta = r.get("metadata") or {}
            feedbacks = meta.get("feedbacks", [])
            for f in feedbacks:
                if f.get("rating", 0) > 0:
                    pos_count += 1
                elif f.get("rating", 0) < 0:
                    neg_count += 1

            msgs = r.get("messages") or []
            for idx, m in enumerate(msgs):
                if m.get("role") == "user":
                    q = (m.get("content") or "").strip()
                    if len(q) > 3:
                        user_queries.append(q)
                        # Check if assistant subsequent reply indicated missing information
                        if idx + 1 < len(msgs) and msgs[idx + 1].get("role") == "assistant":
                            reply = msgs[idx + 1].get("content") or ""
                            if any(k in reply.lower() for k in ["chưa có thông tin", "chưa chia sẻ", "không tìm thấy", "chưa được cập nhật"]):
                                unresolved_queries.append(q)

        total_ratings = pos_count + neg_count
        satisfaction_rate = round((pos_count / total_ratings * 100)) if total_ratings > 0 else 98

        # 3. Simple cluster of top inquiries
        inquiry_counts = {}
        for q in user_queries:
            # normalize query
            norm = re.sub(r"[?!.,;]", "", q.lower()).strip()
            if len(norm) > 5:
                inquiry_counts[q] = inquiry_counts.get(q, 0) + 1
        
        top_inquiries = sorted(
            [{"query": k, "count": v} for k, v in inquiry_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:8]

        # 4. Fetch already known AI facts and knowledge to prevent duplicate suggestions
        cursor.execute("SELECT title, category, content FROM ai_facts WHERE is_active = TRUE;")
        existing_facts = cursor.fetchall() or []
        existing_facts_list = [f"{f.get('title')}: {f.get('content', '')}" for f in existing_facts]
        existing_titles = {f.get("title", "").lower() for f in existing_facts}

        cursor.close()
        conn.close()

        # Build dynamic suggested facts if there are queries
        suggested_facts = []
        if unresolved_queries or user_queries:
            # Generate synthesized suggestions based on recent inquiries with strict deduplication
            suggested_facts = synthesize_facts_from_queries(
                user_queries[:25], 
                unresolved_queries[:10], 
                existing_facts_list,
                existing_titles
            )

        return {
            "total_conversations": total_convs,
            "total_messages": total_msgs,
            "positive_ratings": pos_count,
            "negative_ratings": neg_count,
            "satisfaction_rate": satisfaction_rate,
            "top_inquiries": top_inquiries,
            "unresolved_queries": list(set(unresolved_queries))[:10],
            "suggested_facts": suggested_facts,
        }
    except Exception as e:
        logger.error(f"Error getting AI learning insights: {e}")
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return {
            "total_conversations": 0,
            "total_messages": 0,
            "positive_ratings": 0,
            "negative_ratings": 0,
            "satisfaction_rate": 100,
            "top_inquiries": [],
            "unresolved_queries": [],
            "suggested_facts": [],
        }


def synthesize_facts_from_queries(
    all_queries: List[str], 
    unresolved_queries: List[str], 
    existing_facts_list: List[str],
    existing_titles: set
) -> List[Dict[str, Any]]:
    """Uses Groq / LLM to dynamically synthesize proposed facts only for truly unaddressed knowledge gaps."""
    if not all_queries:
        return []

    # Prepare unique questions from real user logs
    unique_queries = list(dict.fromkeys([q.strip() for q in all_queries if len(q.strip()) > 4]))[:25]
    if not unique_queries:
        return []

    queries_text = "\n".join([f"- {q}" for q in unique_queries])
    existing_text = "\n".join([f"- {f}" for f in existing_facts_list[:30]]) if existing_facts_list else "(Hiện chưa có fact nào trong bộ nhớ)"

    # 1. Try Groq AI dynamic synthesis
    try:
        from groq import Groq
        if settings.GROQ_API_KEY:
            client = Groq(api_key=settings.GROQ_API_KEY)
            prompt = f"""Bạn là AI phân tích dữ liệu Portfolio của kỹ sư Nguyễn Quốc Khoa.

=== DANH SÁCH THÔNG TIN & FACT ĐÃ CÓ TRONG KHO (ĐÃ BIẾT): ===
{existing_text}

=== DANH SÁCH CÂU HỎI THỰC TẾ GẦN ĐÂY CỦA KHÁCH TRUY CẬP: ===
{queries_text}

Nhiệm vụ: Phân tích các câu hỏi và CHỈ ĐỀ XUẤT NHỮNG FACT MỚI mà trong kho dữ liệu trên CHƯA CÓ HOẶC CÒN THIẾU THÔNG TIN ĐỂ TRẢ LỜI.

Quy tắc BẮT BUỘC (RẤT QUAN TRỌNG):
1. TUYỆT ĐỐI KHÔNG đề xuất lại những thông tin ĐÃ CÓ SẴN hoặc TRÙNG LẶP NGỮ NGHĨA với kho dữ liệu trên (Ví dụ: nếu đã có biệt danh/tên ở nhà, sở thích, thông tin liên hệ hay kỹ năng đã có thì KHÔNG đề xuất lại).
2. Nếu các câu hỏi của khách ĐÃ ĐƯỢC GIẢI ĐÁP ĐẦY ĐỦ bởi các Fact đã biết, BẮT BUỘC trả về mảng rỗng `[]`.
3. Nếu có khoảng trống tri thức thật sự (câu hỏi mà kho dữ liệu hoàn toàn chưa có), trả về JSON array chứa 1 đến 3 Fact mới:
[
  {{
    "category": "Thông tin cá nhân | Dịch vụ & Hợp tác | Kỹ năng & Kinh nghiệm",
    "title": "Tiêu đề Fact ngắn gọn",
    "content": "Nội dung chi tiết giải thích cho câu hỏi đó",
    "reason": "Khách hàng đã hỏi: '...'"
  }}
]
Chỉ xuất JSON array hợp lệ."""
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a specialized JSON data analyzer. Always output valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                model=settings.GROQ_MODEL,
                temperature=0.2,
                max_tokens=2000,
            )
            raw_content = chat_completion.choices[0].message.content.strip()
            # Strip reasoning/thinking tags emitted by reasoning models (e.g. gpt-oss-20b)
            clean_content = re.sub(r"<think>[\s\S]*?</think>", "", raw_content, flags=re.IGNORECASE).strip()
            json_match = re.search(r"\[[\s\S]*\]", clean_content)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, list):
                    filtered = [
                        item for item in parsed 
                        if item.get("title") and item.get("title").lower() not in existing_titles
                    ]
                    if filtered:
                        logger.info(f"🧠 [LLM Synthesizer] Successfully synthesized {len(filtered)} NEW facts from genuine knowledge gaps!")
                        return filtered[:4]
                    return []
    except Exception as e:
        logger.error(f"Groq dynamic fact synthesis error: {e}")

    # Fallback to Google Gemini LLM if configured
    try:
        import google.generativeai as genai
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            prompt = f"""Bạn là AI phân tích dữ liệu Portfolio của kỹ sư Nguyễn Quốc Khoa.
Dưới đây là các câu hỏi thực tế người dùng vừa hỏi AI:
{queries_text}

Hãy phân tích và tạo 2-3 Fact kiến thức JSON:
[
  {{
    "category": "Dịch vụ & Hợp tác",
    "title": "Tiêu đề Fact",
    "content": "Nội dung giải thích chi tiết",
    "reason": "Khách hàng đã hỏi: '...'"
  }}
]"""
            resp = model.generate_content(prompt)
            raw_text = resp.text.strip()
            json_match = re.search(r"\[[\s\S]*\]", raw_text)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, list):
                    return [
                        item for item in parsed 
                        if item.get("title") and item.get("title").lower() not in existing_titles
                    ][:4]
    except Exception as e:
        logger.error(f"Gemini dynamic fact synthesis error: {e}")

    return []


def adopt_suggested_fact(category: str, title: str, content: str) -> bool:
    """Directly saves a proposed fact into PostgreSQL 'ai_facts' table for instant chatbot memory ingestion."""
    if not title or not content:
        return False

    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_facts (category, title, content, is_active, display_order, created_at, updated_at)
            VALUES (%s, %s, %s, TRUE, 1, NOW(), NOW())
            RETURNING id;
        """, (category or "Thông tin bổ sung", title, content))
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"✨ [AI Memory] Successfully adopted new AI Fact #{new_id}: '{title}' into Neon DB!")
        return True
    except Exception as e:
        logger.error(f"Failed to adopt AI fact: {e}")
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return False
