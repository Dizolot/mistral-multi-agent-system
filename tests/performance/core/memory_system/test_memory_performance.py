#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты производительности системы памяти.

Измеряет время выполнения операций с памятью при различных объемах данных
и оценивает использование памяти при различных конфигурациях.
"""

import pytest
import os
import tempfile
import shutil
import time
import random
import string
import psutil
import gc
from typing import List, Optional

from src.core.memory_system import (
    MemoryManager,
    BufferMemory,
    SummaryMemory,
    Message,
    UserMessage,
    AssistantMessage,
    create_simple_summarizer
)


def generate_random_message(length: int = 100, user_id: str = "test_user") -> Message:
    """Генерирует случайное сообщение заданной длины."""
    content = ''.join(random.choice(string.ascii_letters + string.digits + ' ') for _ in range(length))
    if random.choice([True, False]):
        return UserMessage(content, user_id)
    else:
        return AssistantMessage(content, "test_agent")


def measure_memory_usage() -> float:
    """Измеряет текущее использование памяти процессом."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # В МБ


class TestMemoryPerformance:
    """Тесты производительности системы памяти."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_buffer_memory_add_performance(self, temp_dir):
        """Тест производительности добавления сообщений в буферную память."""
        storage_path = os.path.join(temp_dir, "buffer_perf.json")
        memory = BufferMemory("buffer_perf", max_messages=1000, storage_path=storage_path)
        
        message_counts = [10, 100, 1000]
        results = {}
        
        for count in message_counts:
            messages = [generate_random_message() for _ in range(count)]
            
            # Измеряем время добавления сообщений
            start_time = time.time()
            for message in messages:
                memory.add_message(message)
            end_time = time.time()
            
            results[count] = end_time - start_time
            
            # Очищаем память для следующего теста
            memory.clear()
        
        # Выводим результаты
        print("\nПроизводительность добавления сообщений в буферную память:")
        for count, elapsed in results.items():
            print(f"{count} сообщений: {elapsed:.6f} секунд ({count/elapsed:.2f} сообщений/сек)")
        
        # Проверяем, что время выполнения растет линейно
        assert results[100] < results[1000]
    
    def test_buffer_memory_get_performance(self, temp_dir):
        """Тест производительности получения сообщений из буферной памяти."""
        storage_path = os.path.join(temp_dir, "buffer_perf.json")
        memory = BufferMemory("buffer_perf", max_messages=1000, storage_path=storage_path)
        
        # Добавляем 1000 сообщений
        for _ in range(1000):
            memory.add_message(generate_random_message())
        
        limit_values = [10, 100, 1000, None]
        results = {}
        
        for limit in limit_values:
            # Измеряем время получения сообщений
            start_time = time.time()
            messages = memory.get_messages(limit)
            end_time = time.time()
            
            results[limit] = end_time - start_time
        
        # Выводим результаты
        print("\nПроизводительность получения сообщений из буферной памяти:")
        for limit, elapsed in results.items():
            limit_str = str(limit) if limit is not None else "все"
            print(f"Получение {limit_str} сообщений: {elapsed:.6f} секунд")
    
    def test_buffer_memory_save_load_performance(self, temp_dir):
        """Тест производительности сохранения и загрузки буферной памяти."""
        storage_path = os.path.join(temp_dir, "buffer_perf.json")
        memory = BufferMemory("buffer_perf", max_messages=1000, storage_path=storage_path)
        
        message_counts = [10, 100, 1000]
        save_results = {}
        load_results = {}
        
        for count in message_counts:
            # Добавляем сообщения
            for _ in range(count):
                memory.add_message(generate_random_message())
            
            # Измеряем время сохранения
            start_time = time.time()
            memory.save()
            end_time = time.time()
            save_results[count] = end_time - start_time
            
            # Создаем новую память и измеряем время загрузки
            new_memory = BufferMemory("buffer_perf", max_messages=1000, storage_path=storage_path)
            start_time = time.time()
            new_memory.load()
            end_time = time.time()
            load_results[count] = end_time - start_time
            
            # Очищаем память для следующего теста
            memory.clear()
        
        # Выводим результаты
        print("\nПроизводительность сохранения буферной памяти:")
        for count, elapsed in save_results.items():
            print(f"{count} сообщений: {elapsed:.6f} секунд")
        
        print("\nПроизводительность загрузки буферной памяти:")
        for count, elapsed in load_results.items():
            print(f"{count} сообщений: {elapsed:.6f} секунд")
    
    def test_summary_memory_performance(self, temp_dir):
        """Тест производительности суммаризирующей памяти."""
        storage_path = os.path.join(temp_dir, "summary_perf.json")
        summarizer = create_simple_summarizer()
        memory = SummaryMemory(
            "summary_perf",
            buffer_size=100,
            summarize_threshold=10,
            summarizer=summarizer,
            storage_path=storage_path
        )
        
        # Добавляем сообщения и измеряем время
        message_counts = [10, 50, 100]
        results = {}
        
        for count in message_counts:
            messages = [generate_random_message() for _ in range(count)]
            
            # Очищаем память перед тестом
            memory.clear()
            
            # Измеряем время добавления сообщений
            start_time = time.time()
            for message in messages:
                memory.add_message(message)
            end_time = time.time()
            
            results[count] = end_time - start_time
        
        # Выводим результаты
        print("\nПроизводительность суммаризирующей памяти:")
        for count, elapsed in results.items():
            print(f"{count} сообщений: {elapsed:.6f} секунд ({count/elapsed:.2f} сообщений/сек)")
            
        # Проверяем, что время выполнения растет с увеличением количества сообщений
        assert results[10] < results[100]
    
    def test_memory_manager_performance(self, temp_dir):
        """Тест производительности менеджера памяти."""
        storage_dir = os.path.join(temp_dir, "manager_perf")
        summarizer = create_simple_summarizer()
        manager = MemoryManager(
            storage_dir=storage_dir,
            default_buffer_size=100,
            default_summarize_threshold=10,
            summarizer=summarizer
        )
        
        # Тестируем производительность с разным количеством пользователей и сообщений
        user_counts = [1, 10, 50]
        message_per_user = 20
        
        for user_count in user_counts:
            # Создаем пользователей
            users = [f"user_{i}" for i in range(user_count)]
            
            # Измеряем время добавления сообщений
            start_time = time.time()
            for user_id in users:
                for i in range(message_per_user):
                    if i % 2 == 0:
                        manager.add_user_message(user_id, f"Сообщение {i} от пользователя {user_id}")
                    else:
                        manager.add_assistant_message(user_id, f"Ответ на сообщение {i-1}", f"agent_{i%5}")
            end_time = time.time()
            
            elapsed = end_time - start_time
            total_messages = user_count * message_per_user
            
            print(f"\n{user_count} пользователей, {message_per_user} сообщений на пользователя:")
            print(f"Время: {elapsed:.6f} секунд ({total_messages/elapsed:.2f} сообщений/сек)")
            
            # Измеряем время сохранения всех данных
            start_time = time.time()
            manager.save_all()
            end_time = time.time()
            
            print(f"Время сохранения: {end_time - start_time:.6f} секунд")
    
    def test_memory_usage(self, temp_dir):
        """Тест использования памяти при различных конфигурациях."""
        storage_dir = os.path.join(temp_dir, "memory_usage")
        
        # Измеряем базовое использование памяти
        gc.collect()
        base_memory = measure_memory_usage()
        
        # Тестируем различные конфигурации
        configs = [
            {"buffer_size": 100, "message_count": 1000},
            {"buffer_size": 1000, "message_count": 1000},
            {"buffer_size": 10000, "message_count": 1000}
        ]
        
        results = {}
        
        for config in configs:
            buffer_size = config["buffer_size"]
            message_count = config["message_count"]
            
            # Создаем менеджер памяти
            manager = MemoryManager(
                storage_dir=storage_dir,
                default_buffer_size=buffer_size,
                summarizer=create_simple_summarizer()
            )
            
            # Добавляем сообщения
            user_id = "test_user"
            for i in range(message_count):
                if i % 2 == 0:
                    manager.add_user_message(user_id, f"Сообщение {i}")
                else:
                    manager.add_assistant_message(user_id, f"Ответ на сообщение {i-1}")
            
            # Измеряем использование памяти
            gc.collect()
            memory_usage = measure_memory_usage() - base_memory
            
            results[buffer_size] = memory_usage
            
            # Очищаем менеджер
            del manager
            gc.collect()
        
        # Выводим результаты
        print("\nИспользование памяти при различных конфигурациях:")
        for buffer_size, memory_usage in results.items():
            print(f"Размер буфера {buffer_size}: {memory_usage:.2f} МБ")
        
        # Проверяем, что использование памяти растет с увеличением размера буфера
        assert results[100] < results[10000] 