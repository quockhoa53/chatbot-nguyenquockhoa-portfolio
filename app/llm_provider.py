import logging
from typing import Dict, Generator, List, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

from app.config import settings
from app.prompt_builder import build_system_prompt
from app.security import is_sensitive_probe, sanitize_text

logger = logging.getLogger("llm_provider")
logging.basicConfig(level=logging.INFO)


class LLMProvider:
    """Core LLM Provider supporting Google Gemini and Groq with streaming."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.gemini_key = settings.GEMINI_API_KEY
        self.groq_key = settings.GROQ_API_KEY
        self.gemini_model_name = settings.GEMINI_MODEL
        self.groq_model_name = settings.GROQ_MODEL

        self.gemini_client: Optional[genai.GenerativeModel] = None
        self.groq_client: Optional[Groq] = None

        self._init_clients()

    def _init_clients(self):
        # 1. Initialize Google Gemini
        if self.gemini_key and genai is not None:
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini_client = genai.GenerativeModel(model_name=self.gemini_model_name)
                logger.info(f"Initialized Gemini model: {self.gemini_model_name}")
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")

        # 2. Initialize Groq
        if self.groq_key and Groq is not None:
            try:
                self.groq_client = Groq(api_key=self.groq_key)
                logger.info(f"Initialized Groq model: {self.groq_model_name}")
            except Exception as e:
                logger.error(f"Failed to configure Groq: {e}")

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        user_style_key: str = "trung_tinh",
    ) -> str:
        """Generates a complete response through the LLM prompt."""
        if not messages:
            return "Xin chào! Tôi là NQK AI Assistant. Tôi có thể hỗ trợ gì cho bạn về thông tin và năng lực của Nguyễn Quốc Khoa?"

        last_user_query = messages[-1].get("content", "")

        # 1. Build dynamic system prompt with context + user style instructions
        system_instruction = build_system_prompt(user_style_key)

        # 2. Try Gemini
        if (self.provider == "gemini" or not self.groq_client) and self.gemini_client:
            try:
                # Prepare history for Gemini
                formatted_history = []
                for m in messages[:-1]:
                    role = "user" if m.get("role") == "user" else "model"
                    formatted_history.append({"role": role, "parts": [m.get("content", "")]})

                model = genai.GenerativeModel(
                    model_name=self.gemini_model_name,
                    system_instruction=system_instruction,
                )
                chat = model.start_chat(history=formatted_history)
                res = chat.send_message(last_user_query)
                return sanitize_text(res.text)
            except Exception as e:
                logger.error(f"Gemini generation error: {e}")

        # 3. Try Groq with multi-model fallback
        if self.groq_client:
            models_to_try = list(dict.fromkeys([
                self.groq_model_name,
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "groq/compound-mini",
                "groq/compound",
            ]))
            groq_messages = [{"role": "system", "content": system_instruction}]
            for m in messages[:-1]:
                role = "user" if m.get("role") == "user" else "assistant"
                groq_messages.append({"role": role, "content": m.get("content", "")})
            groq_messages.append({"role": "user", "content": last_user_query})

            for model_name in models_to_try:
                try:
                    res = self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=groq_messages,
                        temperature=0.7,
                        max_tokens=1500,
                    )
                    return sanitize_text(res.choices[0].message.content)
                except Exception as e:
                    logger.warning(f"Groq model {model_name} failed: {e}. Trying fallback...")
                    continue

        # If no key configured, generate a polite guidance response explaining how to configure Gemini API Key
        return (
            "Xin chào! Tôi là **NQK AI Assistant**. "
            "Để kích hoạt toàn bộ trí tuệ nhân tạo tương tác theo phong cách riêng của bạn, "
            "vui lòng điền `GEMINI_API_KEY` (hoàn toàn miễn phí tại https://aistudio.google.com) "
            "vào file `.env` trong thư mục `PORTFOLIO_CHATBOT` nhé!"
        )

    def stream_response(
        self,
        messages: List[Dict[str, str]],
        user_style_key: str = "trung_tinh",
    ) -> Generator[str, None, None]:
        """Streams response tokens in real-time."""
        if not messages:
            yield "Xin chào! Tôi có thể giúp gì cho bạn?"
            return

        last_user_query = messages[-1].get("content", "")
        system_instruction = build_system_prompt(user_style_key)

        # 1. Stream with Gemini
        if (self.provider == "gemini" or not self.groq_client) and self.gemini_client:
            try:
                formatted_history = []
                for m in messages[:-1]:
                    role = "user" if m.get("role") == "user" else "model"
                    formatted_history.append({"role": role, "parts": [m.get("content", "")]})

                model = genai.GenerativeModel(
                    model_name=self.gemini_model_name,
                    system_instruction=system_instruction,
                )
                chat = model.start_chat(history=formatted_history)
                response = chat.send_message(last_user_query, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield sanitize_text(chunk.text)
                return
            except Exception as e:
                logger.error(f"Gemini streaming error: {e}")

        # 2. Stream with Groq
        if self.groq_client:
            models_to_try = list(dict.fromkeys([
                self.groq_model_name,
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "groq/compound-mini",
                "groq/compound",
            ]))
            groq_messages = [{"role": "system", "content": system_instruction}]
            for m in messages[:-1]:
                role = "user" if m.get("role") == "user" else "assistant"
                groq_messages.append({"role": role, "content": m.get("content", "")})
            groq_messages.append({"role": "user", "content": last_user_query})

            for model_name in models_to_try:
                try:
                    response = self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=groq_messages,
                        temperature=0.7,
                        max_tokens=1500,
                        stream=True,
                    )
                    for chunk in response:
                        delta = chunk.choices[0].delta.content
                        if delta:
                            yield sanitize_text(delta)
                    return
                except Exception as e:
                    logger.warning(f"Groq stream model {model_name} failed: {e}. Trying fallback...")
                    continue

        # Fallback text
        reply = self.generate_response(messages, user_style_key)
        import time
        for word in reply.split(" "):
            yield word + " "
            time.sleep(0.015)


# Global instance
llm_provider = LLMProvider()
