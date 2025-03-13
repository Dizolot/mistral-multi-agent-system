#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты производительности для интеграции системы памяти с агентами.

Проверяет эффективность совместной работы системы памяти и агентов
при обработке различных объемов данных и сценариев использования.
"""

import time
import os
import tempfile
import shutil
import pytest
import psutil
import json
import csv
from typing import Dict, List, Any
from datetime import datetime
from unittest.mock import MagicMock

from src.core.memory_system import (
    MemoryManager,
    BufferMemory,
    SummaryMemory,
    create_simple_summarizer
)
from src.core.agent_manager.agent_manager import AgentManager
from src.core.agent_manager.general_agent import GeneralAgent


class MemoryEnabledAgentManager:
    """
    Тестовая реализация менеджера агентов с поддержкой системы памяти.
    
    Аналогична реализации из примера agent_integration_example.py и тестов.
    """
    
    def __init__(
        self,
        memory_manager,
        agent_manager
    ):
        self.memory_manager = memory_manager
        self.agent_manager = agent_manager
    
    def process_query(
        self,
        query,
        user_id,
        context=None
    ):
        # Добавляем сообщение пользователя в память
        self.memory_manager.add_user_message(user_id, query)
        
        # Получаем контекст из памяти
        memory_context = self.memory_manager.get_context(user_id)
        
        # Объединяем контексты
        combined_context = context or {}
        combined_context["memory"] = memory_context
        
        # Обрабатываем запрос с учетом контекста
        result = self.agent_manager.process_query(query, combined_context)
        
        # Добавляем ответ в память
        agent_id = result.get("agent_id", None)
        response_text = ""
        
        # Корректное извлечение ответа
        if result.get("success", False):
            agent_result = result.get("result", {})
            if isinstance(agent_result, dict) and "response" in agent_result:
                response_text = agent_result["response"]
            elif isinstance(agent_result, str):
                response_text = agent_result
            else:
                response_text = str(agent_result)
        else:
            response_text = result.get("error", "Ответ не получен")
            
        self.memory_manager.add_assistant_message(
            user_id,
            response_text,
            agent_id=agent_id
        )
        
        # Сохраняем состояние памяти
        self.memory_manager.save_all()
        
        return result


class TestMemoryAgentPerformance:
    """Тесты производительности для интеграции системы памяти с агентами."""
    
    @pytest.fixture
    def results_dir(self):
        """Создает директорию для результатов тестов."""
        results_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "results"
        )
        os.makedirs(results_dir, exist_ok=True)
        return results_dir
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_agent(self):
        """Создает заглушку агента для тестов."""
        agent = MagicMock(spec=GeneralAgent)
        agent.agent_id = "test_agent"
        agent.name = "Тестовый агент"
        agent.description = "Агент для тестирования производительности"
        
        # Настраиваем поведение метода calculate_relevance
        agent.calculate_relevance.return_value = 0.8
        
        # Переопределяем метод process_query для тестов
        def mock_process_query(query, context=None):
            # Симулируем задержку обработки запроса
            time.sleep(0.01)
            
            # Формируем ответ с учетом контекста из памяти
            if context and "memory" in context:
                memory_context = context["memory"]
                if memory_context["summary"]:
                    return {
                        "response": f"Ответ с учетом резюме: {memory_context['summary'][:30]}...",
                        "agent_id": "test_agent"
                    }
                elif memory_context["recent_messages"]:
                    return {
                        "response": f"Ответ с учетом последних сообщений ({len(memory_context['recent_messages'])})",
                        "agent_id": "test_agent"
                    }
            
            return {
                "response": f"Базовый ответ на запрос: {query}",
                "agent_id": "test_agent" 
            }
        
        agent.process_query.side_effect = mock_process_query
        return agent
    
    @pytest.fixture
    def memory_enabled_agent_manager(self, temp_dir, mock_agent):
        """Создает менеджер агентов с поддержкой памяти."""
        # Создаем менеджер памяти
        memory_manager = MemoryManager(
            storage_dir=os.path.join(temp_dir, "memory_perf"),
            summarizer=create_simple_summarizer(),
            default_summarize_threshold=5
        )
        
        # Создаем менеджер агентов
        agent_manager = AgentManager()
        agent_manager.register_agent(mock_agent)
        agent_manager.default_agent_id = mock_agent.agent_id
        
        # Создаем менеджер агентов с поддержкой памяти
        return MemoryEnabledAgentManager(memory_manager, agent_manager)
    
    def save_results(self, results_dir, test_name, metrics):
        """Сохраняет результаты теста в JSON и CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Сохраняем в JSON
        json_path = os.path.join(results_dir, f"{test_name}_{timestamp}.json")
        with open(json_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Сохраняем в CSV
        csv_path = os.path.join(results_dir, f"{test_name}_{timestamp}.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            for key, value in metrics.items():
                writer.writerow([key, value])
        
        return json_path, csv_path
    
    def test_memory_agent_conversation_performance(self, memory_enabled_agent_manager, results_dir):
        """Тест производительности диалога с использованием памяти."""
        user_id = "perf_test_user"
        
        # Подготовка тестовых данных для диалога
        conversation = [
            "Привет! Я хочу узнать о системе памяти.",
            "Как работает суммаризация?",
            "Какие преимущества дает использование контекста?",
            "Как это интегрируется с агентами?",
            "Можно ли использовать эту систему для долгосрочного хранения информации?",
            "Как обеспечивается эффективность при большом объеме сообщений?",
            "Есть ли ограничения на объем хранимых данных?",
            "Как обрабатываются конфиденциальные данные?",
            "Можно ли настроить срок хранения информации?",
            "Спасибо за информацию!"
        ]
        
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # в МБ
        
        # Измеряем время обработки всей беседы
        total_time_start = time.time()
        
        # Измеряем время для каждого сообщения
        message_times = []
        
        for message in conversation:
            message_start = time.time()
            result = memory_enabled_agent_manager.process_query(message, user_id)
            message_end = time.time()
            message_times.append(message_end - message_start)
        
        total_time_end = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # в МБ
        
        # Вычисляем метрики
        total_time = total_time_end - total_time_start
        avg_message_time = sum(message_times) / len(message_times)
        memory_usage = end_memory - start_memory
        
        # Получаем статистику о сохраненных данных
        history = memory_enabled_agent_manager.memory_manager.get_chat_history(user_id)
        
        # Подготавливаем результаты
        metrics = {
            "total_conversation_time": total_time,
            "average_message_time": avg_message_time,
            "memory_usage_mb": memory_usage,
            "total_messages": len(history),
            "message_times": message_times,
            "messages_per_second": len(conversation) / total_time
        }
        
        # Сохраняем результаты
        json_path, csv_path = self.save_results(
            results_dir, 
            "memory_agent_conversation", 
            metrics
        )
        
        print(f"\nПроизводительность диалога с использованием памяти:")
        print(f"Всего сообщений: {len(conversation)}")
        print(f"Общее время обработки: {total_time:.4f} сек")
        print(f"Среднее время на сообщение: {avg_message_time*1000:.4f} мс")
        print(f"Использование памяти: {memory_usage:.2f} МБ")
        print(f"Сообщений в секунду: {len(conversation) / total_time:.2f}")
        print(f"Результаты сохранены в:\n{json_path}\n{csv_path}")
        
        # Базовая проверка производительности
        assert avg_message_time < 0.1, f"Среднее время обработки сообщения слишком велико: {avg_message_time*1000:.2f} мс"
    
    def test_memory_agent_scaling_performance(self, temp_dir, mock_agent, results_dir):
        """Тест масштабируемости интеграции памяти и агентов."""
        # Количество пользователей и сообщений для теста
        num_users = 5
        messages_per_user = [5, 10, 20, 30, 50]
        
        scaling_results = []
        
        for msgs_count in messages_per_user:
            # Создаем новый экземпляр для каждого теста
            memory_manager = MemoryManager(
                storage_dir=os.path.join(temp_dir, f"scaling_perf_{msgs_count}"),
                summarizer=create_simple_summarizer(),
                default_summarize_threshold=5
            )
            
            agent_manager = AgentManager()
            agent_manager.register_agent(mock_agent)
            agent_manager.default_agent_id = mock_agent.agent_id
            
            mem_agent_manager = MemoryEnabledAgentManager(memory_manager, agent_manager)
            
            process = psutil.Process(os.getpid())
            start_memory = process.memory_info().rss / 1024 / 1024
            
            # Генерируем сообщения
            start_time = time.time()
            
            for user_idx in range(num_users):
                user_id = f"scale_user_{user_idx}"
                
                for msg_idx in range(msgs_count):
                    query = f"Тестовый запрос {msg_idx} от пользователя {user_id}"
                    mem_agent_manager.process_query(query, user_id)
            
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024
            
            # Расчет метрик
            total_messages = num_users * msgs_count
            total_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            result = {
                "messages_per_user": msgs_count,
                "total_users": num_users,
                "total_messages": total_messages,
                "total_time": total_time,
                "avg_time_per_message": total_time / total_messages,
                "memory_usage_mb": memory_usage,
                "messages_per_second": total_messages / total_time
            }
            
            scaling_results.append(result)
        
        # Сохраняем результаты
        metrics = {
            "scaling_results": scaling_results,
            "num_users": num_users,
            "messages_per_user_variants": messages_per_user
        }
        
        json_path, csv_path = self.save_results(
            results_dir,
            "memory_agent_scaling",
            metrics
        )
        
        print(f"\nПроизводительность при масштабировании:")
        for result in scaling_results:
            print(f"Сообщений на пользователя: {result['messages_per_user']}")
            print(f"Всего сообщений: {result['total_messages']}")
            print(f"Общее время: {result['total_time']:.4f} сек")
            print(f"Среднее время на сообщение: {result['avg_time_per_message']*1000:.4f} мс")
            print(f"Использование памяти: {result['memory_usage_mb']:.2f} МБ")
            print(f"Сообщений в секунду: {result['messages_per_second']:.2f}")
            print("-" * 40)
        
        print(f"Результаты сохранены в:\n{json_path}\n{csv_path}")
        
        # Проверяем, что производительность не деградирует слишком сильно с ростом объема данных
        ratios = []
        for i in range(1, len(scaling_results)):
            current = scaling_results[i]["avg_time_per_message"]
            previous = scaling_results[i-1]["avg_time_per_message"]
            ratio = current / previous if previous > 0 else 1
            ratios.append(ratio)
        
        avg_ratio = sum(ratios) / len(ratios) if ratios else 1
        assert avg_ratio < 2.0, f"Значительная деградация производительности с ростом объема данных: {avg_ratio:.2f}"


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 