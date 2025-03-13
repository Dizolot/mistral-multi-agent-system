#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пример интеграции системы памяти с менеджером агентов.

Демонстрирует, как система памяти может быть интегрирована с менеджером агентов
для обеспечения контекстного понимания запросов и долгосрочной памяти.
"""

import os
import logging
from typing import Dict, List, Any, Optional

from src.core.memory_system import (
    MemoryManager,
    create_simple_summarizer
)
from src.core.agent_manager.agent_manager import AgentManager
from src.core.agent_manager.general_agent import GeneralAgent


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MemoryEnabledAgentManager(AgentManager):
    """
    Расширение менеджера агентов с поддержкой системы памяти.
    
    Добавляет функциональность для работы с системой памяти,
    обеспечивая контекстное понимание запросов и долгосрочную память.
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        default_agent: Optional[str] = None,
        complexity_threshold: float = 0.5
    ):
        """
        Инициализация менеджера агентов с поддержкой памяти.
        
        Args:
            memory_manager: Менеджер памяти для хранения контекста
            default_agent: ID агента по умолчанию для простых запросов
            complexity_threshold: Порог сложности для переключения между режимами работы
        """
        super().__init__(default_agent, complexity_threshold)
        self.memory_manager = memory_manager
        self.logger.info("Менеджер агентов с поддержкой памяти инициализирован")
    
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
        
        # Анализируем сложность запроса
        complexity_level, complexity_score = self.analyze_query_complexity(query)
        
        # Выбираем режим работы
        operation_mode = self.select_operation_mode(complexity_level)
        
        # Обрабатываем запрос в соответствии с режимом
        if operation_mode == "single_agent":
            result = self._process_single_agent_mode(query, combined_context, complexity_level)
        else:
            result = self._process_multi_agent_mode(query, combined_context, complexity_level)
        
        # Добавляем ответ в память
        agent_id = result.get("agent_id", None)
        self.memory_manager.add_assistant_message(
            user_id,
            result["response"],
            agent_id=agent_id
        )
        
        # Сохраняем состояние памяти
        self.memory_manager.save_all()
        
        return result


def main():
    """Основная функция примера."""
    # Создаем директории для хранения данных
    os.makedirs("data/memory_integration", exist_ok=True)
    
    # Создаем менеджер памяти
    memory_manager = MemoryManager(
        storage_dir="data/memory_integration",
        summarizer=create_simple_summarizer()
    )
    
    # Создаем менеджер агентов с поддержкой памяти
    agent_manager = MemoryEnabledAgentManager(
        memory_manager=memory_manager
    )
    
    # Регистрируем агента
    general_agent = GeneralAgent(
        agent_id="general_agent",
        name="Общий агент",
        description="Агент для обработки общих запросов"
    )
    agent_manager.register_agent(general_agent)
    
    # Обрабатываем запросы пользователя
    user_id = "user456"
    
    # Первый запрос
    print("\nПервый запрос:")
    result1 = agent_manager.process_query(
        "Расскажи мне о мульти-агентных системах",
        user_id
    )
    print(f"Ответ: {result1['response']}")
    
    # Второй запрос (с контекстом из памяти)
    print("\nВторой запрос (с контекстом из памяти):")
    result2 = agent_manager.process_query(
        "Какие у них преимущества?",
        user_id
    )
    print(f"Ответ: {result2['response']}")
    
    # Третий запрос (с контекстом из памяти)
    print("\nТретий запрос (с контекстом из памяти):")
    result3 = agent_manager.process_query(
        "Приведи примеры таких систем",
        user_id
    )
    print(f"Ответ: {result3['response']}")
    
    # Получаем историю чата
    chat_history = memory_manager.get_chat_history(user_id)
    print("\nИстория чата:")
    for message in chat_history:
        print(f"{message.role}: {message.content[:50]}...")
    
    # Получаем контекст диалога
    context = memory_manager.get_context(user_id)
    print("\nКонтекст диалога:")
    print(f"Резюме: {context['summary']}")


if __name__ == "__main__":
    main() 