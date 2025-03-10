"""
Интеграция Telegram с оркестратором мульти-агентной системы.

Этот модуль содержит основной класс интеграции, который объединяет компоненты
адаптера Telegram, маршрутизатора сообщений и клиента оркестратора.
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable

from multi_agent_system.integrations.telegram.telegram_bot_adapter import TelegramBotAdapter
from multi_agent_system.integrations.telegram.message_router import MessageRouter
from multi_agent_system.integrations.telegram.orchestrator_client import OrchestratorClient

# Настройка логирования
logger = logging.getLogger("telegram_integration")

class TelegramIntegration:
    """
    Основной класс интеграции Telegram с оркестратором.
    
    Обеспечивает взаимодействие между компонентами:
    - TelegramBotAdapter: адаптер для Telegram API
    - MessageRouter: маршрутизатор сообщений
    - OrchestratorClient: клиент для взаимодействия с оркестратором
    """
    
    def __init__(
        self,
        adapter: Optional[TelegramBotAdapter] = None,
        router: Optional[MessageRouter] = None,
        client: Optional[OrchestratorClient] = None,
        direct_handler: Optional[Callable[[Dict[str, Any]], Awaitable[str]]] = None,
        api_url: str = "http://localhost:8000"
    ):
        """
        Инициализирует интеграцию с заданными компонентами.
        
        Args:
            adapter: Адаптер для Telegram API
            router: Маршрутизатор сообщений
            client: Клиент оркестратора
            direct_handler: Функция для прямой обработки сообщений
            api_url: URL API оркестратора
        """
        self.api_url = api_url
        
        # Инициализируем компоненты, если они не были переданы
        self.client = client or OrchestratorClient(api_url=api_url)
        self.router = router or MessageRouter()
        
        # Создаем адаптер, если он не был передан
        self.adapter = adapter or TelegramBotAdapter(
            orchestrator_client=self.client,
            message_router=self.router,
            direct_handler=direct_handler
        )
        
        # Флаг инициализации
        self._initialized = False
        
    async def initialize(self):
        """
        Инициализирует все компоненты интеграции.
        """
        if self._initialized:
            logger.info("Интеграция уже инициализирована")
            return
            
        logger.info("Инициализация интеграции Telegram с оркестратором")
        
        # Инициализация клиента оркестратора
        await self.client.initialize()
        
        # Инициализация маршрутизатора
        await self.router.initialize() if hasattr(self.router, 'initialize') else None
        
        # Инициализация адаптера
        await self.adapter.initialize() if hasattr(self.adapter, 'initialize') else None
            
        # Устанавливаем флаг инициализации
        self._initialized = True
        logger.info("Интеграция успешно инициализирована")
    
    async def process_message(self, user_id: str, message_text: str) -> str:
        """
        Обрабатывает сообщение от пользователя и возвращает ответ.
        
        Args:
            user_id: Идентификатор пользователя
            message_text: Текст сообщения
            
        Returns:
            str: Ответ от оркестратора
        """
        if not self._initialized:
            logger.warning("Интеграция не инициализирована. Выполняется автоматическая инициализация")
            await self.initialize()
            
        logger.info(f"Обработка сообщения от пользователя {user_id}")
        
        # Формируем данные сообщения
        message_data = {
            "user_id": user_id,
            "text": message_text,
            "type": "text"
        }
        
        # Обработка сообщения через адаптер
        response = await self.adapter.process_message(message_data)
        
        # Возвращаем текст ответа
        return response
    
    async def shutdown(self):
        """
        Закрывает все соединения и освобождает ресурсы.
        """
        logger.info("Завершение работы интеграции Telegram")
        
        # Закрываем компоненты
        if hasattr(self.adapter, 'shutdown'):
            await self.adapter.shutdown()
        
        # Закрываем клиент оркестратора
        await self.client.close()
        
        # Сбрасываем флаг инициализации
        self._initialized = False
        logger.info("Интеграция успешно завершена") 