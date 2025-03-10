"""
Файл с конфигурационными параметрами для Telegram-бота и Mistral API.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация Telegram бота
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не указан в переменных окружения")

# ID администратора (опционально)
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Конфигурация Mistral API
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "http://localhost:8001")

# Параметры запросов к модели
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "mistral-7b-instruct-v0.3")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "1000"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))  # в секундах
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))  # в секундах

# Ограничения
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "4000"))
MAX_HISTORY_LENGTH = int(os.getenv("MAX_HISTORY_LENGTH", "10"))  # количество сообщений в истории

# Пути к файлам
LOG_DIR = os.getenv("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Шаблоны сообщений
WELCOME_MESSAGE = """
Привет! Я бот, который позволяет общаться с языковой моделью Mistral.
Просто отправь мне сообщение, и я передам его модели для генерации ответа.

Команды:
/start - Начать диалог
/help - Показать справку
/reset - Сбросить историю диалога
"""

HELP_MESSAGE = """
Я использую модель Mistral для генерации ответов на ваши сообщения.

Доступные команды:
/start - Начать диалог
/help - Показать эту справку
/reset - Сбросить историю диалога

Просто напишите сообщение, и я отвечу на него!
"""

RESET_MESSAGE = "История диалога сброшена. Можете начать новый разговор!"

PROCESSING_MESSAGE = "Обрабатываю ваш запрос. Это может занять некоторое время..."

ERROR_MESSAGE = "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз."

TIMEOUT_MESSAGE = "Превышено время ожидания ответа. Пожалуйста, попробуйте еще раз или сократите запрос." 