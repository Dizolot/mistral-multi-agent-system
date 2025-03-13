#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль содержит реализацию менеджера агентов - центрального компонента 
для координации работы агентов и маршрутизации запросов между ними.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple

from src.core.agent_manager.agent_base import AgentBase


class OperationMode(Enum):
    """Режимы работы менеджера агентов."""
    SINGLE_AGENT = "single_agent"  # Режим одного агента для простых запросов
    MULTI_AGENT = "multi_agent"    # Режим нескольких агентов для сложных запросов


class ComplexityLevel(Enum):
    """Уровни сложности запросов."""
    LOW = "low"          # Низкая сложность - простой запрос
    MEDIUM = "medium"    # Средняя сложность - требует некоторой декомпозиции
    HIGH = "high"        # Высокая сложность - требует полной декомпозиции и координации


class AgentManager:
    """
    Менеджер агентов - центральный компонент для координации агентов и маршрутизации запросов.
    
    Менеджер отвечает за:
    1. Регистрацию и управление агентами
    2. Анализ сложности запросов
    3. Выбор оптимального режима работы (одноагентный или мульти-агентный)
    4. Маршрутизацию запросов к соответствующим агентам
    5. Сбор и обработку результатов работы агентов
    """
    
    def __init__(self, default_agent: Optional[str] = None, complexity_threshold: float = 0.5):
        """
        Инициализация менеджера агентов.
        
        Args:
            default_agent: ID агента по умолчанию для простых запросов
            complexity_threshold: Порог сложности для переключения между режимами работы
        """
        self.logger = logging.getLogger(__name__)
        self.agents: Dict[str, AgentBase] = {}
        self.default_agent_id = default_agent
        self.complexity_threshold = complexity_threshold
        self.logger.info("AgentManager инициализирован")
    
    def register_agent(self, agent: AgentBase) -> None:
        """
        Регистрация нового агента в системе.
        
        Args:
            agent: Объект агента для регистрации
        """
        if agent.agent_id in self.agents:
            self.logger.warning(f"Агент с ID {agent.agent_id} уже зарегистрирован, перезаписываем")
        
        self.agents[agent.agent_id] = agent
        self.logger.info(f"Агент {agent.agent_id} успешно зарегистрирован")
        
        # Если это первый зарегистрированный агент и нет агента по умолчанию, 
        # устанавливаем его как агента по умолчанию
        if not self.default_agent_id and len(self.agents) == 1:
            self.default_agent_id = agent.agent_id
            self.logger.info(f"Агент {agent.agent_id} установлен как агент по умолчанию")
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Удаление агента из системы.
        
        Args:
            agent_id: Идентификатор агента для удаления
            
        Returns:
            bool: True, если агент был успешно удален, False в противном случае
        """
        if agent_id not in self.agents:
            self.logger.warning(f"Агент с ID {agent_id} не найден")
            return False
        
        if agent_id == self.default_agent_id:
            self.logger.warning(f"Удаление агента по умолчанию {agent_id}")
            self.default_agent_id = next(iter(self.agents.keys())) if self.agents else None
        
        del self.agents[agent_id]
        self.logger.info(f"Агент {agent_id} успешно удален")
        return True
    
    def analyze_query_complexity(self, query: str) -> Tuple[ComplexityLevel, float]:
        """
        Анализ сложности запроса для определения оптимального режима работы.
        
        Args:
            query: Текст запроса пользователя
            
        Returns:
            Tuple[ComplexityLevel, float]: Уровень сложности и численное значение сложности
        """
        # В будущем здесь будет более сложная логика анализа запроса,
        # возможно с использованием ML-модели
        
        # Простая эвристика на основе длины запроса и наличия специфических ключевых слов
        complexity_score = min(1.0, len(query) / 1000)  # Базовая оценка на основе длины
        
        # Увеличиваем сложность при наличии определенных паттернов
        if "объясни" in query.lower() or "почему" in query.lower():
            complexity_score += 0.1
        if "сравни" in query.lower() or "различия" in query.lower():
            complexity_score += 0.2
        if "код" in query.lower() or "программ" in query.lower():
            complexity_score += 0.15
        
        # Определяем уровень сложности на основе численной оценки
        if complexity_score < 0.3:
            level = ComplexityLevel.LOW
        elif complexity_score < 0.6:
            level = ComplexityLevel.MEDIUM
        else:
            level = ComplexityLevel.HIGH
        
        self.logger.debug(f"Запрос '{query[:50]}...' имеет сложность {complexity_score:.2f} ({level.value})")
        return level, complexity_score
    
    def select_operation_mode(self, complexity_level: ComplexityLevel) -> OperationMode:
        """
        Выбор режима работы на основе уровня сложности запроса.
        
        Args:
            complexity_level: Уровень сложности запроса
            
        Returns:
            OperationMode: Выбранный режим работы
        """
        if complexity_level in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM]:
            return OperationMode.SINGLE_AGENT
        else:
            return OperationMode.MULTI_AGENT
    
    def select_agent_for_query(self, query: str) -> str:
        """
        Выбор оптимального агента для обработки запроса.
        
        Args:
            query: Текст запроса пользователя
            
        Returns:
            str: ID выбранного агента
        """
        # В будущем здесь будет более сложная логика выбора агента,
        # возможно с использованием ML-модели и анализа семантики запроса
        
        # Временная простая реализация
        best_agent_id = self.default_agent_id
        best_score = 0.0
        
        for agent_id, agent in self.agents.items():
            score = agent.calculate_relevance(query)
            if score > best_score:
                best_score = score
                best_agent_id = agent_id
                
        self.logger.debug(f"Для запроса '{query[:50]}...' выбран агент {best_agent_id} (score: {best_score:.2f})")
        return best_agent_id
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Обработка запроса пользователя.
        
        Анализирует запрос, выбирает режим работы и маршрутизирует запрос 
        к соответствующему агенту или группе агентов.
        
        Args:
            query: Текст запроса пользователя
            context: Контекст запроса (история диалога, настройки пользователя и т.д.)
            
        Returns:
            Dict[str, Any]: Результат обработки запроса
        """
        if not self.agents:
            error_msg = "Нет зарегистрированных агентов для обработки запроса"
            self.logger.error(error_msg)
            return {"error": error_msg, "success": False}
        
        if not self.default_agent_id:
            self.default_agent_id = next(iter(self.agents.keys()))
            self.logger.warning(f"Агент по умолчанию не установлен, используется {self.default_agent_id}")
        
        # Анализируем сложность запроса
        complexity_level, complexity_score = self.analyze_query_complexity(query)
        
        # Выбираем режим работы
        operation_mode = self.select_operation_mode(complexity_level)
        
        # Обрабатываем запрос в соответствии с выбранным режимом
        if operation_mode == OperationMode.SINGLE_AGENT:
            return self._process_single_agent_mode(query, context, complexity_level)
        else:
            return self._process_multi_agent_mode(query, context, complexity_level)
    
    def _process_single_agent_mode(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]], 
        complexity_level: ComplexityLevel
    ) -> Dict[str, Any]:
        """
        Обработка запроса в режиме одного агента.
        
        Args:
            query: Текст запроса пользователя
            context: Контекст запроса
            complexity_level: Уровень сложности запроса
            
        Returns:
            Dict[str, Any]: Результат обработки запроса
        """
        self.logger.info(f"Обработка запроса в режиме одного агента (сложность: {complexity_level.value})")
        
        # Выбираем оптимального агента для запроса
        agent_id = self.select_agent_for_query(query)
        
        if agent_id not in self.agents:
            error_msg = f"Агент с ID {agent_id} не найден"
            self.logger.error(error_msg)
            return {"error": error_msg, "success": False}
        
        agent = self.agents[agent_id]
        
        # Обрабатываем запрос выбранным агентом
        try:
            result = agent.process_query(query, context)
            return {
                "success": True,
                "agent_id": agent_id,
                "operation_mode": OperationMode.SINGLE_AGENT.value,
                "complexity_level": complexity_level.value,
                "result": result
            }
        except Exception as e:
            error_msg = f"Ошибка при обработке запроса агентом {agent_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"error": error_msg, "success": False}
    
    def _process_multi_agent_mode(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]], 
        complexity_level: ComplexityLevel
    ) -> Dict[str, Any]:
        """
        Обработка запроса в режиме нескольких агентов.
        
        Декомпозирует запрос на подзадачи, распределяет их между агентами и 
        объединяет результаты работы.
        
        Args:
            query: Текст запроса пользователя
            context: Контекст запроса
            complexity_level: Уровень сложности запроса
            
        Returns:
            Dict[str, Any]: Результат обработки запроса
        """
        self.logger.info(f"Обработка запроса в режиме нескольких агентов (сложность: {complexity_level.value})")
        
        # TODO: В будущих версиях здесь будет реализована декомпозиция запроса
        # и распределение подзадач между агентами
        
        # Пока используем временное решение на основе общего агента
        return self._process_single_agent_mode(query, context, complexity_level)
    
    def get_registered_agents(self) -> List[Dict[str, Any]]:
        """
        Получение списка зарегистрированных агентов.
        
        Returns:
            List[Dict[str, Any]]: Список с информацией о зарегистрированных агентах
        """
        return [
            {
                "agent_id": agent_id,
                "name": agent.name,
                "description": agent.description,
                "is_default": agent_id == self.default_agent_id
            }
            for agent_id, agent in self.agents.items()
        ] 