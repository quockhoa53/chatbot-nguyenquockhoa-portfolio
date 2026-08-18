@echo off
title NQK Portfolio AI Chatbot Service
echo ========================================================
echo   STARTING NQK PORTFOLIO AI CHATBOT (FastAPI + LLM)
echo ========================================================

cd /d "%~dp0"

if not exist venv (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Checking and installing dependencies...
pip install -r requirements.txt

echo [INFO] Starting FastAPI server on http://localhost:8000 ...
python main.py
pause
