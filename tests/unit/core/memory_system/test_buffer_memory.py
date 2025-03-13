#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для буферной памяти.

Проверяет функциональность буферной памяти, включая добавление и получение сообщений,
сохранение и загрузку состояния.
"""

import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime

from src.core.memory_system.memory_base import Message, UserMessage, AssistantMessage
from src.core.memory_system.buffer_memory import BufferMemory


class TestBufferMemory:
    """Тесты для буферной памяти."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_buffer_memory_initialization(self):
        """Тест инициализации буферной памяти."""
        memory_id = "test_buffer"
        description = "Тестовая буферная память"
        max_messages = 10
        
        memory = BufferMemory(memory_id, description, max_messages)
        
        assert memory.memory_id == memory_id
        assert memory.description == description
        assert memory.max_messages == max_messages
        assert len(memory.messages) == 0
    
    def test_add_message(self):
        """Тест добавления сообщения в буфер."""
        memory = BufferMemory("test_buffer", max_messages=5)
        
        message1 = UserMessage("Сообщение 1", "user123")
        message2 = AssistantMessage("Сообщение 2", "agent123")
        
        memory.add_message(message1)
        memory.add_message(message2)
        
        assert len(memory.messages) == 2
        assert memory.messages[0].content == "Сообщение 1"
        assert memory.messages[1].content == "Сообщение 2"
    
    def test_get_messages(self):
        """Тест получения сообщений из буфера."""
        memory = BufferMemory("test_buffer", max_messages=5)
        
        # Добавляем сообщения
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Получаем все сообщения
        all_messages = memory.get_messages()
        assert len(all_messages) == 5
        
        # Получаем ограниченное количество сообщений
        limited_messages = memory.get_messages(limit=3)
        assert len(limited_messages) == 3
        assert limited_messages[0].content == "Сообщение 2"
        assert limited_messages[2].content == "Сообщение 4"
    
    def test_max_messages_limit(self):
        """Тест ограничения максимального количества сообщений."""
        memory = BufferMemory("test_buffer", max_messages=3)
        
        # Добавляем сообщения
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Проверяем, что в буфере только последние 3 сообщения
        messages = memory.get_messages()
        assert len(messages) == 3
        assert messages[0].content == "Сообщение 2"
        assert messages[1].content == "Сообщение 3"
        assert messages[2].content == "Сообщение 4"
    
    def test_clear(self):
        """Тест очистки буфера."""
        memory = BufferMemory("test_buffer")
        
        # Добавляем сообщения
        for i in range(3):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        assert len(memory.messages) == 3
        
        # Очищаем буфер
        memory.clear()
        
        assert len(memory.messages) == 0
    
    def test_save_and_load(self, temp_dir):
        """Тест сохранения и загрузки состояния буфера."""
        storage_path = os.path.join(temp_dir, "buffer_test.json")
        
        # Создаем и заполняем буфер
        memory1 = BufferMemory("test_buffer", max_messages=5, storage_path=storage_path)
        memory1.add_message(UserMessage("Сообщение пользователя", "user123"))
        memory1.add_message(AssistantMessage("Сообщение ассистента", "agent123"))
        
        # Сохраняем состояние
        memory1.save()
        
        # Проверяем, что файл создан
        assert os.path.exists(storage_path)
        
        # Создаем новый буфер и загружаем состояние
        memory2 = BufferMemory("test_buffer", max_messages=10, storage_path=storage_path)
        memory2.load()
        
        # Проверяем, что состояние загружено корректно
        assert memory2.max_messages == 5  # Должно быть загружено из файла
        assert len(memory2.messages) == 2
        assert memory2.messages[0].content == "Сообщение пользователя"
        assert memory2.messages[1].content == "Сообщение ассистента"
    
    def test_save_without_storage_path(self):
        """Тест сохранения без указания пути хранения."""
        memory = BufferMemory("test_buffer")
        
        # Попытка сохранения без указания пути должна вызвать исключение
        with pytest.raises(ValueError):
            memory.save()
    
    def test_load_without_storage_path(self):
        """Тест загрузки без указания пути хранения."""
        memory = BufferMemory("test_buffer")
        
        # Попытка загрузки без указания пути должна вызвать исключение
        with pytest.raises(ValueError):
            memory.load()
    
    def test_load_nonexistent_file(self, temp_dir):
        """Тест загрузки из несуществующего файла."""
        storage_path = os.path.join(temp_dir, "nonexistent.json")
        memory = BufferMemory("test_buffer", storage_path=storage_path)
        
        # Попытка загрузки из несуществующего файла должна вызвать исключение
        with pytest.raises(FileNotFoundError):
            memory.load()
    
    def test_get_info(self, temp_dir):
        """Тест получения информации о буферной памяти."""
        memory_id = "test_buffer"
        description = "Тестовая буферная память"
        max_messages = 10
        storage_path = os.path.join(temp_dir, "buffer_info_test.json")
        
        memory = BufferMemory(memory_id, description, max_messages, storage_path)
        
        # Добавляем сообщения
        for i in range(3):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        info = memory.get_info()
        
        assert info["memory_id"] == memory_id
        assert info["description"] == description
        assert info["type"] == "BufferMemory"
        assert info["max_messages"] == max_messages
        assert info["current_messages"] == 3
        assert info["storage_path"] == storage_path 