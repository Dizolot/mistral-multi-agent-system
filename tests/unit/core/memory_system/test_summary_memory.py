#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для суммаризирующей памяти.

Проверяет функциональность суммаризирующей памяти, включая добавление сообщений,
обновление резюме и получение контекста.
"""

import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime
from typing import List, Optional

from src.core.memory_system.memory_base import Message, UserMessage, AssistantMessage
from src.core.memory_system.summary_memory import SummaryMemory


def simple_summarizer(messages: List[Message], current_summary: Optional[str] = None) -> str:
    """Простой суммаризатор для тестирования."""
    summary_parts = []
    
    if current_summary:
        summary_parts.append(current_summary)
    
    summary_parts.append(f"Добавлено {len(messages)} новых сообщений.")
    
    for i, message in enumerate(messages):
        summary_parts.append(f"{i+1}. {message.role}: {message.content[:20]}...")
    
    return "\n".join(summary_parts)


class TestSummaryMemory:
    """Тесты для суммаризирующей памяти."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_summary_memory_initialization(self):
        """Тест инициализации суммаризирующей памяти."""
        memory_id = "test_summary"
        description = "Тестовая суммаризирующая память"
        buffer_size = 10
        summarize_threshold = 5
        
        memory = SummaryMemory(
            memory_id,
            description,
            buffer_size,
            summarize_threshold,
            summarizer=simple_summarizer
        )
        
        assert memory.memory_id == memory_id
        assert memory.description == description
        assert memory.buffer.max_messages == buffer_size
        assert memory.summarize_threshold == summarize_threshold
        assert memory.summary == ""
        assert len(memory.buffer.get_messages()) == 0
    
    def test_add_message_below_threshold(self):
        """Тест добавления сообщения ниже порога суммаризации."""
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=5,
            summarizer=simple_summarizer
        )
        
        # Добавляем сообщения ниже порога
        for i in range(3):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Проверяем, что сообщения добавлены в буфер
        assert len(memory.buffer.get_messages()) == 3
        
        # Проверяем, что резюме не обновлено
        assert memory.summary == ""
    
    def test_add_message_above_threshold(self):
        """Тест добавления сообщения выше порога суммаризации."""
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=3,
            summarizer=simple_summarizer
        )
        
        # Добавляем сообщения выше порога
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Проверяем, что буфер очищен после суммаризации
        assert len(memory.buffer.get_messages()) == 2  # 5 - 3 = 2 (последние два сообщения)
        
        # Проверяем, что резюме обновлено
        assert memory.summary != ""
        assert "Добавлено 3 новых сообщений" in memory.summary
    
    def test_get_messages(self):
        """Тест получения сообщений из буфера."""
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=5,
            summarizer=simple_summarizer
        )
        
        # Добавляем сообщения
        for i in range(3):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Получаем сообщения
        messages = memory.get_messages()
        
        assert len(messages) == 3
        assert messages[0].content == "Сообщение 0"
        assert messages[1].content == "Сообщение 1"
        assert messages[2].content == "Сообщение 2"
    
    def test_get_summary(self):
        """Тест получения резюме."""
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=3,
            summarizer=simple_summarizer
        )
        
        # Добавляем сообщения для создания резюме
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Получаем резюме
        summary = memory.get_summary()
        
        assert summary != ""
        assert "Добавлено 3 новых сообщений" in summary
    
    def test_get_context(self):
        """Тест получения контекста диалога."""
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=3,
            summarizer=simple_summarizer
        )
        
        # Добавляем сообщения для создания резюме и буфера
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Получаем контекст
        context = memory.get_context()
        
        assert "summary" in context
        assert "recent_messages" in context
        assert context["summary"] != ""
        assert len(context["recent_messages"]) == 2
    
    def test_clear(self):
        """Тест очистки памяти."""
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=3,
            summarizer=simple_summarizer
        )
        
        # Добавляем сообщения для создания резюме
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Проверяем, что резюме создано и буфер содержит сообщения
        assert memory.summary != ""
        assert len(memory.buffer.get_messages()) > 0
        
        # Очищаем память
        memory.clear()
        
        # Проверяем, что резюме и буфер очищены
        assert memory.summary == ""
        assert len(memory.buffer.get_messages()) == 0
    
    def test_save_and_load(self, temp_dir):
        """Тест сохранения и загрузки состояния памяти."""
        storage_path = os.path.join(temp_dir, "summary_test.json")
        
        # Создаем и заполняем память
        memory1 = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=3,
            summarizer=simple_summarizer,
            storage_path=storage_path
        )
        
        # Добавляем сообщения для создания резюме
        for i in range(5):
            memory1.add_message(Message(f"Сообщение {i}", "user"))
        
        # Сохраняем состояние
        memory1.save()
        
        # Проверяем, что файл создан
        assert os.path.exists(storage_path)
        
        # Создаем новую память и загружаем состояние
        memory2 = SummaryMemory(
            "test_summary",
            buffer_size=5,  # Другой размер буфера
            summarize_threshold=5,  # Другой порог
            summarizer=simple_summarizer,
            storage_path=storage_path
        )
        memory2.load()
        
        # Проверяем, что состояние загружено корректно
        assert memory2.summarize_threshold == 3  # Должно быть загружено из файла
        assert memory2.summary != ""
        assert "Добавлено 3 новых сообщений" in memory2.summary
        assert len(memory2.buffer.get_messages()) == 2
    
    def test_save_without_storage_path(self):
        """Тест сохранения без указания пути хранения."""
        memory = SummaryMemory("test_summary", summarizer=simple_summarizer)
        
        # Попытка сохранения без указания пути должна вызвать исключение
        with pytest.raises(ValueError):
            memory.save()
    
    def test_load_without_storage_path(self):
        """Тест загрузки без указания пути хранения."""
        memory = SummaryMemory("test_summary", summarizer=simple_summarizer)
        
        # Попытка загрузки без указания пути должна вызвать исключение
        with pytest.raises(ValueError):
            memory.load()
    
    def test_load_nonexistent_file(self, temp_dir):
        """Тест загрузки из несуществующего файла."""
        storage_path = os.path.join(temp_dir, "nonexistent.json")
        memory = SummaryMemory(
            "test_summary",
            summarizer=simple_summarizer,
            storage_path=storage_path
        )
        
        # Попытка загрузки из несуществующего файла должна вызвать исключение
        with pytest.raises(FileNotFoundError):
            memory.load()
    
    def test_without_summarizer(self):
        """Тест работы без суммаризатора."""
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=3
        )
        
        # Добавляем сообщения выше порога
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Проверяем, что буфер не очищен, так как суммаризатор не задан
        assert len(memory.buffer.get_messages()) == 5
        
        # Проверяем, что резюме не обновлено
        assert memory.summary == ""
    
    def test_get_info(self, temp_dir):
        """Тест получения информации о суммаризирующей памяти."""
        memory_id = "test_summary"
        description = "Тестовая суммаризирующая память"
        buffer_size = 10
        summarize_threshold = 5
        storage_path = os.path.join(temp_dir, "summary_info_test.json")
        
        memory = SummaryMemory(
            memory_id,
            description,
            buffer_size,
            summarize_threshold,
            summarizer=simple_summarizer,
            storage_path=storage_path
        )
        
        # Добавляем сообщения
        for i in range(3):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        info = memory.get_info()
        
        assert info["memory_id"] == memory_id
        assert info["description"] == description
        assert info["type"] == "SummaryMemory"
        assert info["buffer_size"] == buffer_size
        assert info["current_buffer_messages"] == 3
        assert info["summarize_threshold"] == summarize_threshold
        assert info["has_summary"] is False
        assert info["summary_length"] == 0
        assert info["storage_path"] == storage_path 