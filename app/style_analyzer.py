import asyncio
import logging
from typing import Dict, List, Optional, Tuple

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

from app.config import settings

logger = logging.getLogger("style_analyzer")
logging.basicConfig(level=logging.INFO)

# 10 Standardized Personas for Portfolio Chatbot (Flexible Adaptive Communication)
STYLE_PROMPT_DIRECTIVES: Dict[str, Tuple[str, str]] = {
    "hai_huoc_troll": (
        "Hài hước & Dí dỏm (Meme & Cà khịa)",
        "Người dùng thích đùa giỡn, troll vui vẻ, dùng tiếng lóng mạng (slang), meme hoặc phong cách hài hước. Hãy trả lời cực kỳ duyên dáng, dí dỏm, có thể 'cà khịa' nhẹ nhàng, bắt trend hài hước, chủ động kèm theo các icon meme hài hước/cà khịa hợp cảnh (như 🤡, 🐸, 🐧, 🌚, 🤣, 🤪, ☕, 🗿, 💀), mang lại tiếng cười sảng khoái và vẫn giải quyết chuẩn xác trọng tâm câu hỏi.",
    ),
    "cuc_suc_thang_than": (
        "Cục súc & Bộc trực",
        "Người dùng ăn nói cộc lốc, gắt gỏng hoặc cục súc ('hỏi cái này coi', 'nhanh lên', 'gì vậy m'). Hãy trả lời với phong thái 'ngầu', ngắn gọn, thẳng thừng, bộc trực, không vòng vo hoa mỹ, 'nói ít hiểu nhiều', có thể chêm icon đanh thép / châm biếm nhẹ (🗿, 🐧, ☕, 😎) tương ứng với phong cách người dùng mà vẫn chuẩn xác thông tin.",
    ),
    "trang_trong_lich_su": (
        "Trang trọng & Lịch thiệp",
        "Người dùng xưng hô cung kính, trang trọng, lịch sự. Hãy dùng ngôi xưng kính ngữ (Quý khách, Bạn/Tôi), câu từ nhã nhặn, chỉn chu, biểu đạt sự trân trọng và tác phong chuẩn mực.",
    ),
    "nha_tuyen_dung": (
        "Nhà tuyển dụng / HR",
        "Người dùng là Nhà tuyển dụng hoặc HR đang tìm kiếm ứng viên. Hãy nhấn mạnh các thông tin trọng tâm: số năm kinh nghiệm, các thế mạnh công nghệ cốt lõi (Java/Spring Boot, PostgreSQL, Microservices, AI), tinh thần trách nhiệm, khả năng bắt đầu công việc và cung cấp nhanh phương thức liên hệ/CV.",
    ),
    "chuyen_gia_ky_thuat": (
        "Tech Lead / Kỹ sư chuyên sâu",
        "Người dùng là Kỹ sư phần mềm hoặc Tech Lead muốn trao đổi chuyên sâu. Hãy sử dụng ngôn ngữ kỹ thuật chuẩn xác (Clean Architecture, DDD, Microservices, Database indexing/caching, concurrency, event-driven), giải thích cụ thể về quyết định thiết kế và phân tích trade-off bài bản.",
    ),
    "khach_hang_doanh_nghiep": (
        "Khách hàng / Đối tác phát triển",
        "Người dùng là Khách hàng hoặc Doanh nghiệp muốn tìm người triểnkai dự án. Hãy tập trung vào giá trị thực tế của sản phẩm, tính ổn định, tối ưu chi phí/hiệu năng và hướng dẫn họ kết nối qua Email hoặc form Liên hệ trên website.",
    ),
    "ngan_gon_xuc_tich": (
        "Ngắn gọn & Súc tích",
        "Người dùng đang bận hoặc thích đọc nhanh. Hãy trả lời cực kỳ gãy gọn bằng 2-3 gạch đầu dòng ngắn, đi thẳng vào trọng tâm câu hỏi, loại bỏ toàn bộ lời rào đón rườm rà.",
    ),
    "nguoi_hoc_hoi_chia_se": (
        "Người học hỏi / Khám phá kiến thức",
        "Người dùng là người mới học lập trình hoặc muốn tìm cảm hứng. Hãy đối thoại với sự khích lệ, chia sẻ kinh nghiệm thực tế của Khoa và gợi ý tham khảo các bài viết trong mục Kho kiến thức.",
    ),
    "than_thien_giao_luu": (
        "Thân thiện & Cởi mở",
        "Người dùng muốn trò chuyện thoải mái và kết nối tự nhiên. Hãy trả lời với năng lượng tích cực, ấm áp, văn phong gần gũi và có thể sử dụng các emoji phù hợp (😊, ✨, 🚀).",
    ),
    "thang_than_thuc_te": (
        "Thẳng thắn & Thực tế",
        "Người dùng có câu hỏi trực diện hoặc muốn kiểm chứng năng lực. Hãy giữ thái độ tự tin, điềm tĩnh, dùng dẫn chứng cụ thể từ các dự án đã triển khai để trả lời thuyết phục.",
    ),
    "trung_tinh": (
        "Chuyên nghiệp & Tự nhiên",
        "Trả lời với phong cách chuyên nghiệp, thân thiện, linh hoạt, súc tích và thể hiện rõ năng lực chuyên môn của Khoa.",
    ),
}

PERSONA_CLASSIFICATION_SYSTEM_PROMPT = """
Bạn là chuyên gia phân tích tâm lý, ngữ cảnh và phong cách giao tiếp người dùng trong hội thoại.
Nhiệm vụ của bạn: Đọc toàn bộ đoạn hội thoại được cung cấp và nhận diện chính xác phong cách / chân dung của Người dùng (User).

Danh sách các nhóm phong cách:
1. hai_huoc_troll : Đùa giỡn, troll, hài hước, dùng meme, châm biếm, vui vẻ, xưng hô thân mật dân dã.
2. cuc_suc_thang_than : Ăn nói cộc lốc, gắt gỏng, cục súc, nói thẳng, thiếu kiên nhẫn, câu cú cộc cằn ('nhanh lên', 'gì m', 'hỏi coi').
3. trang_trong_lich_su : Trang trọng, lịch thiệp, xưng hô kính cẩn, lễ phép ('Kính gửi', 'Dạ thưa', 'Xin chào quý anh/chị').
4. nha_tuyen_dung : Nhà tuyển dụng, HR, headhunter tìm kiếm ứng viên, hỏi về kinh nghiệm, CV, sự sẵn sàng làm việc, mức độ phù hợp JD.
5. chuyen_gia_ky_thuat : Tech Lead, kỹ sư phần mềm, kiến trúc sư hệ thống; hỏi sâu về kiến trúc, system design, concurrency, clean architecture, microservices, database trade-offs.
6. khach_hang_doanh_nghiep : Khách hàng, doanh nghiệp hoặc đối tác muốn thuê lập trình, xây dựng hệ thống, hỏi về chi phí, giải pháp sản phẩm, thời gian triển khai.
7. ngan_gon_xuc_tich : Người dùng bận rộn, thích đọc nhanh, hỏi ngắn hoặc yêu cầu tóm tắt gãy gọn, không thích rườm rà.
8. nguoi_hoc_hoi_chia_se : Người mới học lập trình, junior, sinh viên hỏi kinh nghiệm học tập, định hướng nghề nghiệp, tài liệu chuyên môn.
9. than_thien_giao_luu : Trò chuyện cởi mở, thân thiện, vui vẻ, chào hỏi tự nhiên, năng lượng tích cực.
10. thang_than_thuc_te : Thẳng thắn, đặt câu hỏi thực tế, muốn kiểm chứng năng lực và số liệu cụ thể.

Nếu đoạn chat quá ngắn hoặc chưa rõ xu hướng, chọn: trung_tinh

QUY TẮC ĐẦU RA:
- CHỈ trả về duy nhất 1 mã nhãn (ví dụ: hai_huoc_troll hoặc cuc_suc_thang_than).
- KHÔNG thêm bất kỳ từ ngữ, dấu câu hay giải thích nào khác.
"""


class UserStyleAnalyzer:
    """Independent background analyzer running the full dialogue through an LLM classifier."""

    def __init__(self):
        self.gemini_model: Optional[genai.GenerativeModel] = None
        self.groq_client: Optional[Groq] = None
        self._init_llm_clients()

    def _init_llm_clients(self):
        if settings.GEMINI_API_KEY and genai is not None:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel(
                    model_name=settings.GEMINI_MODEL,
                    system_instruction=PERSONA_CLASSIFICATION_SYSTEM_PROMPT,
                )
                logger.info("[StyleAnalyzer] Initialized dedicated Gemini classifier model.")
            except Exception as e:
                logger.error(f"[StyleAnalyzer] Gemini init error: {e}")

        if settings.GROQ_API_KEY and Groq is not None:
            try:
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("[StyleAnalyzer] Initialized dedicated Groq classifier client.")
            except Exception as e:
                logger.error(f"[StyleAnalyzer] Groq init error: {e}")

    def classify_heuristics(self, text: str) -> Optional[str]:
        """Fast regex-based heuristic classifier taking 0ms and consuming 0 API quota."""
        t = text.lower()
        if any(w in t for w in ["haha", "hehe", "kiki", "troll", "cà khịa", "chúa hề", "hài vãi", "mlem", "gke dza", "ảo thật", "đùa"]):
            return "hai_huoc_troll"
        if any(w in t for w in ["nhanh lên", "nói lẹ", "lẹ coi", "lẹ đi", "gì m", "m là ai", "hỏi coi", "mệt quá", "bực"]):
            return "cuc_suc_thang_than"
        if any(w in t for w in ["kính gửi", "kính chào", "dạ thưa", "quý anh", "quý chị", "quý công ty", "trân trọng cảm ơn"]):
            return "trang_trong_lich_su"
        if any(w in t for w in ["tuyển dụng", "phỏng vấn", "hr", "recruiter", "headhunt", "offer", "ứng tuyển", "tìm ứng viên"]):
            return "nha_tuyen_dung"
        if any(w in t for w in ["báo giá", "chi phí", "thuê làm", "hợp đồng", "dự án e-commerce", "triển khai web", "hợp tác dự án", "cần làm web"]):
            return "khach_hang_doanh_nghiep"
        if any(w in t for w in ["clean architecture", "microservices", "kafka", "redis", "concurrency", "indexing", "thread pool", "acid", "sharding", "trade-off", "system design"]):
            return "chuyen_gia_ky_thuat"
        if any(w in t for w in ["ngắn gọn", "vắn tắt", "tóm tắt nhanh", "bullet point"]):
            return "ngan_gon_xuc_tich"
        if any(w in t for w in ["học lập trình", "lộ trình", "chia sẻ kinh nghiệm", "tài liệu học", "lời khuyên"]):
            return "nguoi_hoc_hoi_chia_se"
        return None

    def classify_dialogue_with_llm(self, messages: List[Dict[str, str]]) -> str:
        """Sends dialogue to LLM only when heuristics cannot determine persona."""
        if not messages:
            return "trung_tinh"

        # Check heuristics on last 2 user messages first
        for m in reversed(messages):
            if m.get("role") == "user":
                h_style = self.classify_heuristics(m.get("content", ""))
                if h_style:
                    return h_style

        # Format concise dialogue transcript for LLM
        transcript_lines = []
        for m in messages[-4:]:
            speaker = "User" if m.get("role") == "user" else "AI"
            transcript_lines.append(f"{speaker}: {m.get('content', '')[:100]}")
        
        dialogue_text = "\n".join(transcript_lines)
        analysis_prompt = (
            f"Hội thoại:\n\"\"\"\n{dialogue_text}\n\"\"\"\n"
            f"Phân loại phong cách User (trả về đúng 1 nhãn):"
        )

        detected_label = "trung_tinh"

        # 1. Try Gemini classifier
        if self.gemini_model:
            try:
                response = self.gemini_model.generate_content(
                    analysis_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=20,
                    ),
                )
                raw_text = response.text.strip().lower()
                for key in STYLE_PROMPT_DIRECTIVES:
                    if key in raw_text:
                        return key
            except Exception as e:
                logger.warning(f"[StyleAnalyzer] Gemini classification error: {e}")

        # 2. Try Groq classifier with zero retries to avoid wasting rate limits
        if self.groq_client:
            for model_candidate in ["openai/gpt-oss-20b", "groq/compound-mini", "openai/gpt-oss-120b"]:
                try:
                    res = self.groq_client.chat.completions.create(
                        model=model_candidate,
                        messages=[
                            {"role": "system", "content": PERSONA_CLASSIFICATION_SYSTEM_PROMPT},
                            {"role": "user", "content": analysis_prompt},
                        ],
                        temperature=0.1,
                        max_tokens=20,
                    )
                    raw_text = res.choices[0].message.content.strip().lower()
                    for key in STYLE_PROMPT_DIRECTIVES:
                        if key in raw_text:
                            return key
                except Exception as e:
                    logger.warning(f"[StyleAnalyzer] Groq classifier model {model_candidate} failed: {e}")
                    continue

        return "trung_tinh"

    async def analyze_style_async(self, session_id: str, messages: List[Dict[str, str]]):
        """Asynchronous background worker with smart throttling to protect LLM rate limits."""
        try:
            if not messages or len(messages) > 6:
                # Already past early phase, no need to re-classify repeatedly
                return

            from app.memory import session_manager
            session = session_manager.get_or_create_session(session_id)
            if session.user_style and session.user_style != "trung_tinh":
                # Already has specific persona identified, keep it
                return

            # Check heuristics directly first (instant, 0 API quota consumed)
            last_content = messages[-1].get("content", "") if messages else ""
            fast_style = self.classify_heuristics(last_content)
            if fast_style:
                style_title, _ = STYLE_PROMPT_DIRECTIVES.get(fast_style, STYLE_PROMPT_DIRECTIVES["trung_tinh"])
                session_manager.update_user_style(session_id, fast_style, style_title)
                logger.info(f"[StyleAnalyzer:FastHeuristic] Session {session_id} persona: {fast_style} ({style_title})")
                return

            # Only call LLM on turn 2 to save rate limit quota
            if len(messages) >= 2 and len(messages) <= 4:
                detected_key = await asyncio.to_thread(self.classify_dialogue_with_llm, messages)
                style_title, _ = STYLE_PROMPT_DIRECTIVES.get(detected_key, STYLE_PROMPT_DIRECTIVES["trung_tinh"])
                session_manager.update_user_style(session_id, detected_key, style_title)
                logger.info(f"[StyleAnalyzer:LLM] Session {session_id} persona: {detected_key} ({style_title})")

        except Exception as e:
            logger.error(f"Error in LLM style analyzer async worker: {e}")

    def get_style_directive(self, style_key: str) -> str:
        """Returns the prompt instruction corresponding to the detected style."""
        _, directive = STYLE_PROMPT_DIRECTIVES.get(
            style_key, STYLE_PROMPT_DIRECTIVES["trung_tinh"]
        )
        return directive


# Global instance
style_analyzer = UserStyleAnalyzer()
