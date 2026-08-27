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

        # 4. Fetch already adopted AI facts to prevent duplicate suggestions
        cursor.execute("SELECT title, category FROM ai_facts WHERE is_active = TRUE;")
        existing_facts = cursor.fetchall() or []
        existing_titles = {f.get("title", "").lower() for f in existing_facts}

        cursor.close()
        conn.close()

        # Build dynamic default suggested facts if there are queries
        suggested_facts = []
        if unresolved_queries or user_queries:
            # Generate synthesized suggestions based on recent inquiries
            suggested_facts = synthesize_facts_from_queries(user_queries[:20], unresolved_queries[:10], existing_titles)

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


def synthesize_facts_from_queries(all_queries: List[str], unresolved_queries: List[str], existing_titles: set) -> List[Dict[str, Any]]:
    """Uses Groq / LLM to dynamically synthesize high-value proposed facts from actual user queries."""
    if not all_queries:
        return []

    # Prepare unique questions from real user logs
    unique_queries = list(dict.fromkeys([q.strip() for q in all_queries if len(q.strip()) > 4]))[:20]
    if not unique_queries:
        return []

    queries_text = "\n".join([f"- {q}" for q in unique_queries])

    # 1. Try Groq AI dynamic synthesis
    try:
        from groq import Groq
        if settings.GROQ_API_KEY:
            client = Groq(api_key=settings.GROQ_API_KEY)
            prompt = f"""Bạn là AI phân tích dữ liệu Portfolio của kỹ sư Nguyễn Quốc Khoa.
Dưới đây là danh sách các câu hỏi THỰC TẾ mà khách truy cập vừa đặt cho AI Chatbot:
{queries_text}

Nhiệm vụ: Hãy phân tích các câu hỏi trên và đúc kết 2 đến 3 Fact kiến thức mới ĐƯỢC TẠO RA TRỰC TIẾP TỪ CÁC CÂU HỎI TRÊN để nạp vào Bộ nhớ AI.
Quy tắc:
- Trả về DUY NHẤT một JSON array hợp lệ (không kèm markdown ngoài JSON).
- Mỗi phần tử có 4 trường: "category", "title", "content", "reason".
- "reason" phải trích dẫn câu hỏi thực tế của người dùng đã dẫn đến đề xuất đó.

Ví dụ định dạng:
[
  {{
    "category": "Dịch vụ & Hợp tác",
    "title": "Tiêu đề Fact ngắn gọn",
    "content": "Nội dung chi tiết giải thích cho chủ đề",
    "reason": "Khách hàng đã hỏi: 'Câu hỏi cụ thể...'"
  }}
]"""
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia phân tích dữ liệu hội thoại. Luôn trả về định dạng JSON array hợp lệ."},
                    {"role": "user", "content": prompt}
                ],
                model=settings.GROQ_MODEL,
                temperature=0.3,
                max_tokens=600,
            )
            raw_content = chat_completion.choices[0].message.content.strip()
            json_match = re.search(r"\[[\s\S]*\]", raw_content)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, list):
                    filtered = [
                        item for item in parsed 
                        if item.get("title") and item.get("title").lower() not in existing_titles
                    ]
                    if filtered:
                        logger.info(f"🧠 [LLM Synthesizer] Successfully synthesized {len(filtered)} dynamic facts from real user queries!")
                        return filtered[:4]
    except Exception as e:
        logger.warning(f"Groq dynamic fact synthesis failed ({e}). Falling back to pattern-based extractor.")

    # 2. Dynamic pattern-based extractor as resilient fallback based on actual queries
    results = []
    for q in unique_queries:
        q_lower = q.lower()
        if any(w in q_lower for w in ["freelance", "thuê", "giá", "làm web", "dự án ngoài"]):
            title = "Khả năng nhận dự án Freelance & Báo giá phần mềm"
            if title.lower() not in existing_titles and not any(r["title"] == title for r in results):
                results.append({
                    "category": "Dịch vụ & Hợp tác",
                    "title": title,
                    "content": "Nguyễn Quốc Khoa sẵn sàng nhận các dự án phát triển phần mềm Freelance, thiết kế hệ thống web trọn gói và tư vấn kiến trúc AI/Microservices.",
                    "reason": f"Khách hàng đã hỏi: \"{q}\""
                })
        elif any(w in q_lower for w in ["ai", "claude", "chatgpt", "llm", "tài liệu"]):
            title = "Tài liệu và phương pháp làm việc hiệu quả với AI"
            if title.lower() not in existing_titles and not any(r["title"] == title for r in results):
                results.append({
                    "category": "Kinh nghiệm & Kỹ năng",
                    "title": title,
                    "content": "Khoa thường xuyên ứng dụng AI Agents, Prompt Engineering và Claude/GPT để tối ưu tốc độ lập trình và tự động hóa quy trình phần mềm.",
                    "reason": f"Khách hàng đã hỏi: \"{q}\""
                })
        elif any(w in q_lower for w in ["cà phê", "gặp mặt", "giao lưu", "hài hước"]):
            title = "Sở thích giao lưu cà phê & Kết nối công nghệ"
            if title.lower() not in existing_titles and not any(r["title"] == title for r in results):
                results.append({
                    "category": "Đời tư & Sở thích",
                    "title": title,
                    "content": "Khoa luôn cởi mở gặp gỡ, giao lưu cà phê chia sẻ về công nghệ, kiến trúc backend và khởi nghiệp tại khu vực TP.HCM.",
                    "reason": f"Khách hàng đã hỏi: \"{q}\""
                })

    return results[:3]


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
