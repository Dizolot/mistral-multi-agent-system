"""
Мок-сервер Mistral API для тестирования.

Этот модуль имитирует работу Mistral API для тестирования интеграции.
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger

# Настройка логирования
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
)
logger.add(
    "logs/mistral_api_mock.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

# Создание директории для логов, если она не существует
os.makedirs("logs", exist_ok=True)

# Создаем приложение FastAPI
app = FastAPI(
    title="Mistral API Mock",
    description="Mock server for Mistral API testing",
    version="0.1.0"
)

# Добавляем middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Выполняется при запуске сервера"""
    logger.info("Мок-сервер Mistral API запущен")

@app.on_event("shutdown")
async def shutdown_event():
    """Выполняется при остановке сервера"""
    logger.info("Мок-сервер Mistral API остановлен")

@app.get("/health")
async def health_check():
    """Эндпоинт для проверки здоровья API-сервера"""
    return {"status": "ok"}

@app.post("/completion")
async def generate_completion(request: Request):
    """Эндпоинт для генерации текста"""
    data = await request.json()
    
    prompt = data.get("prompt", "")
    logger.info(f"Получен запрос на генерацию текста: {prompt[:50]}...")
    
    # Имитируем ответ модели
    response_text = f"Это ответ от мок-сервера Mistral API на запрос: {prompt[:50]}..."
    
    return {
        "content": response_text,
        "stop_reason": "stop",
        "model": "mistral-7b-mock"
    }

@app.post("/v1/chat/completions")
async def generate_chat_completion(request: Request):
    """Эндпоинт для генерации ответа в чате"""
    data = await request.json()
    
    messages = data.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Сообщения не предоставлены")
    
    last_message = messages[-1].get("content", "")
    logger.info(f"Получен запрос на генерацию ответа в чате: {last_message[:50]}...")
    
    # Имитируем ответ модели
    response_text = f"Это ответ от мок-сервера Mistral API на сообщение: {last_message[:50]}..."
    
    return {
        "id": "mock-response-id",
        "object": "chat.completion",
        "created": 1677858242,
        "model": "mistral-7b-mock",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop",
                "index": 0
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }

def run_server():
    """Запускает мок-сервер Mistral API"""
    try:
        uvicorn.run(
            "multi_agent_system.mistral_api_mock:app",
            host="0.0.0.0",
            port=8001,
            reload=True
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске мок-сервера Mistral API: {e}")

if __name__ == "__main__":
    run_server() 