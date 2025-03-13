#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Базовый интерфейс для системы памяти.

Определяет основные абстракции и интерфейсы для различных типов памяти,
используемых в мульти-агентной системе.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime


class Message:
    """
    Базовый класс для сообщений в системе памяти.
    
    Представляет собой абстракцию сообщения, которое может быть сохранено
    в системе памяти и использовано для контекста диалога.
    """
    
    def __init__(
        self,
        content: str,
        role: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализация сообщения.
        
        Args:
            content: Содержимое сообщения
            role: Роль отправителя (user, assistant, system)
            timestamp: Временная метка создания сообщения
            metadata: Дополнительные метаданные сообщения
        """
        self.content = content
        self.role = role
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует сообщение в словарь для сериализации.
        
        Returns:
            Dict[str, Any]: Словарь с данными сообщения
        """
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Создает сообщение из словаря.
        
        Args:
            data: Словарь с данными сообщения
            
        Returns:
            Message: Созданное сообщение
        """
        timestamp = datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"]
        return cls(
            content=data["content"],
            role=data["role"],
            timestamp=timestamp,
            metadata=data.get("metadata", {})
        )
    
    def __str__(self) -> str:
        """
        Строковое представление сообщения.
        
        Returns:
            str: Строковое представление
        """
        return f"{self.role}: {self.content}"


class UserMessage(Message):
    """Сообщение от пользователя."""
    
    def __init__(
        self,
        content: str,
        user_id: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализация сообщения пользователя.
        
        Args:
            content: Содержимое сообщения
            user_id: Идентификатор пользователя
            timestamp: Временная метка создания сообщения
            metadata: Дополнительные метаданные сообщения
        """
        super().__init__(content, "user", timestamp, metadata)
        self.user_id = user_id
        self.metadata["user_id"] = user_id


class AssistantMessage(Message):
    """Сообщение от ассистента (агента)."""
    
    def __init__(
        self,
        content: str,
        agent_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализация сообщения ассистента.
        
        Args:
            content: Содержимое сообщения
            agent_id: Идентификатор агента (если применимо)
            timestamp: Временная метка создания сообщения
            metadata: Дополнительные метаданные сообщения
        """
        super().__init__(content, "assistant", timestamp, metadata)
        if agent_id:
            self.agent_id = agent_id
            self.metadata["agent_id"] = agent_id


class SystemMessage(Message):
    """Системное сообщение."""
    
    def __init__(
        self,
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализация системного сообщения.
        
        Args:
            content: Содержимое сообщения
            timestamp: Временная метка создания сообщения
            metadata: Дополнительные метаданные сообщения
        """
        super().__init__(content, "system", timestamp, metadata)


class MemoryBase(ABC):
    """
    Абстрактный базовый класс для всех типов памяти.
    
    Определяет общий интерфейс для различных типов памяти,
    используемых в мульти-агентной системе.
    """
    
    def __init__(self, memory_id: str, description: str):
        """
        Инициализация базового класса памяти.
        
        Args:
            memory_id: Уникальный идентификатор памяти
            description: Описание памяти
        """
        self.memory_id = memory_id
        self.description = description
        self.logger = logging.getLogger(f"memory.{memory_id}")
    
    @abstractmethod
    def add_message(self, message: Message) -> None:
        """
        Добавляет сообщение в память.
        
        Args:
            message: Сообщение для добавления
        """
        pass
    
    @abstractmethod
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """
        Получает сообщения из памяти.
        
        Args:
            limit: Максимальное количество сообщений для получения
            
        Returns:
            List[Message]: Список сообщений
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Очищает память."""
        pass
    
    @abstractmethod
    def save(self) -> None:
        """Сохраняет состояние памяти."""
        pass
    
    @abstractmethod
    def load(self) -> None:
        """Загружает состояние памяти."""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Получает информацию о памяти.
        
        Returns:
            Dict[str, Any]: Информация о памяти
        """
        return {
            "memory_id": self.memory_id,
            "description": self.description,
            "type": self.__class__.__name__
        } 