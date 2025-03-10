"""
Адаптер для интеграции Telegram-бота с оркестратором.

Этот модуль обеспечивает связь между Telegram-ботом и оркестратором,
позволяя обрабатывать сообщения через оркестратор или напрямую.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

class TelegramBotAdapter:
    """
    Адаптер для интеграции Telegram-бота с оркестратором.
    
    Обеспечивает связь между Telegram-ботом и оркестратором,
    а также предоставляет возможность прямой обработки сообщений.
    """
    
    def __init__(
        self,
        orchestrator_client=None,
        message_router=None,
        direct_handler: Optional[Callable[[Dict[str, Any]], Awaitable[str]]] = None
    ):
        """
        Инициализирует адаптер.
        
        Args:
            orchestrator_client: Клиент для взаимодействия с оркестратором
            message_router: Маршрутизатор сообщений
            direct_handler: Функция для прямой обработки сообщений (без оркестратора)
        """
        self.orchestrator_client = orchestrator_client
        self.message_router = message_router
        self.direct_handler = direct_handler
        
        logger.info("TelegramBotAdapter инициализирован")
    
    async def initialize(self):
        """Инициализирует адаптер."""
        logger.info("Инициализация TelegramBotAdapter...")
        return True
    
    async def process_message(self, message: Dict[str, Any]) -> str:
        """
        Обрабатывает сообщение от пользователя.
        
        Args:
            message: Информация о сообщении от пользователя
        
        Returns:
            str: Ответ для пользователя
        """
        try:
            user_id = message.get("user_id", "unknown")
            text = message.get("text", "")
            session_id = message.get("session_id", "default")
            
            logger.info(f"Обработка сообщения от пользователя {user_id}: {text[:50]}...")
            
            # Определяем тип сообщения
            message_type = self.message_router.determine_message_type(text)
            
            if message_type == "direct":
                # Если это прямой запрос и есть обработчик, используем его
                if self.direct_handler:
                    logger.info(f"Обработка прямого запроса от пользователя {user_id}")
                    return await self.direct_handler(message)
            
            # В остальных случаях отправляем запрос оркестратору
            logger.info(f"Отправка запроса оркестратору для пользователя {user_id}")
            
            # Подготавливаем сообщение для оркестратора
            orchestrator_message = {
                "user_id": user_id,
                "text": text,
                "type": message_type,
                "session_id": session_id
            }
            
            # Отправляем запрос оркестратору
            response = await self.orchestrator_client.send_message(orchestrator_message)
            
            if response:
                content = response.get("content", "")
                logger.info(f"Получен ответ от оркестратора для пользователя {user_id}")
                return content
            else:
                logger.error(f"Пустой ответ от оркестратора для пользователя {user_id}")
                return "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз."
        
        except Exception as e:
            logger.exception(f"Ошибка при обработке сообщения: {e}")
            return f"Произошла ошибка при обработке запроса: {str(e)}"
    
    async def shutdown(self):
        """Завершает работу адаптера."""
        logger.info("Завершение работы TelegramBotAdapter...")
        # Здесь можно добавить логику завершения работы, если необходимо 