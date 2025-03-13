"""
Тестовый скрипт для отладки Telegram бота
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import Application, ContextTypes
from dataclasses import dataclass
from datetime import datetime

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Создаем директорию для логов
os.makedirs('logs', exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MockMessage:
    message_id: int
    text: str
    date: datetime
    chat_id: int
    
    async def reply_text(self, text: str, reply_to_message_id: Optional[int] = None) -> 'MockMessage':
        logger.info(f"Ответ бота: {text}")
        return MockMessage(
            message_id=self.message_id + 1,
            text=text,
            date=datetime.now(),
            chat_id=self.chat_id
        )
    
    async def delete(self):
        logger.info(f"Удаление сообщения {self.message_id}")

    async def edit_text(self, text: str) -> 'MockMessage':
        logger.info(f"Редактирование сообщения {self.message_id}: {text}")
        return MockMessage(
            message_id=self.message_id,
            text=text,
            date=datetime.now(),
            chat_id=self.chat_id
        )

@dataclass
class MockChat:
    id: int
    type: str = "private"

class MockUpdate:
    """Мок объекта Update для тестирования обработчиков Telegram"""
    
    def __init__(self, message_text: str, chat_id: int = 12345):
        self.message = MockMessage(
            message_id=1,
            text=message_text,
            date=datetime.now(),
            chat_id=chat_id
        )
        self.chat = MockChat(id=chat_id)
        self.message_id = 1
    
    @property
    def effective_message(self):
        return self.message
    
    @property
    def effective_chat(self):
        return self.chat

async def simulate_message(app: Application, message: str) -> None:
    """
    Симулирует получение сообщения от пользователя
    """
    update = MockUpdate(message_text=message)
    context = ContextTypes.DEFAULT_TYPE(app)
    
    # Получаем обработчик сообщений из приложения
    from telegram_bot.telegram_bot import message_handler
    
    try:
        await message_handler(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")

async def test_bot_commands():
    """
    Тест обработки основных команд бота
    """
    from telegram_bot.config import config
    from telegram_bot.telegram_bot import create_application
    
    logger.info("Запуск тестирования команд бота")
    
    # Создаем приложение
    app = await create_application(config)
    
    # Тестируем команду /start
    update = MockUpdate(message_text="/start")
    context = ContextTypes.DEFAULT_TYPE(app)
    from telegram_bot.telegram_bot import start
    await start(update, context)
    
    # Тестируем команду /help
    update = MockUpdate(message_text="/help")
    from telegram_bot.telegram_bot import help_command
    await help_command(update, context)
    
    # Тестируем команду /reset
    update = MockUpdate(message_text="/reset")
    from telegram_bot.telegram_bot import reset
    await reset(update, context)
    
    logger.info("Завершение тестирования команд бота")

async def test_mistral_integration():
    """
    Тест интеграции с Mistral API
    """
    from telegram_bot.config import config
    from telegram_bot.telegram_bot import create_application
    from telegram_bot.mistral_client import MistralClient
    
    logger.info("Запуск тестирования интеграции с Mistral")
    
    # Создаем приложение
    app = await create_application(config)
    
    # Создаем клиента Mistral
    mistral_client = MistralClient(
        base_url=config.get("MISTRAL_API_URL"),
        timeout=config.get("REQUEST_TIMEOUT")
    )
    
    # Тестируем запрос к модели
    try:
        result = await mistral_client.chat_completion(
            messages=[{"role": "user", "content": "Привет, как дела?"}],
            model=config.get("MODEL_NAME"),
            max_tokens=100
        )
        logger.info(f"Ответ от Mistral API: {result}")
    except Exception as e:
        logger.error(f"Ошибка при обращении к Mistral API: {e}")
        
    logger.info("Завершение тестирования интеграции с Mistral")

async def test_message_handler():
    """
    Тест обработки сообщений пользователя
    """
    from telegram_bot.config import config
    from telegram_bot.telegram_bot import create_application
    
    logger.info("Запуск тестирования обработчика сообщений")
    
    # Создаем приложение
    app = await create_application(config)
    
    # Тестируем обработку обычного сообщения
    await simulate_message(app, "Привет, бот!")
    
    # Тестируем обработку длинного сообщения
    long_message = "А" * 1000
    await simulate_message(app, long_message)
    
    # Тестируем обработку специальных символов
    await simulate_message(app, "@#$%^&*()_+")
    
    logger.info("Завершение тестирования обработчика сообщений")

async def main():
    """
    Основная функция для запуска тестов
    """
    logger.info("Запуск тестирования бота")
    
    # Тестируем команды бота
    await test_bot_commands()
    
    # Тестируем интеграцию с Mistral
    await test_mistral_integration()
    
    # Тестируем обработчик сообщений
    await test_message_handler()
    
    logger.info("Тестирование завершено")

if __name__ == "__main__":
    # Запускаем тесты
    asyncio.run(main()) 