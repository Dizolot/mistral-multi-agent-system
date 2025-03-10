"""
Конфигурационный файл для Telegram-бота
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env-файла
load_dotenv()

# Токен Telegram-бота
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

if not TELEGRAM_TOKEN:
    raise ValueError("Токен Telegram-бота не установлен! Проверьте переменную окружения TELEGRAM_TOKEN.")

# ID администратора бота
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# URL для взаимодействия с Mistral API
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "http://localhost:8080")

# URL для взаимодействия с оркестратором
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_API_URL", "http://localhost:8002")

# Флаг использования оркестратора (если False, то используется прямой режим)
USE_ORCHESTRATOR = os.getenv("USE_ORCHESTRATOR", "True").lower() in ("true", "1", "yes")

# Параметры модели
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "mistral-7b-instruct")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "1000"))

# Параметры запросов
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "180"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "4096"))
MAX_HISTORY_LENGTH = int(os.getenv("MAX_HISTORY_LENGTH", "10"))  # Максимальное количество сообщений в истории диалога

# Текстовые сообщения
WELCOME_MESSAGE = """
👋 Привет! Я ассистент на базе модели Mistral.

Я могу отвечать на ваши вопросы и помогать с различными задачами.
Просто напишите мне сообщение, и я постараюсь помочь!

Для сброса диалога используйте команду /reset
Для получения помощи используйте команду /help
"""

HELP_MESSAGE = """
🔍 Справка по использованию бота:

1. Просто напишите мне сообщение с вопросом или задачей
2. Для сброса диалога используйте команду /reset
3. Для переключения режима работы используйте команду /mode

Поддерживаемые режимы:
- direct: прямое взаимодействие с моделью
- orchestrator: обработка через оркестратор (если доступен)

Пример переключения режима: /mode direct
"""

RESET_MESSAGE = "🔄 Диалог сброшен. Можете начать новый разговор."
PROCESSING_MESSAGE = "⌛ Инициализация обработки запроса... Сейчас покажу ход обработки."
ERROR_MESSAGE = "❌ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз."
TIMEOUT_MESSAGE = "⌛ Запрос занял слишком много времени. Пожалуйста, попробуйте еще раз или упростите запрос."

# Пути к файлам
LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", "logs")

# Создаем директорию для логов, если она не существует
os.makedirs(LOG_DIRECTORY, exist_ok=True) 