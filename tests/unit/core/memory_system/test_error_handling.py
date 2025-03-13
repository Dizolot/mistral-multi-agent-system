#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для проверки обработки ошибок в системе памяти.

Проверяет поведение системы памяти при некорректных входных данных
и ошибках сохранения/загрузки.
"""

import pytest
import os
import tempfile
import shutil
import json
from unittest.mock import patch, mock_open
from datetime import datetime

from src.core.memory_system import (
    MemoryManager,
    BufferMemory,
    SummaryMemory,
    Message,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    create_simple_summarizer
)


class TestErrorHandling:
    """Тесты для проверки обработки ошибок в системе памяти."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_invalid_message_deserialization(self):
        """Тест обработки ошибок при десериализации некорректных сообщений."""
        # Некорректные данные сообщения
        invalid_data = {
            "content": "Тестовое сообщение",
            # Отсутствует поле role
            "timestamp": datetime.now().isoformat()
        }
        
        # Проверяем, что вызывается исключение
        with pytest.raises(KeyError):
            Message.from_dict(invalid_data)
    
    def test_invalid_timestamp_format(self):
        """Тест обработки ошибок при некорректном формате временной метки."""
        # Некорректный формат временной метки
        invalid_data = {
            "content": "Тестовое сообщение",
            "role": "user",
            "timestamp": "2023-01-01"  # Некорректный формат
        }
        
        # Проверяем, что вызывается исключение
        with pytest.raises(ValueError):
            Message.from_dict(invalid_data)
    
    def test_buffer_memory_save_permission_error(self, temp_dir):
        """Тест обработки ошибок при отсутствии прав на сохранение файла."""
        # Создаем директорию только для чтения
        readonly_dir = os.path.join(temp_dir, "readonly")
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o500)  # Только чтение и выполнение
        
        storage_path = os.path.join(readonly_dir, "buffer.json")
        memory = BufferMemory("test_buffer", storage_path=storage_path)
        
        # Добавляем сообщение
        memory.add_message(UserMessage("Тестовое сообщение", "user123"))
        
        # Проверяем, что при сохранении вызывается исключение
        with pytest.raises(PermissionError):
            memory.save()
    
    def test_buffer_memory_load_invalid_json(self, temp_dir):
        """Тест обработки ошибок при загрузке некорректного JSON-файла."""
        storage_path = os.path.join(temp_dir, "invalid.json")
        
        # Создаем файл с некорректным JSON
        with open(storage_path, 'w') as f:
            f.write("This is not a valid JSON")
        
        memory = BufferMemory("test_buffer", storage_path=storage_path)
        
        # Проверяем, что при загрузке вызывается исключение
        with pytest.raises(json.JSONDecodeError):
            memory.load()
    
    def test_buffer_memory_load_missing_fields(self, temp_dir):
        """Тест обработки ошибок при загрузке файла с отсутствующими полями."""
        storage_path = os.path.join(temp_dir, "missing_fields.json")
        
        # Создаем файл с отсутствующими полями
        with open(storage_path, 'w') as f:
            json.dump({
                "memory_id": "test_buffer",
                # Отсутствуют поля description, max_messages, messages
            }, f)
        
        memory = BufferMemory("test_buffer", storage_path=storage_path)
        
        # Проверяем, что при загрузке вызывается исключение
        with pytest.raises(KeyError):
            memory.load()
    
    def test_summary_memory_without_summarizer(self):
        """Тест поведения суммаризирующей памяти без суммаризатора."""
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=3
        )
        
        # Добавляем сообщения выше порога суммаризации
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Проверяем, что буфер не очищен, так как суммаризатор не задан
        assert len(memory.buffer.get_messages()) == 5
        
        # Проверяем, что резюме не обновлено
        assert memory.summary == ""
    
    def test_memory_manager_invalid_user_id(self, temp_dir):
        """Тест обработки ошибок при использовании некорректного идентификатора пользователя."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        # Проверяем различные некорректные идентификаторы
        invalid_ids = [None, "", 123, {}]
        
        for invalid_id in invalid_ids:
            with pytest.raises((TypeError, AttributeError)):
                manager.add_user_message(invalid_id, "Тестовое сообщение")
    
    def test_memory_manager_invalid_content(self, temp_dir):
        """Тест обработки ошибок при использовании некорректного содержимого сообщения."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        # Проверяем различные некорректные содержимые
        invalid_contents = [None, 123, {}]
        
        for invalid_content in invalid_contents:
            with pytest.raises((TypeError, AttributeError)):
                manager.add_user_message("user123", invalid_content)
    
    def test_memory_manager_save_all_error_handling(self, temp_dir):
        """Тест обработки ошибок при сохранении всех типов памяти."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        # Добавляем сообщения для двух пользователей
        manager.add_user_message("user1", "Сообщение от пользователя 1")
        manager.add_user_message("user2", "Сообщение от пользователя 2")
        
        # Патчим метод save буферной памяти, чтобы он вызывал исключение
        with patch.object(BufferMemory, 'save', side_effect=Exception("Ошибка сохранения")):
            # Проверяем, что исключение не распространяется наружу
            manager.save_all()
            
            # Проверяем, что второй пользователь все еще может быть сохранен
            assert os.path.exists(os.path.join(storage_dir, "user2_buffer.json"))
    
    def test_memory_manager_load_error_handling(self, temp_dir):
        """Тест обработки ошибок при загрузке памяти."""
        storage_dir = os.path.join(temp_dir, "memory_test")
        manager = MemoryManager(storage_dir=storage_dir)
        
        # Добавляем сообщение и сохраняем
        manager.add_user_message("user1", "Тестовое сообщение")
        manager.save_all()
        
        # Создаем некорректный файл памяти
        with open(os.path.join(storage_dir, "user2_buffer.json"), 'w') as f:
            f.write("This is not a valid JSON")
        
        # Получаем память для пользователя с некорректным файлом
        # Проверяем, что создается новая память вместо загрузки некорректной
        buffer_memory = manager.get_buffer_memory("user2")
        
        # Проверяем, что память пуста
        assert len(buffer_memory.get_messages()) == 0
    
    def test_summarizer_error_handling(self):
        """Тест обработки ошибок в суммаризаторе."""
        # Создаем суммаризатор, который вызывает исключение
        def failing_summarizer(messages, current_summary=None):
            raise Exception("Ошибка суммаризации")
        
        memory = SummaryMemory(
            "test_summary",
            buffer_size=10,
            summarize_threshold=3,
            summarizer=failing_summarizer
        )
        
        # Добавляем сообщения выше порога суммаризации
        for i in range(5):
            memory.add_message(Message(f"Сообщение {i}", "user"))
        
        # Проверяем, что исключение не распространяется наружу
        # и что буфер не очищен
        assert len(memory.buffer.get_messages()) == 5
        
        # Проверяем, что резюме не обновлено
        assert memory.summary == "" 