"""
Модуль для интеграции системы памяти с системой аналитики агентов.

Этот модуль предоставляет инструменты для передачи данных из истории диалогов 
в систему аналитики агентов для последующего анализа и улучшения.
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

from multi_agent_system.memory.conversation_memory import ConversationMemoryManager
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector
from multi_agent_system.logger import get_logger

# Настройка логирования
logger = get_logger(__name__)

class MemoryAnalyticsIntegration:
    """
    Класс для интеграции между системой памяти и системой аналитики агентов.
    
    Предоставляет методы для преобразования истории диалогов в формат, 
    подходящий для анализа, и отправки этих данных в систему аналитики.
    """
    
    def __init__(
        self,
        memory_manager: ConversationMemoryManager,
        data_collector: AgentDataCollector
    ):
        """
        Инициализирует интеграцию между памятью и аналитикой.
        
        Args:
            memory_manager: Менеджер памяти для доступа к истории диалогов
            data_collector: Коллектор данных для записи в аналитику
        """
        self.memory_manager = memory_manager
        self.data_collector = data_collector
        logger.info("Интеграция памяти и аналитики инициализирована")
    
    def process_conversation_history(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        process_all: bool = False,
        last_n_interactions: Optional[int] = None
    ) -> int:
        """
        Обрабатывает историю разговора пользователя и передает её в систему аналитики.
        
        Args:
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии (если None, генерируется новый)
            process_all: Обрабатывать всю историю или только новые сообщения
            last_n_interactions: Количество последних взаимодействий для обработки
            
        Returns:
            Количество обработанных взаимодействий
        """
        # Создаем или используем переданный идентификатор сессии
        session_id = session_id or str(uuid.uuid4())
        
        # Получаем историю диалога
        chat_history = self.memory_manager.get_chat_history(user_id)
        
        # Если указано количество последних взаимодействий, ограничиваем историю
        if last_n_interactions is not None and not process_all:
            chat_history = chat_history[-last_n_interactions*2:]
        
        # Группируем сообщения в пары "запрос-ответ"
        interactions = []
        current_request = None
        
        for i, message in enumerate(chat_history):
            # Пропускаем системные сообщения
            if isinstance(message, SystemMessage):
                continue
            
            # Обрабатываем сообщение пользователя (запрос)
            if isinstance(message, HumanMessage):
                # Если у нас уже есть запрос без ответа, сохраняем его как отдельное взаимодействие
                if current_request is not None:
                    interactions.append({
                        "request": current_request.content,
                        "response": "",
                        "timestamp": datetime.now().isoformat(),
                        "is_complete": False
                    })
                
                # Сохраняем текущий запрос
                current_request = message
            
            # Обрабатываем сообщение агента (ответ)
            elif isinstance(message, AIMessage) and current_request is not None:
                # Определяем имя агента, если есть дополнительные метаданные
                agent_name = "default_agent"
                if hasattr(message, "additional_kwargs") and "agent_name" in message.additional_kwargs:
                    agent_name = message.additional_kwargs["agent_name"]
                
                # Создаем полное взаимодействие "запрос-ответ"
                interactions.append({
                    "request": current_request.content,
                    "response": message.content,
                    "agent_name": agent_name,
                    "timestamp": datetime.now().isoformat(),
                    "is_complete": True
                })
                
                # Сбрасываем текущий запрос
                current_request = None
        
        # Если остался необработанный запрос, добавляем его
        if current_request is not None:
            interactions.append({
                "request": current_request.content,
                "response": "",
                "timestamp": datetime.now().isoformat(),
                "is_complete": False
            })
        
        # Записываем взаимодействия в аналитику
        processed_count = 0
        for interaction in interactions:
            if interaction["is_complete"]:
                success = self.data_collector.record_interaction(
                    user_id=user_id,
                    session_id=session_id,
                    agent_name=interaction.get("agent_name", "default_agent"),
                    request=interaction["request"],
                    response=interaction["response"],
                    processing_time=0.0,  # У нас нет данных о времени обработки
                    is_successful=True,
                    metadata={"source": "conversation_memory"}
                )
                
                if success:
                    processed_count += 1
        
        logger.info(f"Обработано {processed_count} взаимодействий из истории диалога пользователя {user_id}")
        return processed_count
    
    def process_all_users(
        self,
        last_n_interactions: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Обрабатывает историю разговоров всех пользователей.
        
        Args:
            last_n_interactions: Количество последних взаимодействий для обработки
            
        Returns:
            Словарь с количеством обработанных взаимодействий для каждого пользователя
        """
        users = self.memory_manager.get_all_users()
        results = {}
        
        for user_id in users:
            session_id = str(uuid.uuid4())
            processed_count = self.process_conversation_history(
                user_id=user_id,
                session_id=session_id,
                last_n_interactions=last_n_interactions
            )
            results[user_id] = processed_count
        
        total_processed = sum(results.values())
        logger.info(f"Обработано всего {total_processed} взаимодействий для {len(users)} пользователей")
        return results
    
    def analyze_user_conversation_patterns(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Анализирует паттерны разговора пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Словарь с результатами анализа
        """
        # Получаем всю историю диалога пользователя
        chat_history = self.memory_manager.get_chat_history(user_id)
        
        # Инициализируем статистику
        stats = {
            "total_messages": len(chat_history),
            "user_messages": 0,
            "ai_messages": 0,
            "system_messages": 0,
            "avg_user_message_length": 0,
            "avg_ai_message_length": 0,
            "topic_distribution": {}
        }
        
        # Анализируем каждое сообщение
        user_message_lengths = []
        ai_message_lengths = []
        
        for message in chat_history:
            if isinstance(message, HumanMessage):
                stats["user_messages"] += 1
                user_message_lengths.append(len(message.content))
                
                # TODO: Дополнительный анализ тем может быть реализован здесь
                
            elif isinstance(message, AIMessage):
                stats["ai_messages"] += 1
                ai_message_lengths.append(len(message.content))
                
            elif isinstance(message, SystemMessage):
                stats["system_messages"] += 1
        
        # Вычисляем средние длины сообщений
        if user_message_lengths:
            stats["avg_user_message_length"] = sum(user_message_lengths) / len(user_message_lengths)
        
        if ai_message_lengths:
            stats["avg_ai_message_length"] = sum(ai_message_lengths) / len(ai_message_lengths)
        
        return stats


def extract_performance_metrics_from_memory(
    memory_manager: ConversationMemoryManager,
    data_collector: AgentDataCollector
) -> Dict[str, Any]:
    """
    Извлекает метрики производительности из истории диалогов и отправляет их в аналитику.
    
    Args:
        memory_manager: Менеджер памяти
        data_collector: Коллектор данных аналитики
        
    Returns:
        Словарь с агрегированными метриками
    """
    users = memory_manager.get_all_users()
    
    # Инициализируем агрегированные метрики
    metrics = {
        "total_conversations": len(users),
        "total_interactions": 0,
        "agent_distribution": {},
        "avg_user_satisfaction": 0
    }
    
    integration = MemoryAnalyticsIntegration(memory_manager, data_collector)
    
    # Обрабатываем историю всех пользователей
    processed_counts = integration.process_all_users()
    metrics["total_interactions"] = sum(processed_counts.values())
    
    # Получаем распределение использования агентов
    agent_interactions = data_collector.get_agent_interactions()
    agent_counts = {}
    
    for interaction in agent_interactions:
        agent_name = interaction.get("agent_name", "unknown")
        agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
    
    metrics["agent_distribution"] = agent_counts
    
    # Вычисляем дополнительные метрики на основе данных
    # TODO: Добавить расчет удовлетворенности пользователей
    
    logger.info(f"Извлечены метрики из памяти: {metrics}")
    return metrics 