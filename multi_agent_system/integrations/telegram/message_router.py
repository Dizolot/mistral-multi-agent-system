"""
Маршрутизатор сообщений для интеграции с Telegram.

Этот модуль анализирует входящие сообщения и определяет их тип
для дальнейшей маршрутизации.
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MessageRouter:
    """
    Маршрутизатор сообщений для интеграции с Telegram.
    
    Анализирует входящие сообщения и определяет их тип
    для дальнейшей маршрутизации.
    """
    
    def __init__(self):
        """Инициализирует маршрутизатор сообщений."""
        # Регулярные выражения для определения типов сообщений
        self.patterns = {
            "code": r"```[\s\S]*?```|`[\s\S]*?`",  # Код в маркдауне
            "question": r"\?\s*$",  # Вопрос (заканчивается на ?)
            "command": r"^/[a-zA-Z0-9_]+",  # Команда (начинается с /)
            "task": r"^(задача|task):",  # Задача
            "search": r"^(найди|поиск|search):",  # Поисковый запрос
        }
        
        # Компилируем регулярные выражения
        self.compiled_patterns = {
            key: re.compile(pattern, re.IGNORECASE)
            for key, pattern in self.patterns.items()
        }
        
        logger.info("MessageRouter инициализирован")
    
    async def initialize(self):
        """Инициализирует маршрутизатор."""
        logger.info("Инициализация MessageRouter...")
        return True
    
    def determine_message_type(self, text: str) -> str:
        """
        Определяет тип сообщения на основе его содержимого.
        
        Args:
            text: Текст сообщения
        
        Returns:
            str: Тип сообщения
        """
        if not text:
            return "direct"
        
        # Проверяем каждый паттерн
        if self.compiled_patterns["code"].search(text):
            return "code"
        
        if self.compiled_patterns["command"].search(text):
            return "command"
        
        if self.compiled_patterns["task"].search(text):
            return "task"
        
        if self.compiled_patterns["search"].search(text):
            return "search"
        
        if self.compiled_patterns["question"].search(text):
            return "question"
        
        # По умолчанию считаем, что это прямой запрос
        return "direct"
    
    def get_message_priority(self, message_type: str) -> int:
        """
        Возвращает приоритет сообщения на основе его типа.
        
        Args:
            message_type: Тип сообщения
        
        Returns:
            int: Приоритет сообщения (чем меньше, тем выше приоритет)
        """
        priorities = {
            "command": 1,
            "task": 2,
            "code": 3,
            "question": 4,
            "search": 5,
            "direct": 6
        }
        
        return priorities.get(message_type, 10)  # По умолчанию низкий приоритет 

    def route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Маршрутизирует сообщение на основе его типа и содержимого.
        
        Args:
            message: Словарь с данными сообщения (включая текст)
            
        Returns:
            Dict[str, Any]: Маршрутизированное сообщение с дополнительными метаданными
        """
        if not message or "text" not in message:
            logger.warning("Получено пустое сообщение или сообщение без текста")
            return message
            
        # Определяем тип сообщения
        message_text = message.get("text", "")
        message_type = self.determine_message_type(message_text)
        
        # Добавляем метаданные к сообщению
        routed_message = message.copy()
        routed_message["message_type"] = message_type
        routed_message["priority"] = self.get_message_priority(message_type)
        
        logger.info(f"Сообщение маршрутизировано с типом: {message_type}, приоритет: {routed_message['priority']}")
        
        return routed_message 