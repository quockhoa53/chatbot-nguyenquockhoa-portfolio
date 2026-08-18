# 🤖 NQK Portfolio AI Chatbot Service

Hệ thống AI Chatbot độc lập hỗ trợ tư vấn và giải đáp thông tin về kỹ sư **Nguyễn Quốc Khoa** (Full-stack & AI Systems Engineer), được xây dựng bằng **Python (FastAPI)**, truy xuất dữ liệu an toàn từ **PostgreSQL** và tích hợp các mô hình **LLM Miễn Phí (Google Gemini 1.5 Flash / Groq LLaMA 3.3)** kèm **Luồng nhận diện phong cách hội thoại (Persona Classifier)** độc lập.

---

## 📁 Cấu Trúc Thư Mục (Clean Architecture)

```
PORTFOLIO_CHATBOT/
├── app/
│   ├── __init__.py
│   ├── config.py              # Quản lý cấu hình & biến môi trường tập trung
│   ├── database.py            # Truy vấn PostgreSQL an toàn (Whitelist tables & RAM Cache)
│   ├── security.py            # Guardrails phòng chống lộ mật khẩu & làm sạch dữ liệu
│   ├── memory.py              # Quản lý phiên hội thoại nhiều lượt (Session Manager)
│   ├── style_analyzer.py      # Luồng LLM độc lập phân loại phong cách người dùng
│   ├── prompt_builder.py      # Tổng hợp Database Context + Phong cách để tạo Dynamic Prompt
│   ├── llm_provider.py        # Module kết nối LLM (Gemini / Groq) hỗ trợ Streaming SSE
│   └── api/
│       ├── __init__.py
│       └── routes.py          # REST & Streaming SSE Endpoints (/api/chat, /api/chat/stream, ...)
├── main.py                    # Server Entry Point
├── requirements.txt           # Danh sách thư viện Python
├── .env.example               # File mẫu cấu hình biến môi trường
├── .gitignore                 # Bỏ qua venv, .env, cache
├── run.bat                    # Script khởi chạy 1 chạm cho Windows
└── README.md
```

---

## 🔒 Tính Năng Nổi Bật & Bảo Mật

1. **Không Gán Cứng Câu Trả Lời**: 100% câu trả lời được xử lý và suy luận từ LLM thông qua Dynamic Prompt sinh theo thời gian thực từ Database.
2. **Luồng Nhận Diện Phong Cách Độc Lập**: Toàn bộ Transcript đối thoại được gửi vào background worker cho LLM phân loại vào 7 nhóm chân dung (Nhà tuyển dụng, Tech Lead, Doanh nghiệp, Ngắn gọn, Học hỏi, Thân thiện, Thực tế).
3. **Bảo Mật Tuyệt Đối (Zero Secrets Leak)**: Bảng `admin_users` (mật khẩu/hash), `admin_allowed_ips` (IP quản trị), API keys, DB connection strings hoàn toàn bị cô lập và không bao giờ được nạp vào bộ nhớ Chatbot.

---

## 🚀 Hướng Dẫn Khởi Chạy

### 1. Cấu hình biến môi trường:
Copy file `.env.example` thành `.env`:
```bash
cp .env.example .env
```
Điền `GEMINI_API_KEY` (lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/app/apikey)) vào file `.env`.

### 2. Khởi chạy trên Windows:
Nhấp đúp vào file **`run.bat`** (hoặc chạy trong PowerShell: `.\run.bat`). Script sẽ tự động tạo Virtual Environment và cài đặt đầy đủ thư viện.

### 3. Khởi chạy thủ công bằng Terminal:
```bash
python -m venv venv
.\venv\Scripts\activate      # Trên Windows
# source venv/bin/activate   # Trên Linux/macOS

pip install -r requirements.txt
python main.py
```

* Service URL: **`http://localhost:8000`**
* Swagger UI Docs: **`http://localhost:8000/docs`**
