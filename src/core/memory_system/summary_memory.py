#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Реализация суммаризирующей памяти для системы памяти.

Суммаризирующая память хранит сжатое представление истории диалога,
используя модель для создания и обновления резюме разговора.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Callable

from src.core.memory_system.memory_base import MemoryBase, Message
from src.core.memory_system.buffer_memory import BufferMemory


class SummaryMemory(MemoryBase):
    """
    Суммаризирующая память для хранения сжатого представления истории диалога.
    
    Использует модель для создания и обновления резюме разговора на основе
    новых сообщений, что позволяет эффективно хранить длинные диалоги.
    """
    
    def __init__(
        self,
        memory_id: str,
        description: str = "Суммаризирующая память для хранения сжатого представления истории диалога",
        buffer_size: int = 10,
        summarize_threshold: int = 5,
        summarizer: Optional[Callable[[List[Message], Optional[str]], str]] = None,
        storage_path: Optional[str] = None
    ):
        """
        Инициализация суммаризирующей памяти.
        
        Args:
            memory_id: Уникальный идентификатор памяти
            description: Описание памяти
            buffer_size: Размер буфера для новых сообщений
            summarize_threshold: Порог количества сообщений для суммаризации
            summarizer: Функция для суммаризации сообщений
            storage_path: Путь для сохранения состояния памяти
        """
        super().__init__(memory_id, description)
        self.buffer = BufferMemory(f"{memory_id}_buffer", "Буфер для новых сообщений", buffer_size)
        self.summarize_threshold = summarize_threshold
        self.summarizer = summarizer
        self.storage_path = storage_path
        self.summary = ""
        
        # Создаем директорию для хранения, если она не существует
        if storage_path:
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        self.logger.info(f"Суммаризирующая память {memory_id} инициализирована с размером буфера {buffer_size}")
    
    def add_message(self, message: Message) -> None:
        """
        Добавляет сообщение в память и обновляет резюме при необходимости.
        
        Args:
            message: Сообщение для добавления
        """
        # Добавляем сообщение в буфер
        self.buffer.add_message(message)
        
        # Проверяем, нужно ли обновить резюме
        if len(self.buffer.get_messages()) >= self.summarize_threshold:
            self._update_summary()
        
        self.logger.debug(f"Добавлено сообщение в память {self.memory_id}: {message}")
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """
        Получает сообщения из буфера.
        
        Args:
            limit: Максимальное количество сообщений для получения
            
        Returns:
            List[Message]: Список сообщений из буфера
        """
        return self.buffer.get_messages(limit)
    
    def get_summary(self) -> str:
        """
        Получает текущее резюме диалога.
        
        Returns:
            str: Текущее резюме диалога
        """
        return self.summary
    
    def get_context(self) -> Dict[str, Any]:
        """
        Получает полный контекст диалога, включая резюме и последние сообщения.
        
        Returns:
            Dict[str, Any]: Контекст диалога
        """
        return {
            "summary": self.summary,
            "recent_messages": [message.to_dict() for message in self.buffer.get_messages()]
        }
    
    def _update_summary(self) -> None:
        """
        Обновляет резюме на основе новых сообщений в буфере.
        
        Raises:
            ValueError: Если summarizer не задан
        """
        if not self.summarizer:
            self.logger.warning("Summarizer не задан, резюме не будет обновлено")
            return
        
        messages = self.buffer.get_messages()
        
        # Обновляем резюме
        self.summary = self.summarizer(messages, self.summary)
        
        # Очищаем буфер после обновления резюме
        self.buffer.clear()
        
        self.logger.info(f"Резюме памяти {self.memory_id} обновлено")
    
    def clear(self) -> None:
        """Очищает память и резюме."""
        self.buffer.clear()
        self.summary = ""
        self.logger.info(f"Память {self.memory_id} очищена")
    
    def save(self) -> None:
        """
        Сохраняет состояние памяти в файл.
        
        Raises:
            ValueError: Если storage_path не задан
        """
        if not self.storage_path:
            raise ValueError("storage_path не задан для сохранения памяти")
        
        # Создаем директорию для хранения, если она не существует
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        # Сериализуем сообщения из буфера
        serialized_messages = [message.to_dict() for message in self.buffer.get_messages()]
        
        # Сохраняем в файл
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump({
                "memory_id": self.memory_id,
                "description": self.description,
                "summary": self.summary,
                "buffer_messages": serialized_messages,
                "summarize_threshold": self.summarize_threshold
            }, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Память {self.memory_id} сохранена в {self.storage_path}")
    
    def load(self) -> None:
        """
        Загружает состояние памяти из файла.
        
        Raises:
            ValueError: Если storage_path не задан
            FileNotFoundError: Если файл не найден
        """
        if not self.storage_path:
            raise ValueError("storage_path не задан для загрузки памяти")
        
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
        self.summary = data["summary"]
        self.summarize_threshold = data["summarize_threshold"]
        
        # Очищаем текущий буфер
        self.buffer.clear()
        
        # Десериализуем сообщения в буфер
        for message_data in data["buffer_messages"]:
            message = Message.from_dict(message_data)
            self.buffer.add_message(message)
        
        self.logger.info(f"Память {self.memory_id} загружена из {self.storage_path}")
    
    def get_info(self) -> Dict[str, Any]:
        """
        Получает информацию о суммаризирующей памяти.
        
        Returns:
            Dict[str, Any]: Информация о памяти
        """
        info = super().get_info()
        info.update({
            "buffer_size": self.buffer.max_messages,
            "current_buffer_messages": len(self.buffer.get_messages()),
            "summarize_threshold": self.summarize_threshold,
            "has_summary": bool(self.summary),
            "summary_length": len(self.summary) if self.summary else 0,
            "storage_path": self.storage_path
        })
        return info 