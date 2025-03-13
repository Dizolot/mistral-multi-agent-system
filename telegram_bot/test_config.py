"""
Тестовая конфигурация для отладки бота
"""

import os
from dataclasses import dataclass

# Константы для тестового окружения
WELCOME_MESSAGE = "Привет! Я тестовый бот."
HELP_MESSAGE = "Это тестовый режим бота."
RESET_MESSAGE = "История диалога сброшена."
PROCESSING_MESSAGE = "Обрабатываю запрос..."
ERROR_MESSAGE = "Произошла ошибка."
TIMEOUT_MESSAGE = "Превышено время ожидания."
MAX_MESSAGE_LENGTH = 4096
MAX_HISTORY_LENGTH = 10

@dataclass
class TestConfig:
    # Telegram
    TELEGRAM_BOT_TOKEN: str = "test_token"
    
    # Mistral
    MISTRAL_API_BASE_URL: str = "http://localhost:11434/api/generate"
    MISTRAL_API_TIMEOUT: int = 180
    
    # Orchestrator
    ORCHESTRATOR_API_BASE_URL: str = "http://localhost:8000"
    ORCHESTRATOR_API_TIMEOUT: int = 30
    
    # Logging
    LOG_DIRECTORY: str = "logs"
    
    def __post_init__(self):
        os.makedirs(self.LOG_DIRECTORY, exist_ok=True)

test_config = TestConfig() 