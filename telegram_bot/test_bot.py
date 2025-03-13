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

@dataclass
class MockChat:
    id: int
    type: str = "private"

class MockUpdate:
    def __init__(self, message_text: str, chat_id: int = 12345):
        self.message = MockMessage(
            message_id=1,
            text=message_text,
            date=datetime.now(),
            chat_id=chat_id
        )
        self.effective_chat = MockChat(id=chat_id)
        
    @property
    def effective_message(self):
        return self.message

async def simulate_message(app: Application, message: str) -> None:
    """
    Симулирует получение сообщения ботом
    """
    logger.info(f"Симулируем сообщение: {message}")
    mock_update = MockUpdate(message)
    context = await app.context_types.context.create_context(mock_update, app)
    await app.process_update(mock_update, context)

async def main():
    """
    Основная функция для тестирования бота
    """
    app = None
    try:
        from telegram_bot.test_config import test_config
        from telegram_bot.telegram_bot import create_application
        
        # Создаем приложение с тестовой конфигурацией
        app = await create_application(test_config)
        
        # Запускаем бота
        await app.initialize()
        await app.start()
        
        # Тестовые сообщения
        test_messages = [
            "Привет!",
            "Как дела?",
            "Расскажи о себе",
            "Пока!"
        ]
        
        # Отправляем тестовые сообщения с паузами
        for message in test_messages:
            await simulate_message(app, message)
            await asyncio.sleep(2)  # Пауза между сообщениями
            
        # Даем время на обработку последнего сообщения
        await asyncio.sleep(5)
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {str(e)}", exc_info=True)
    finally:
        # Корректно завершаем работу
        if app:
            try:
                await app.stop()
                await app.shutdown()
            except Exception as e:
                logger.error(f"Ошибка при завершении работы: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 