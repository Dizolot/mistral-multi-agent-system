#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль с базовым классом Agent, определяющим интерфейс для всех агентов в системе.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class AgentBase(ABC):
    """
    Абстрактный базовый класс для всех агентов в системе.
    
    Определяет общий интерфейс, который должны реализовать все агенты.
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        keywords: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None
    ):
        """
        Инициализация базового агента.
        
        Args:
            agent_id: Уникальный идентификатор агента
            name: Человекочитаемое имя агента
            description: Описание агента, его возможностей и области применения
            keywords: Список ключевых слов для определения релевантности запросов
            capabilities: Список возможностей агента
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.keywords = keywords or []
        self.capabilities = capabilities or []
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.logger.info(f"Агент {name} ({agent_id}) инициализирован")
    
    @abstractmethod
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Обработка запроса пользователя.
        
        Args:
            query: Текст запроса пользователя
            context: Контекст запроса (история диалога, настройки пользователя и т.д.)
            
        Returns:
            Any: Результат обработки запроса
        """
        pass
    
    @abstractmethod
    def calculate_relevance(self, query: str) -> float:
        """
        Расчет релевантности агента для обработки данного запроса.
        
        Args:
            query: Текст запроса пользователя
            
        Returns:
            float: Оценка релевантности от 0.0 до 1.0
        """
        pass
    
    def update(self, feedback: Dict[str, Any]) -> bool:
        """
        Обновление агента на основе полученной обратной связи.
        
        Args:
            feedback: Словарь с обратной связью о работе агента
            
        Returns:
            bool: True, если обновление успешно, False в противном случае
        """
        # По умолчанию обновление не поддерживается, но наследники могут переопределить
        self.logger.warning(f"Агент {self.name} не поддерживает обновление на основе обратной связи")
        return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        Получение информации об агенте.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об агенте
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "capabilities": self.capabilities
        }
    
    def __str__(self) -> str:
        """
        Строковое представление агента.
        
        Returns:
            str: Строка с информацией об агенте
        """
        return f"{self.name} ({self.agent_id}): {self.description}"
    
    def __repr__(self) -> str:
        """Представление агента для отладки."""
        return f"<Agent: {self.agent_id}>" 