#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Реализация буферной памяти для системы памяти.

Буферная память хранит последние N сообщений в диалоге и предоставляет
доступ к ним для использования в контексте диалога.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import deque

from src.core.memory_system.memory_base import MemoryBase, Message


class BufferMemory(MemoryBase):
    """
    Буферная память для хранения последних N сообщений.
    
    Хранит фиксированное количество последних сообщений в диалоге
    и предоставляет доступ к ним для использования в контексте.
    """
    
    def __init__(
        self,
        memory_id: str,
        description: str = "Буферная память для хранения последних сообщений",
        max_messages: int = 50,
        storage_path: Optional[str] = None
    ):
        """
        Инициализация буферной памяти.
        
        Args:
            memory_id: Уникальный идентификатор памяти
            description: Описание памяти
            max_messages: Максимальное количество сообщений в буфере
            storage_path: Путь для сохранения состояния памяти
        """
        super().__init__(memory_id, description)
        self.max_messages = max_messages
        self.messages = deque(maxlen=max_messages)
        self.storage_path = storage_path
        
        # Создаем директорию для хранения, если она не существует
        if storage_path:
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        self.logger.info(f"Буферная память {memory_id} инициализирована с максимальным размером {max_messages}")
    
    def add_message(self, message: Message) -> None:
        """
        Добавляет сообщение в буфер.
        
        Args:
            message: Сообщение для добавления
        """
        self.messages.append(message)
        self.logger.debug(f"Добавлено сообщение в буфер {self.memory_id}: {message}")
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """
        Получает сообщения из буфера.
        
        Args:
            limit: Максимальное количество сообщений для получения
            
        Returns:
            List[Message]: Список сообщений
        """
        if limit is None or limit >= len(self.messages):
            return list(self.messages)
        return list(self.messages)[-limit:]
    
    def clear(self) -> None:
        """Очищает буфер сообщений."""
        self.messages.clear()
        self.logger.info(f"Буфер памяти {self.memory_id} очищен")
    
    def save(self) -> None:
        """
        Сохраняет состояние буфера в файл.
        
        Raises:
            ValueError: Если storage_path не задан
        """
        if not self.storage_path:
            raise ValueError("storage_path не задан для сохранения буфера")
        
        # Создаем директорию для хранения, если она не существует
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        # Сериализуем сообщения
        serialized_messages = [message.to_dict() for message in self.messages]
        
        # Сохраняем в файл
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump({
                "memory_id": self.memory_id,
                "description": self.description,
                "max_messages": self.max_messages,
                "messages": serialized_messages
            }, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Буфер памяти {self.memory_id} сохранен в {self.storage_path}")
    
    def load(self) -> None:
        """
        Загружает состояние буфера из файла.
        
        Raises:
            ValueError: Если storage_path не задан
            FileNotFoundError: Если файл не найден
        """
        if not self.storage_path:
            raise ValueError("storage_path не задан для загрузки буфера")
        
        if not os.path.exists(self.storage_path):
            raise FileNotFoundError(f"Файл {self.storage_path} не найден")
        
        # Загружаем из файла
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем идентификатор памяти
        if data["memory_id"] != self.memory_id:
            self.logger.warning(f"Загружаемый идентификатор памяти {data['memory_id']} не соответствует текущему {self.memory_id}")
        
        # Обновляем параметры
        self.description = data["description"]
        self.max_messages = data["max_messages"]
        
        # Очищаем текущий буфер
        self.messages.clear()
        
        # Десериализуем сообщения
        for message_data in data["messages"]:
            message = Message.from_dict(message_data)
            self.messages.append(message)
        
        self.logger.info(f"Буфер памяти {self.memory_id} загружен из {self.storage_path}, {len(self.messages)} сообщений")
    
    def get_info(self) -> Dict[str, Any]:
        """
        Получает информацию о буферной памяти.
        
        Returns:
            Dict[str, Any]: Информация о памяти
        """
        info = super().get_info()
        info.update({
            "max_messages": self.max_messages,
            "current_messages": len(self.messages),
            "storage_path": self.storage_path
        })
        return info 