#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Интеграционные тесты для системы памяти и менеджера агентов.

Проверяет корректность интеграции системы памяти с менеджером агентов,
включая передачу контекста из памяти агентам и сохранение ответов агентов в памяти.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch

from src.core.memory_system import (
    MemoryManager,
    create_simple_summarizer
)
from src.core.agent_manager.agent_manager import AgentManager
from src.core.agent_manager.general_agent import GeneralAgent


class MemoryEnabledAgentManager:
    """
    Тестовая реализация менеджера агентов с поддержкой системы памяти.
    
    Аналогична реализации из примера agent_integration_example.py.
    """
    
    def __init__(
        self,
        memory_manager,
        agent_manager
    ):
        """
        Инициализация менеджера агентов с поддержкой памяти.
        
        Args:
            memory_manager: Менеджер памяти для хранения контекста
            agent_manager: Менеджер агентов для обработки запросов
        """
        self.memory_manager = memory_manager
        self.agent_manager = agent_manager
    
    def process_query(
        self,
        query,
        user_id,
        context=None
    ):
        """
        Обработка запроса пользователя с учетом контекста из памяти.
        
        Args:
            query: Запрос пользователя
            user_id: Идентификатор пользователя
            context: Дополнительный контекст (если есть)
            
        Returns:
            Dict: Результат обработки запроса
        """
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
        
        # Исправление: Корректное извлечение ответа из структуры результата, возвращаемой AgentManager
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


class TestMemoryAgentIntegration:
    """Интеграционные тесты для системы памяти и менеджера агентов."""
    
    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_agent(self):
        """Создает мок для агента."""
        agent = MagicMock(spec=GeneralAgent)
        agent.agent_id = "test_agent"
        agent.name = "Тестовый агент"
        agent.description = "Агент для тестирования"
        
        # Настраиваем поведение метода calculate_relevance
        agent.calculate_relevance.return_value = 0.8
        
        # Настраиваем поведение метода process_query
        def process_query(query, context=None):
            # Проверяем наличие контекста из памяти
            if context and "memory" in context:
                memory_context = context["memory"]
                if memory_context["summary"]:
                    return {
                        "response": f"Ответ с учетом резюме: {memory_context['summary'][:20]}...",
                        "agent_id": "test_agent"
                    }
                elif memory_context["recent_messages"]:
                    return {
                        "response": f"Ответ с учетом последних сообщений: {len(memory_context['recent_messages'])} сообщений",
                        "agent_id": "test_agent"
                    }
            
            # Если контекста нет, возвращаем простой ответ
            return {
                "response": f"Ответ на запрос: {query}",
                "agent_id": "test_agent"
            }
        
        agent.process_query.side_effect = process_query
        return agent
    
    @pytest.fixture
    def memory_enabled_agent_manager(self, temp_dir, mock_agent):
        """Создает менеджер агентов с поддержкой памяти."""
        # Создаем менеджер памяти
        memory_manager = MemoryManager(
            storage_dir=os.path.join(temp_dir, "memory_test"),
            summarizer=create_simple_summarizer(),
            default_summarize_threshold=3
        )
        
        # Создаем менеджер агентов
        agent_manager = AgentManager()
        agent_manager.register_agent(mock_agent)
        agent_manager.default_agent = mock_agent.agent_id
        
        # Создаем менеджер агентов с поддержкой памяти
        return MemoryEnabledAgentManager(memory_manager, agent_manager)
    
    def test_context_passing_to_agent(self, memory_enabled_agent_manager):
        """Тест передачи контекста из памяти агенту."""
        user_id = "test_user"
        
        # Очищаем память пользователя перед тестом
        memory_enabled_agent_manager.memory_manager.clear_memory(user_id)
        
        # Первый запрос (без контекста)
        result1 = memory_enabled_agent_manager.process_query(
            "Привет, как дела?",
            user_id
        )
        
        assert "result" in result1
        assert "response" in result1["result"]
        # При первом запросе уже добавлено сообщение в память, поэтому агент получает контекст
        assert ("Ответ с учетом последних сообщений" in result1["result"]["response"] or 
                "Ответ с учетом резюме" in result1["result"]["response"])
        
        # Второй запрос (с контекстом из последних сообщений)
        result2 = memory_enabled_agent_manager.process_query(
            "Что ты умеешь?",
            user_id
        )
        
        assert "result" in result2
        assert "response" in result2["result"]
        assert ("Ответ с учетом последних сообщений" in result2["result"]["response"] or 
                "Ответ с учетом резюме" in result2["result"]["response"])
        
        # Добавляем еще запросы для создания резюме
        memory_enabled_agent_manager.process_query("Расскажи о погоде", user_id)
        memory_enabled_agent_manager.process_query("Какой сегодня день?", user_id)
        
        # Запрос с резюме
        result5 = memory_enabled_agent_manager.process_query(
            "Что мы обсуждали?",
            user_id
        )
        
        assert "result" in result5
        assert "response" in result5["result"]
        assert "Ответ с учетом резюме:" in result5["result"]["response"]
    
    def test_agent_responses_saving(self, memory_enabled_agent_manager):
        """Тест сохранения ответов агента в памяти."""
        user_id = "test_user"
        
        # Очищаем память пользователя перед тестом
        memory_enabled_agent_manager.memory_manager.clear_memory(user_id)
        
        # Отправляем запрос
        result = memory_enabled_agent_manager.process_query(
            "Привет, как дела?",
            user_id
        )
        
        # Проверяем, что ответ агента сохранен в памяти
        memory_manager = memory_enabled_agent_manager.memory_manager
        chat_history = memory_manager.get_chat_history(user_id)
        
        assert len(chat_history) == 2  # Запрос пользователя и ответ агента
        assert chat_history[0].role == "user"
        assert chat_history[0].content == "Привет, как дела?"
        assert chat_history[1].role == "assistant"
        # Ответ должен соответствовать реальному ответу от агента
        assert "Ответ с учетом последних сообщений" in chat_history[1].content
        assert chat_history[1].metadata["agent_id"] == "test_agent"
    
    def test_memory_persistence(self, memory_enabled_agent_manager, temp_dir):
        """Тест сохранения и загрузки состояния памяти."""
        user_id = "test_user"
        
        # Отправляем запросы
        memory_enabled_agent_manager.process_query("Привет", user_id)
        memory_enabled_agent_manager.process_query("Как дела?", user_id)
        
        # Проверяем, что файлы памяти созданы
        memory_dir = os.path.join(temp_dir, "memory_test")
        assert os.path.exists(os.path.join(memory_dir, f"{user_id}_buffer.json"))
        assert os.path.exists(os.path.join(memory_dir, f"{user_id}_summary.json"))
        
        # Создаем новый менеджер памяти с тем же путем хранения
        new_memory_manager = MemoryManager(
            storage_dir=os.path.join(temp_dir, "memory_test"),
            summarizer=create_simple_summarizer()
        )
        
        # Получаем историю чата из нового менеджера
        chat_history = new_memory_manager.get_chat_history(user_id)
        
        # Проверяем, что история загружена корректно
        assert len(chat_history) == 4  # 2 запроса и 2 ответа
        assert chat_history[0].role == "user"
        assert chat_history[0].content == "Привет"
        assert chat_history[1].role == "assistant"
        assert chat_history[2].role == "user"
        assert chat_history[2].content == "Как дела?"
        assert chat_history[3].role == "assistant"
    
    def test_context_format(self, memory_enabled_agent_manager):
        """Тест формата контекста, передаваемого агенту."""
        user_id = "test_user"
        
        # Отправляем запросы для создания контекста
        memory_enabled_agent_manager.process_query("Привет", user_id)
        memory_enabled_agent_manager.process_query("Как дела?", user_id)
        
        # Получаем контекст из памяти
        memory_manager = memory_enabled_agent_manager.memory_manager
        context = memory_manager.get_context(user_id)
        
        # Проверяем формат контекста
        assert "summary" in context
        assert "recent_messages" in context
        assert isinstance(context["summary"], str)
        assert isinstance(context["recent_messages"], list)
        
        # Проверяем формат сообщений в контексте
        for message_dict in context["recent_messages"]:
            assert "content" in message_dict
            assert "role" in message_dict
            assert "timestamp" in message_dict
            assert "metadata" in message_dict 