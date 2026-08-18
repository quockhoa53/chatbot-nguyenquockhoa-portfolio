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

# 7 Standardized Personas for Portfolio Chatbot
STYLE_PROMPT_DIRECTIVES: Dict[str, Tuple[str, str]] = {
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
        "Người dùng là Khách hàng hoặc Doanh nghiệp muốn tìm người triển khai dự án. Hãy tập trung vào giá trị thực tế của sản phẩm, tính ổn định, tối ưu chi phí/hiệu năng và hướng dẫn họ kết nối qua Email hoặc form Liên hệ trên website.",
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
        "Trả lời với phong cách chuyên nghiệp, thân thiện, súc tích và thể hiện rõ năng lực chuyên môn của Khoa.",
    ),
}

PERSONA_CLASSIFICATION_SYSTEM_PROMPT = """
Bạn là chuyên gia phân tích tâm lý, ngữ cảnh và phong cách giao tiếp người dùng trong hội thoại.
Nhiệm vụ của bạn: Đọc toàn bộ đoạn hội thoại được cung cấp và nhận diện chính xác phong cách / chân dung của Người dùng (User).

Danh sách 7 nhóm phong cách:
1. nha_tuyen_dung : Nhà tuyển dụng, HR, headhunter tìm kiếm ứng viên, hỏi về kinh nghiệm, CV, sự sẵn sàng làm việc, mức độ phù hợp JD.
2. chuyen_gia_ky_thuat : Tech Lead, kỹ sư phần mềm, kiến trúc sư hệ thống; hỏi sâu về kiến trúc, system design, concurrency, clean architecture, microservices, database trade-offs.
3. khach_hang_doanh_nghiep : Khách hàng, doanh nghiệp hoặc đối tác muốn thuê lập trình, xây dựng hệ thống, hỏi về chi phí, giải pháp sản phẩm, thời gian triển khai.
4. ngan_gon_xuc_tich : Người dùng bận rộn, thích đọc nhanh, hỏi ngắn hoặc yêu cầu tóm tắt gãy gọn, không thích rườm rà.
5. nguoi_hoc_hoi_chia_se : Người mới học lập trình, junior, sinh viên hỏi kinh nghiệm học tập, định hướng nghề nghiệp, tài liệu chuyên môn.
6. than_thien_giao_luu : Trò chuyện cởi mở, thân thiện, vui vẻ, chào hỏi tự nhiên, năng lượng tích cực.
7. thang_than_thuc_te : Thẳng thắn, đặt câu hỏi thực tế, muốn kiểm chứng năng lực và số liệu cụ thể.

Nếu đoạn chat quá ngắn hoặc chưa rõ xu hướng, chọn: trung_tinh

QUY TẮC ĐẦU RA:
- CHỈ trả về duy nhất 1 mã nhãn (ví dụ: nha_tuyen_dung).
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

    def classify_dialogue_with_llm(self, messages: List[Dict[str, str]]) -> str:
        """Sends the entire conversation dialogue to the LLM to classify user persona."""
        if not messages:
            return "trung_tinh"

        # Format full dialogue transcript
        transcript_lines = []
        for m in messages:
            speaker = "Người dùng (User)" if m.get("role") == "user" else "Trợ lý AI (Assistant)"
            transcript_lines.append(f"{speaker}: {m.get('content', '')}")
        
        dialogue_text = "\n".join(transcript_lines)
        analysis_prompt = (
            f"Dưới đây là toàn bộ đoạn hội thoại:\n"
            f"\"\"\"\n{dialogue_text}\n\"\"\"\n\n"
            f"Dựa trên toàn bộ hội thoại trên, hãy phân loại phong cách của Người dùng."
        )

        detected_label = "trung_tinh"

        # 1. Try Gemini classifier
        if self.gemini_model:
            try:
                response = self.gemini_model.generate_content(
                    analysis_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=30,
                    ),
                )
                raw_text = response.text.strip().lower()
                for key in STYLE_PROMPT_DIRECTIVES:
                    if key in raw_text:
                        detected_label = key
                        break
                return detected_label
            except Exception as e:
                logger.error(f"[StyleAnalyzer] Gemini classification error: {e}")

        # 2. Try Groq classifier
        if self.groq_client:
            try:
                res = self.groq_client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": PERSONA_CLASSIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": analysis_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=30,
                )
                raw_text = res.choices[0].message.content.strip().lower()
                for key in STYLE_PROMPT_DIRECTIVES:
                    if key in raw_text:
                        detected_label = key
                        break
                return detected_label
            except Exception as e:
                logger.error(f"[StyleAnalyzer] Groq classification error: {e}")

        return "trung_tinh"

    async def analyze_style_async(self, session_id: str, messages: List[Dict[str, str]]):
        """Asynchronous background worker feeding the entire dialogue into the LLM classifier."""
        try:
            if not messages:
                return

            # Run LLM classification in background thread pool without blocking event loop
            detected_key = await asyncio.to_thread(self.classify_dialogue_with_llm, messages)

            from app.memory import session_manager

            style_title, _ = STYLE_PROMPT_DIRECTIVES.get(
                detected_key, STYLE_PROMPT_DIRECTIVES["trung_tinh"]
            )
            session_manager.update_user_style(session_id, detected_key, style_title)
            logger.info(f"[StyleAnalyzer:LLM] Session {session_id} persona classified by LLM as: {detected_key} ({style_title})")

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
