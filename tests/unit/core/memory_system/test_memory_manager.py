#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для менеджера памяти.

Проверяет функциональность менеджера памяти, включая создание и получение
различных типов памяти, добавление сообщений и получение истории чата.
"""

import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime
from typing import List, Optional

from src.core.memory_system.memory_base import Message, UserMessage, AssistantMessage, SystemMessage
from src.core.memory_system.buffer_memory import BufferMemory
from src.core.memory_system.summary_memory import SummaryMemory
from src.core.memory_system.memory_manager import MemoryManager
from src.core.memory_system.summarizers import create_simple_summarizer


class TestMemoryManager:
    """Тесты для менеджера памяти."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_memory_manager_initialization(self, temp_dir):
        """Тест инициализации менеджера памяти."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        default_buffer_size = 20
        default_summarize_threshold = 10
        summarizer = create_simple_summarizer()
        
        manager = MemoryManager(
            storage_dir=storage_dir,
            default_buffer_size=default_buffer_size,
            default_summarize_threshold=default_summarize_threshold,
            summarizer=summarizer
        )
        
        assert manager.storage_dir == storage_dir
        assert manager.default_buffer_size == default_buffer_size
        assert manager.default_summarize_threshold == default_summarize_threshold
        assert manager.summarizer == summarizer
        assert os.path.exists(storage_dir)
        assert len(manager.buffer_memories) == 0
        assert len(manager.summary_memories) == 0
    
    def test_get_buffer_memory(self, temp_dir):
        """Тест получения буферной памяти."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        user_id = "test_user"
        
        # Получаем буферную память
        buffer_memory = manager.get_buffer_memory(user_id)
        
        # Проверяем, что память создана корректно
        assert buffer_memory.memory_id == f"buffer_{user_id}"
        assert buffer_memory.max_messages == manager.default_buffer_size
        assert buffer_memory.storage_path == os.path.join(storage_dir, f"{user_id}_buffer.json")
        
        # Проверяем, что память добавлена в словарь
        assert user_id in manager.buffer_memories
        assert manager.buffer_memories[user_id] == buffer_memory
        
        # Получаем память повторно и проверяем, что это тот же объект
        buffer_memory2 = manager.get_buffer_memory(user_id)
        assert buffer_memory2 is buffer_memory
    
    def test_get_summary_memory(self, temp_dir):
        """Тест получения суммаризирующей памяти."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        summarizer = create_simple_summarizer()
        manager = MemoryManager(storage_dir=storage_dir, summarizer=summarizer)
        
        user_id = "test_user"
        
        # Получаем суммаризирующую память
        summary_memory = manager.get_summary_memory(user_id)
        
        # Проверяем, что память создана корректно
        assert summary_memory.memory_id == f"summary_{user_id}"
        assert summary_memory.buffer.max_messages == manager.default_buffer_size
        assert summary_memory.summarize_threshold == manager.default_summarize_threshold
        assert summary_memory.storage_path == os.path.join(storage_dir, f"{user_id}_summary.json")
        
        # Проверяем, что память добавлена в словарь
        assert user_id in manager.summary_memories
        assert manager.summary_memories[user_id] == summary_memory
        
        # Получаем память повторно и проверяем, что это тот же объект
        summary_memory2 = manager.get_summary_memory(user_id)
        assert summary_memory2 is summary_memory
    
    def test_add_user_message(self, temp_dir):
        """Тест добавления сообщения пользователя."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        user_id = "test_user"
        content = "Тестовое сообщение пользователя"
        metadata = {"test_key": "test_value"}
        
        # Добавляем сообщение
        manager.add_user_message(user_id, content, metadata)
        
        # Проверяем, что сообщение добавлено в буферную память
        buffer_memory = manager.get_buffer_memory(user_id)
        buffer_messages = buffer_memory.get_messages()
        
        assert len(buffer_messages) == 1
        assert buffer_messages[0].content == content
        assert buffer_messages[0].role == "user"
        assert buffer_messages[0].user_id == user_id
        assert buffer_messages[0].metadata["test_key"] == "test_value"
        
        # Проверяем, что сообщение добавлено в суммаризирующую память
        summary_memory = manager.get_summary_memory(user_id)
        summary_messages = summary_memory.get_messages()
        
        assert len(summary_messages) == 1
        assert summary_messages[0].content == content
        assert summary_messages[0].role == "user"
    
    def test_add_assistant_message(self, temp_dir):
        """Тест добавления сообщения ассистента."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        user_id = "test_user"
        content = "Тестовое сообщение ассистента"
        agent_id = "test_agent"
        metadata = {"test_key": "test_value"}
        
        # Добавляем сообщение
        manager.add_assistant_message(user_id, content, agent_id, metadata)
        
        # Проверяем, что сообщение добавлено в буферную память
        buffer_memory = manager.get_buffer_memory(user_id)
        buffer_messages = buffer_memory.get_messages()
        
        assert len(buffer_messages) == 1
        assert buffer_messages[0].content == content
        assert buffer_messages[0].role == "assistant"
        assert buffer_messages[0].agent_id == agent_id
        assert buffer_messages[0].metadata["test_key"] == "test_value"
        
        # Проверяем, что сообщение добавлено в суммаризирующую память
        summary_memory = manager.get_summary_memory(user_id)
        summary_messages = summary_memory.get_messages()
        
        assert len(summary_messages) == 1
        assert summary_messages[0].content == content
        assert summary_messages[0].role == "assistant"
    
    def test_add_system_message(self, temp_dir):
        """Тест добавления системного сообщения."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        user_id = "test_user"
        content = "Тестовое системное сообщение"
        metadata = {"test_key": "test_value"}
        
        # Добавляем сообщение
        manager.add_system_message(user_id, content, metadata)
        
        # Проверяем, что сообщение добавлено в буферную память
        buffer_memory = manager.get_buffer_memory(user_id)
        buffer_messages = buffer_memory.get_messages()
        
        assert len(buffer_messages) == 1
        assert buffer_messages[0].content == content
        assert buffer_messages[0].role == "system"
        assert buffer_messages[0].metadata["test_key"] == "test_value"
        
        # Проверяем, что сообщение добавлено в суммаризирующую память
        summary_memory = manager.get_summary_memory(user_id)
        summary_messages = summary_memory.get_messages()
        
        assert len(summary_messages) == 1
        assert summary_messages[0].content == content
        assert summary_messages[0].role == "system"
    
    def test_get_chat_history(self, temp_dir):
        """Тест получения истории чата."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        user_id = "test_user"
        
        # Добавляем сообщения
        manager.add_system_message(user_id, "Системное сообщение")
        manager.add_user_message(user_id, "Сообщение пользователя 1")
        manager.add_assistant_message(user_id, "Сообщение ассистента 1")
        manager.add_user_message(user_id, "Сообщение пользователя 2")
        manager.add_assistant_message(user_id, "Сообщение ассистента 2")
        
        # Получаем всю историю чата
        history = manager.get_chat_history(user_id)
        
        assert len(history) == 5
        assert history[0].role == "system"
        assert history[1].role == "user"
        assert history[2].role == "assistant"
        assert history[3].role == "user"
        assert history[4].role == "assistant"
        
        # Получаем ограниченную историю чата
        limited_history = manager.get_chat_history(user_id, limit=3)
        
        assert len(limited_history) == 3
        # Проверяем, что получены последние 3 сообщения
        assert limited_history[0].role == "assistant"
        assert limited_history[0].content == "Сообщение ассистента 1"
        assert limited_history[1].role == "user"
        assert limited_history[1].content == "Сообщение пользователя 2"
        assert limited_history[2].role == "assistant"
        assert limited_history[2].content == "Сообщение ассистента 2"
    
    def test_get_chat_summary(self, temp_dir):
        """Тест получения резюме чата."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        summarizer = create_simple_summarizer()
        manager = MemoryManager(
            storage_dir=storage_dir,
            summarizer=summarizer,
            default_summarize_threshold=3
        )
        
        user_id = "test_user"
        
        # Добавляем сообщения для создания резюме
        manager.add_system_message(user_id, "Системное сообщение")
        manager.add_user_message(user_id, "Сообщение пользователя 1")
        manager.add_assistant_message(user_id, "Сообщение ассистента 1")
        manager.add_user_message(user_id, "Сообщение пользователя 2")
        manager.add_assistant_message(user_id, "Сообщение ассистента 2")
        
        # Получаем резюме чата
        summary = manager.get_chat_summary(user_id)
        
        assert summary != ""
        # Проверяем, что резюме содержит информацию о сообщениях
        assert "system: " in summary or "user: " in summary or "assistant: " in summary
    
    def test_get_context(self, temp_dir):
        """Тест получения контекста диалога."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        summarizer = create_simple_summarizer()
        manager = MemoryManager(
            storage_dir=storage_dir,
            summarizer=summarizer,
            default_summarize_threshold=3
        )
        
        user_id = "test_user"
        
        # Добавляем сообщения для создания контекста
        manager.add_system_message(user_id, "Системное сообщение")
        manager.add_user_message(user_id, "Сообщение пользователя 1")
        manager.add_assistant_message(user_id, "Сообщение ассистента 1")
        manager.add_user_message(user_id, "Сообщение пользователя 2")
        manager.add_assistant_message(user_id, "Сообщение ассистента 2")
        
        # Получаем контекст
        context = manager.get_context(user_id)
        
        assert "summary" in context
        assert "recent_messages" in context
        assert context["summary"] != ""
        assert len(context["recent_messages"]) > 0
    
    def test_clear_memory(self, temp_dir):
        """Тест очистки памяти."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        user_id = "test_user"
        
        # Добавляем сообщения
        manager.add_user_message(user_id, "Сообщение пользователя")
        manager.add_assistant_message(user_id, "Сообщение ассистента")
        
        # Проверяем, что сообщения добавлены
        assert len(manager.get_chat_history(user_id)) == 2
        
        # Очищаем память
        manager.clear_memory(user_id)
        
        # Проверяем, что память очищена
        assert len(manager.get_chat_history(user_id)) == 0
    
    def test_save_all(self, temp_dir):
        """Тест сохранения всех типов памяти."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        user1_id = "test_user1"
        user2_id = "test_user2"
        
        # Добавляем сообщения для разных пользователей
        manager.add_user_message(user1_id, "Сообщение пользователя 1")
        manager.add_assistant_message(user1_id, "Сообщение ассистента 1")
        
        manager.add_user_message(user2_id, "Сообщение пользователя 2")
        manager.add_assistant_message(user2_id, "Сообщение ассистента 2")
        
        # Сохраняем все типы памяти
        manager.save_all()
        
        # Проверяем, что файлы созданы
        assert os.path.exists(os.path.join(storage_dir, f"{user1_id}_buffer.json"))
        assert os.path.exists(os.path.join(storage_dir, f"{user1_id}_summary.json"))
        assert os.path.exists(os.path.join(storage_dir, f"{user2_id}_buffer.json"))
        assert os.path.exists(os.path.join(storage_dir, f"{user2_id}_summary.json"))
    
    def test_get_all_users(self, temp_dir):
        """Тест получения списка всех пользователей."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        # Изначально список пользователей пуст
        assert len(manager.get_all_users()) == 0
        
        # Добавляем сообщения для разных пользователей
        manager.add_user_message("user1", "Сообщение пользователя 1")
        manager.add_user_message("user2", "Сообщение пользователя 2")
        manager.add_user_message("user3", "Сообщение пользователя 3")
        
        # Получаем список пользователей
        users = manager.get_all_users()
        
        assert len(users) == 3
        assert "user1" in users
        assert "user2" in users
        assert "user3" in users
    
    def test_get_formatted_history(self, temp_dir):
        """Тест получения форматированной истории чата."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        user_id = "test_user"
        
        # Добавляем сообщения
        manager.add_system_message(user_id, "Системное сообщение")
        manager.add_user_message(user_id, "Сообщение пользователя 1")
        manager.add_assistant_message(user_id, "Сообщение ассистента 1")
        manager.add_user_message(user_id, "Сообщение пользователя 2")
        manager.add_assistant_message(user_id, "Сообщение ассистента 2")
        
        # Получаем форматированную историю без системных сообщений
        formatted_history = manager.get_formatted_history(user_id, include_system_messages=False)
        
        assert len(formatted_history) == 4
        assert formatted_history[0]["role"] == "user"
        assert formatted_history[0]["content"] == "Сообщение пользователя 1"
        assert formatted_history[1]["role"] == "assistant"
        assert formatted_history[1]["content"] == "Сообщение ассистента 1"
        
        # Получаем форматированную историю с системными сообщениями
        formatted_history_with_system = manager.get_formatted_history(user_id, include_system_messages=True)
        
        assert len(formatted_history_with_system) == 5
        assert formatted_history_with_system[0]["role"] == "system"
        assert formatted_history_with_system[0]["content"] == "Системное сообщение"
        
        # Получаем ограниченную форматированную историю
        limited_formatted_history = manager.get_formatted_history(user_id, include_system_messages=False, limit=2)
        
        assert len(limited_formatted_history) == 2
        assert limited_formatted_history[0]["role"] == "user"
        assert limited_formatted_history[0]["content"] == "Сообщение пользователя 2"
        assert limited_formatted_history[1]["role"] == "assistant"
        assert limited_formatted_history[1]["content"] == "Сообщение ассистента 2" 