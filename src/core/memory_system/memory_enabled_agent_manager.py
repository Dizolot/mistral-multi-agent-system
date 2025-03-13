#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль содержит реализацию менеджера агентов с поддержкой системы памяти.

Обеспечивает интеграцию системы памяти с менеджером агентов, позволяя
агентам использовать контекст из предыдущих взаимодействий при обработке запросов.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from src.core.agent_manager.agent_manager import AgentManager, ComplexityLevel, OperationMode
from src.core.memory_system.memory_manager import MemoryManager


class MemoryEnabledAgentManager:
    """
    Менеджер агентов с поддержкой системы памяти.
    
    Расширяет функциональность менеджера агентов, добавляя интеграцию
    с системой памяти для сохранения контекста взаимодействий.
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        agent_manager: Optional[AgentManager] = None,
        default_agent: Optional[str] = None,
        complexity_threshold: float = 0.5
    ):
        """
        Инициализация менеджера агентов с поддержкой памяти.
        
        Args:
            memory_manager: Менеджер памяти для хранения контекста
            agent_manager: Существующий менеджер агентов (если есть)
            default_agent: ID агента по умолчанию для простых запросов
            complexity_threshold: Порог сложности для переключения между режимами работы
        """
        self.logger = logging.getLogger(__name__)
        self.memory_manager = memory_manager
        
        # Создаем новый менеджер агентов, если не предоставлен существующий
        self.agent_manager = agent_manager or AgentManager(
            default_agent=default_agent,
            complexity_threshold=complexity_threshold
        )
        
        self.logger.info("Менеджер агентов с поддержкой памяти инициализирован")
    
    def register_agent(self, agent):
        """
        Регистрирует агента в менеджере.
        
        Args:
            agent: Агент для регистрации
        """
        self.agent_manager.register_agent(agent)
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Отменяет регистрацию агента.
        
        Args:
            agent_id: ID агента для отмены регистрации
            
        Returns:
            bool: True, если агент был удален, иначе False
        """
        return self.agent_manager.unregister_agent(agent_id)
    
    def process_query(
        self,
        query: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обработка запроса пользователя с учетом контекста из памяти.
        
        Args:
            query: Запрос пользователя
            user_id: Идентификатор пользователя
            context: Дополнительный контекст (если есть)
            
        Returns:
            Dict[str, Any]: Результат обработки запроса
        """
        # Добавляем сообщение пользователя в память
        self.memory_manager.add_user_message(user_id, query)
        
        # Получаем контекст из памяти
        memory_context = self.memory_manager.get_context(user_id)
        
        # Объединяем контексты
        combined_context = context or {}
        combined_context["memory"] = memory_context
        
        # Обрабатываем запрос с учетом контекста
        self.logger.debug(f"Обработка запроса от пользователя {user_id}: {query}")
        result = self.agent_manager.process_query(query, combined_context)
        
        # Добавляем ответ в память
        agent_id = result.get("agent_id", None)
        response_text = ""
        
        # Извлекаем текст ответа из результата
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
    
    def analyze_query_complexity(self, query: str) -> Tuple[ComplexityLevel, float]:
        """
        Анализирует сложность запроса.
        
        Args:
            query: Текст запроса
            
        Returns:
            Tuple[ComplexityLevel, float]: Уровень сложности и числовая оценка
        """
        return self.agent_manager.analyze_query_complexity(query)
    
    def select_operation_mode(self, complexity_level: ComplexityLevel) -> OperationMode:
        """
        Выбирает режим работы в зависимости от сложности запроса.
        
        Args:
            complexity_level: Уровень сложности запроса
            
        Returns:
            OperationMode: Выбранный режим работы
        """
        return self.agent_manager.select_operation_mode(complexity_level)
    
    def select_agent_for_query(self, query: str) -> str:
        """
        Выбирает наиболее подходящего агента для обработки запроса.
        
        Args:
            query: Текст запроса
            
        Returns:
            str: ID выбранного агента
        """
        return self.agent_manager.select_agent_for_query(query)
    
    def get_registered_agents(self) -> List[Dict[str, Any]]:
        """
        Возвращает список зарегистрированных агентов.
        
        Returns:
            List[Dict[str, Any]]: Список зарегистрированных агентов
        """
        return self.agent_manager.get_registered_agents()
    
    def get_chat_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получает историю чата для пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            limit: Максимальное количество сообщений
            
        Returns:
            List[Dict[str, Any]]: История чата
        """
        return self.memory_manager.get_chat_history(user_id, limit)
    
    def clear_memory(self, user_id: str) -> None:
        """
        Очищает память для конкретного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
        """
        self.memory_manager.clear_memory(user_id)
    
    def add_system_message(self, user_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Добавляет системное сообщение в память.
        
        Args:
            user_id: Идентификатор пользователя
            content: Содержимое сообщения
            metadata: Дополнительные метаданные
        """
        self.memory_manager.add_system_message(user_id, content, metadata)
    
    def save_all(self) -> None:
        """Сохраняет все данные памяти."""
        self.memory_manager.save_all() 