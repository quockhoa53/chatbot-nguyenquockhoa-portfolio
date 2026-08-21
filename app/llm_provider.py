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


def _format_gemini_history(messages: List[Dict[str, str]]) -> List[Dict[str, any]]:
    """
    Format chat history for Google Gemini GenerativeModel.start_chat().
    Rules strictly enforced by Gemini API:
    1. First turn in history MUST have role == 'user'.
    2. Roles MUST alternate between 'user' and 'model'.
    3. Content parts must not be empty.
    4. The last turn in history before chat.send_message() should be 'model'.
    """
    formatted: List[Dict[str, any]] = []
    for m in messages:
        role = "user" if m.get("role") == "user" else "model"
        content = (m.get("content") or "").strip()
        if not content:
            continue

        if formatted and formatted[-1]["role"] == role:
            # Merge consecutive messages with same role
            formatted[-1]["parts"][0] += "\n\n" + content
        else:
            formatted.append({"role": role, "parts": [content]})

    # Gemini requires the first turn in history to be from 'user'
    while formatted and formatted[0]["role"] == "model":
        formatted.pop(0)

    # Gemini requires the last turn in history (before new send_message) to be from 'model'
    while formatted and formatted[-1]["role"] == "user":
        formatted.pop()

    return formatted


def _filter_thinking_stream(generator: Generator[str, None, None]) -> Generator[str, None, None]:
    """
    Stateful streaming filter that suppresses all content enclosed within <think> and </think> tags.
    Emits clean final response tokens in real-time to the user.
    """
    in_think = False
    buffer = ""

    for chunk in generator:
        if not chunk:
            continue
        buffer += chunk

        while buffer:
            if not in_think:
                think_start = buffer.find("<think>")
                if think_start != -1:
                    # Emit clean text before <think>
                    before = buffer[:think_start]
                    if before:
                        yield before
                    buffer = buffer[think_start + len("<think>"):]
                    in_think = True
                else:
                    # Check if buffer ends with partial "<think"
                    partial = False
                    for i in range(1, len("<think>")):
                        if buffer.endswith("<think>"[:i]):
                            if len(buffer) > i:
                                yield buffer[:-i]
                                buffer = buffer[-i:]
                            partial = True
                            break
                    if not partial:
                        yield buffer
                        buffer = ""
                    break
            else:
                think_end = buffer.find("</think>")
                if think_end != -1:
                    # Thought block ended, discard thought text
                    buffer = buffer[think_end + len("</think>"):]
                    in_think = False
                else:
                    # Still inside <think>, check if buffer ends with partial "</think"
                    partial_len = 0
                    for i in range(1, len("</think>")):
                        if buffer.endswith("</think>"[:i]):
                            partial_len = i
                            break
                    buffer = buffer[-partial_len:] if partial_len > 0 else ""
                    break

    # If stream ends with unclosed thought or remaining clean text
    if buffer and not in_think:
        clean = re.sub(r"<think>[\s\S]*?</think>", "", buffer)
        clean = re.sub(r"<think>[\s\S]*$", "", clean)
        if clean:
            yield clean


class LLMProvider:
    """Core LLM Provider supporting Google Gemini and Groq with streaming."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.gemini_key = settings.GEMINI_API_KEY
        self.groq_key = settings.GROQ_API_KEY
        self.gemini_model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"
        self.groq_model_name = settings.GROQ_MODEL or "openai/gpt-oss-120b"

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

        # Keep last 6 messages to stay well within TPM token limits
        trimmed_messages = messages[-6:] if len(messages) > 6 else messages
        last_user_query = trimmed_messages[-1].get("content", "")
        system_instruction = build_system_prompt(user_style_key)

        # 1. Try Gemini models with fallback
        if self.gemini_key and genai is not None:
            gemini_models_to_try = list(dict.fromkeys([
                self.gemini_model_name,
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b",
                "gemini-1.5-pro",
            ]))
            formatted_history = _format_gemini_history(trimmed_messages[:-1])

            for g_model_name in gemini_models_to_try:
                try:
                    model = genai.GenerativeModel(
                        model_name=g_model_name,
                        system_instruction=system_instruction,
                    )
                    chat = model.start_chat(history=formatted_history)
                    res = chat.send_message(last_user_query)
                    if res and res.text:
                        return sanitize_text(res.text)
                except Exception as e:
                    logger.warning(f"Gemini model {g_model_name} failed: {e}. Trying fallback...")
                    continue

        # 2. Try Groq with multi-model fallback
        if self.groq_client:
            models_to_try = list(dict.fromkeys([
                self.groq_model_name,
                "openai/gpt-oss-120b",
                "qwen/qwen3.6-27b",
                "openai/gpt-oss-20b",
                "groq/compound-mini",
                "groq/compound",
            ]))
            groq_messages = [{"role": "system", "content": system_instruction}]
            for m in trimmed_messages[:-1]:
                role = "user" if m.get("role") == "user" else "assistant"
                content = (m.get("content") or "").strip()
                if content:
                    # Clean out any previous action tags or think tags from history
                    clean_m_content = re.sub(r"<think>[\s\S]*?</think>", "", content)
                    groq_messages.append({"role": role, "content": clean_m_content})
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

        # If completely unavailable, return a friendly server busy response
        return (
            "Dạ xin lỗi bạn! Hiện tại kết nối AI đang bị gián đoạn hoặc quá tải trong giây lát. 🙏\n\n"
            "Bạn vui lòng **thử gửi lại tin nhắn sau vài giây**, hoặc liên hệ trực tiếp với anh Khoa qua:\n"
            "• 📧 Email: **nguyenquockhoa5549@gmail.com**\n"
            "• 📱 Hotline / Zalo: **0969 895 549**\n"
            "• 📝 [Mở Form Liên Hệ Trực Tiếp](/contact)\n\n"
            "Rất cảm ơn sự thông cảm của bạn! ✨"
        )

    def _raw_stream_response(
        self,
        messages: List[Dict[str, str]],
        user_style_key: str = "trung_tinh",
    ) -> Generator[str, None, None]:
        """Internal generator pulling raw stream chunks from LLMs."""
        if not messages:
            yield "Xin chào! Tôi có thể giúp gì cho bạn?"
            return

        trimmed_messages = messages[-6:] if len(messages) > 6 else messages
        last_user_query = trimmed_messages[-1].get("content", "")
        system_instruction = build_system_prompt(user_style_key)

        # 1. Stream with Gemini models with fallback
        if self.gemini_key and genai is not None:
            gemini_models_to_try = list(dict.fromkeys([
                self.gemini_model_name,
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b",
                "gemini-1.5-pro",
            ]))
            formatted_history = _format_gemini_history(trimmed_messages[:-1])

            for g_model_name in gemini_models_to_try:
                try:
                    model = genai.GenerativeModel(
                        model_name=g_model_name,
                        system_instruction=system_instruction,
                    )
                    chat = model.start_chat(history=formatted_history)
                    response = chat.send_message(last_user_query, stream=True)
                    has_chunks = False
                    for chunk in response:
                        if chunk.text:
                            has_chunks = True
                            yield chunk.text
                    if has_chunks:
                        return
                except Exception as e:
                    logger.warning(f"Gemini stream model {g_model_name} failed: {e}. Trying fallback...")
                    continue

        # 2. Stream with Groq
        if self.groq_client:
            models_to_try = list(dict.fromkeys([
                self.groq_model_name,
                "openai/gpt-oss-120b",
                "qwen/qwen3.6-27b",
                "openai/gpt-oss-20b",
                "groq/compound-mini",
                "groq/compound",
            ]))
            groq_messages = [{"role": "system", "content": system_instruction}]
            for m in trimmed_messages[:-1]:
                role = "user" if m.get("role") == "user" else "assistant"
                content = (m.get("content") or "").strip()
                if content:
                    clean_m_content = re.sub(r"<think>[\s\S]*?</think>", "", content)
                    groq_messages.append({"role": role, "content": clean_m_content})
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
                            yield delta
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

    def stream_response(
        self,
        messages: List[Dict[str, str]],
        user_style_key: str = "trung_tinh",
    ) -> Generator[str, None, None]:
        """Streams response tokens with real-time thought-process filtering and security sanitization."""
        raw_stream = self._raw_stream_response(messages, user_style_key)
        for token in _filter_thinking_stream(raw_stream):
            yield sanitize_text(token)


# Global instance
llm_provider = LLMProvider()
