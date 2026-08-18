import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

app = FastAPI(
    title="NQK Portfolio AI Chatbot API",
    description="Adaptive AI Assistant for Nguyen Quoc Khoa Portfolio with Style Detection",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "NQK Portfolio AI Chatbot with Adaptive Style Engine",
        "provider": settings.LLM_PROVIDER,
        "docs": "/docs",
    }


if __name__ == "__main__":
    print(f"🚀 Starting NQK Portfolio Chatbot on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
