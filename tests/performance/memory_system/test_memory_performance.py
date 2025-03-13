#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты производительности для системы памяти.

Проверяет производительность различных компонентов системы памяти,
включая буферную память, суммаризацию и менеджер памяти.
"""

import time
import os
import tempfile
import shutil
import pytest
import psutil

from src.core.memory_system import (
    MemoryManager,
    BufferMemory,
    SummaryMemory,
    UserMessage,
    AssistantMessage,
    create_simple_summarizer,
    create_keyword_summarizer
)


class TestMemoryPerformance:
    """Тесты производительности для системы памяти."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_buffer_memory_add_performance(self, temp_dir):
        """Тест производительности добавления сообщений в буферную память."""
        buffer_memory = BufferMemory(
            memory_id="buffer_perf",
            description="Буферная память для тестирования производительности",
            max_messages=1000,
            storage_path=os.path.join(temp_dir, "buffer_perf.json")
        )
        
        # Подготовка тестовых данных
        num_messages = 1000
        messages = [
            UserMessage(f"Тестовое сообщение {i}", f"user{i % 10}")
            for i in range(num_messages)
        ]
        
        # Измерение времени добавления сообщений
        start_time = time.time()
        for message in messages:
            buffer_memory.add_message(message)
        end_time = time.time()
        
        # Вычисление метрик
        total_time = end_time - start_time
        avg_time_per_message = total_time / num_messages
        
        print(f"\nПроизводительность BufferMemory.add_message:")
        print(f"Всего сообщений: {num_messages}")
        print(f"Общее время: {total_time:.4f} сек")
        print(f"Среднее время на сообщение: {avg_time_per_message*1000:.4f} мс")
        
        # Проверка, что время добавления одного сообщения не превышает 1 мс
        assert avg_time_per_message < 0.001, f"Среднее время добавления сообщения ({avg_time_per_message*1000:.4f} мс) превышает 1 мс"
    
    def test_summary_memory_summarization_performance(self, temp_dir):
        """Тест производительности суммаризации в SummaryMemory."""
        # Создаем суммаризатор
        summarizer = create_simple_summarizer()
        
        # Создаем память с суммаризацией
        summary_memory = SummaryMemory(
            memory_id="summary_perf",
            description="Суммаризирующая память для тестирования производительности",
            summarizer=summarizer,
            summarize_threshold=10,
            storage_path=os.path.join(temp_dir, "summary_perf.json")
        )
        
        # Подготовка тестовых данных
        num_messages = 50
        messages = []
        for i in range(num_messages):
            messages.append(UserMessage(
                f"Пользователь спрашивает о теме {i % 5}. Это сообщение содержит достаточно текста, чтобы суммаризатор мог работать с содержательным текстом.",
                f"user{i % 3}"
            ))
            messages.append(AssistantMessage(
                f"Ответ на вопрос о теме {i % 5}. Здесь содержится подробная информация по запрошенной теме с деталями и примерами.",
                f"assistant{i % 2}"
            ))
        
        # Добавляем сообщения и измеряем время суммаризации
        start_time = time.time()
        for message in messages:
            summary_memory.add_message(message)
        end_time = time.time()
        
        # Вычисление метрик
        total_time = end_time - start_time
        avg_time_per_message = total_time / len(messages)
        
        # Получаем текущее использование памяти
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # в МБ
        
        print(f"\nПроизводительность SummaryMemory.add_message с суммаризацией:")
        print(f"Всего сообщений: {len(messages)}")
        print(f"Общее время: {total_time:.4f} сек")
        print(f"Среднее время на сообщение: {avg_time_per_message*1000:.4f} мс")
        print(f"Использование памяти: {memory_usage:.2f} МБ")
        
        # Проверка, что время добавления одного сообщения не превышает 10 мс
        assert avg_time_per_message < 0.01, f"Среднее время добавления сообщения с суммаризацией ({avg_time_per_message*1000:.4f} мс) превышает 10 мс"
    
    def test_memory_manager_context_retrieval_performance(self, temp_dir):
        """Тест производительности получения контекста из MemoryManager."""
        # Создаем менеджер памяти
        memory_manager = MemoryManager(
            storage_dir=os.path.join(temp_dir, "manager_perf"),
            summarizer=create_keyword_summarizer(),
            default_summarize_threshold=5
        )
        
        # Подготовка тестовых данных
        num_users = 10
        messages_per_user = 20
        
        # Добавляем сообщения для разных пользователей
        for user_idx in range(num_users):
            user_id = f"user{user_idx}"
            for msg_idx in range(messages_per_user):
                memory_manager.add_user_message(
                    user_id,
                    f"Запрос пользователя {user_id} номер {msg_idx}. Содержит информацию о теме {msg_idx % 5}."
                )
                memory_manager.add_assistant_message(
                    user_id,
                    f"Ответ на запрос пользователя {user_id} номер {msg_idx}. Подробная информация по теме {msg_idx % 5}.",
                    agent_id=f"agent{msg_idx % 3}"
                )
        
        # Измеряем время получения контекста
        start_time = time.time()
        for user_idx in range(num_users):
            user_id = f"user{user_idx}"
            context = memory_manager.get_context(user_id)
        end_time = time.time()
        
        # Вычисление метрик
        total_time = end_time - start_time
        avg_time_per_user = total_time / num_users
        
        print(f"\nПроизводительность MemoryManager.get_context:")
        print(f"Количество пользователей: {num_users}")
        print(f"Сообщений на пользователя: {messages_per_user}")
        print(f"Общее время: {total_time:.4f} сек")
        print(f"Среднее время на пользователя: {avg_time_per_user*1000:.4f} мс")
        
        # Проверка, что время получения контекста не превышает 5 мс на пользователя
        assert avg_time_per_user < 0.005, f"Среднее время получения контекста ({avg_time_per_user*1000:.4f} мс) превышает 5 мс"
    
    def test_memory_persistence_performance(self, temp_dir):
        """Тест производительности сохранения и загрузки состояния памяти."""
        # Создаем менеджер памяти
        storage_dir = os.path.join(temp_dir, "persistence_perf")
        memory_manager = MemoryManager(
            storage_dir=storage_dir,
            summarizer=create_simple_summarizer(),
            default_summarize_threshold=10
        )
        
        # Подготовка тестовых данных
        num_users = 5
        messages_per_user = 30
        
        # Добавляем сообщения для разных пользователей
        for user_idx in range(num_users):
            user_id = f"user{user_idx}"
            for msg_idx in range(messages_per_user):
                memory_manager.add_user_message(
                    user_id,
                    f"Запрос пользователя {user_id} номер {msg_idx}. Содержит информацию о теме {msg_idx % 5}."
                )
                memory_manager.add_assistant_message(
                    user_id,
                    f"Ответ на запрос пользователя {user_id} номер {msg_idx}. Подробная информация по теме {msg_idx % 5}.",
                    agent_id=f"agent{msg_idx % 3}"
                )
        
        # Измеряем время сохранения
        start_time = time.time()
        memory_manager.save_all()
        save_time = time.time() - start_time
        
        # Создаем новый менеджер памяти и измеряем время загрузки
        start_time = time.time()
        new_memory_manager = MemoryManager(
            storage_dir=storage_dir,
            summarizer=create_simple_summarizer()
        )
        load_time = time.time() - start_time
        
        # Проверяем, что данные загружены корректно
        for user_idx in range(num_users):
            user_id = f"user{user_idx}"
            history = new_memory_manager.get_chat_history(user_id)
            # Проверяем, что история загружена (может быть не точно messages_per_user * 2 из-за суммаризации)
            assert len(history) > 0
        
        print(f"\nПроизводительность сохранения и загрузки памяти:")
        print(f"Количество пользователей: {num_users}")
        print(f"Сообщений на пользователя: {messages_per_user}")
        print(f"Время сохранения: {save_time*1000:.4f} мс")
        print(f"Время загрузки: {load_time*1000:.4f} мс")
        
        # Проверка, что время сохранения и загрузки не превышает допустимые значения
        assert save_time < 0.1, f"Время сохранения ({save_time*1000:.4f} мс) превышает 100 мс"
        assert load_time < 0.1, f"Время загрузки ({load_time*1000:.4f} мс) превышает 100 мс"


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 