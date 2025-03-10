"""
Модуль для управления диалогами пользователей с моделью.
Хранит историю сообщений и управляет контекстом разговора.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from config import MAX_HISTORY_LENGTH

# Настройка логирования
logger = logging.getLogger(__name__)

class Conversation:
    """
    Класс для представления разговора пользователя с моделью.
    Хранит историю сообщений и метаданные разговора.
    """
    
    def __init__(self, user_id: int):
        """
        Инициализация разговора.
        
        Args:
            user_id: ID пользователя в Telegram
        """
        self.user_id = user_id
        self.messages = []  # история сообщений в формате [{role: "", content: ""}]
        self.started_at = datetime.now()
        self.last_active = datetime.now()
        logger.info(f"Создан новый разговор для пользователя {user_id}")
    
    def add_user_message(self, content: str) -> None:
        """
        Добавляет сообщение пользователя в историю.
        
        Args:
            content: Текст сообщения пользователя
        """
        message = {
            "role": "user",
            "content": content
        }
        self._add_message(message)
    
    def add_assistant_message(self, content: str) -> None:
        """
        Добавляет ответ ассистента в историю.
        
        Args:
            content: Текст ответа ассистента
        """
        message = {
            "role": "assistant",
            "content": content
        }
        self._add_message(message)
    
    def _add_message(self, message: Dict[str, str]) -> None:
        """
        Добавляет сообщение в историю и обновляет время последней активности.
        Следит за ограничением на количество сообщений в истории.
        
        Args:
            message: Сообщение в формате {role: "", content: ""}
        """
        self.messages.append(message)
        self.last_active = datetime.now()
        
        # Ограничиваем длину истории
        if len(self.messages) > MAX_HISTORY_LENGTH:
            self.messages = self.messages[-MAX_HISTORY_LENGTH:]
            logger.info(f"История сообщений для пользователя {self.user_id} обрезана до {MAX_HISTORY_LENGTH}")
    
    def reset(self) -> None:
        """
        Сбрасывает историю диалога.
        """
        self.messages = []
        logger.info(f"История диалога для пользователя {self.user_id} сброшена")

class ConversationManager:
    """
    Управляет диалогами всех пользователей.
    """
    
    def __init__(self):
        """
        Инициализация менеджера диалогов.
        """
        self.conversations = {}  # user_id -> Conversation
        logger.info("Инициализирован менеджер диалогов")
    
    def get_conversation(self, user_id: int) -> Conversation:
        """
        Получает или создает разговор для пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Объект разговора
        """
        if user_id not in self.conversations:
            self.conversations[user_id] = Conversation(user_id)
        
        return self.conversations[user_id]
    
    def reset_conversation(self, user_id: int) -> None:
        """
        Сбрасывает разговор для пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
        """
        if user_id in self.conversations:
            self.conversations[user_id].reset()
        else:
            self.conversations[user_id] = Conversation(user_id)
            
        logger.info(f"Сброшен разговор для пользователя {user_id}")
    
    def get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает историю сообщений пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Список сообщений в формате [{role: "", content: ""}, ...]
        """
        conversation = self.get_conversation(user_id)
        return conversation.messages
    
    def add_user_message(self, user_id: int, content: str) -> None:
        """
        Добавляет сообщение пользователя в историю.
        
        Args:
            user_id: ID пользователя в Telegram
            content: Текст сообщения
        """
        conversation = self.get_conversation(user_id)
        conversation.add_user_message(content)
    
    def add_assistant_message(self, user_id: int, content: str) -> None:
        """
        Добавляет ответ ассистента в историю.
        
        Args:
            user_id: ID пользователя в Telegram
            content: Текст ответа
        """
        conversation = self.get_conversation(user_id)
        conversation.add_assistant_message(content) 