#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Реализация общего (универсального) агента, способного обрабатывать 
широкий спектр запросов пользователей.
"""

import re
from typing import Dict, Any, Optional, List

from src.core.agent_manager.agent_base import AgentBase


class GeneralAgent(AgentBase):
    """
    Универсальный агент для обработки запросов общего характера.
    
    Является базовой реализацией агента, способного отвечать на широкий 
    спектр вопросов без узкой специализации.
    """
    
    def __init__(self, model_adapter=None):
        """
        Инициализация общего агента.
        
        Args:
            model_adapter: Адаптер модели для генерации ответов
        """
        super().__init__(
            agent_id="general",
            name="Общий ассистент",
            description="Универсальный ассистент для ответов на широкий спектр вопросов",
            keywords=["помощь", "информация", "вопрос", "что такое", "как"],
            capabilities=["ответы на общие вопросы", "предоставление информации", "помощь пользователю"]
        )
        # В реальной реализации здесь будет использоваться адаптер модели
        self.model_adapter = model_adapter
        
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Обработка запроса пользователя.
        
        Args:
            query: Текст запроса пользователя
            context: Контекст запроса (история диалога, настройки пользователя и т.д.)
            
        Returns:
            Dict[str, Any]: Результат обработки запроса
        """
        self.logger.info(f"Обработка запроса общим агентом: '{query[:50]}...'")
        
        # Проверяем наличие модели
        if self.model_adapter is None:
            # Временная заглушка для демонстрации
            if "привет" in query.lower():
                response = "Здравствуйте! Чем я могу вам помочь?"
            elif "как дела" in query.lower():
                response = "У меня всё хорошо, спасибо! Как я могу вам помочь сегодня?"
            elif "погода" in query.lower():
                response = "Я не могу предоставить информацию о погоде, так как не имею доступа к актуальным данным."
            else:
                response = f"Я получил ваш запрос: '{query}'. К сожалению, без подключения к модели я не могу дать полноценный ответ."
        else:
            # Формируем промпт для модели
            system_message = "Ты — полезный ассистент, который предоставляет точную и релевантную информацию пользователю."
            if context and "history" in context:
                # Добавляем историю диалога, если она есть
                prompt = self._format_history(context["history"])
                prompt += f"\nUser: {query}\nAssistant: "
            else:
                prompt = f"User: {query}\nAssistant: "
            
            # Вызываем модель через адаптер
            response = self.model_adapter.generate(
                system_message=system_message,
                prompt=prompt
            )
        
        # Формируем результат
        result = {
            "response": response,
            "agent_id": self.agent_id,
            "confidence": self.calculate_relevance(query)
        }
        
        return result
    
    def calculate_relevance(self, query: str) -> float:
        """
        Расчет релевантности агента для обработки данного запроса.
        
        Args:
            query: Текст запроса пользователя
            
        Returns:
            float: Оценка релевантности от 0.0 до 1.0
        """
        # Базовая релевантность для общего агента - он может обрабатывать любые запросы
        relevance = 0.5
        
        # Проверяем наличие ключевых слов
        for keyword in self.keywords:
            if keyword.lower() in query.lower():
                relevance += 0.1
                
        # Проверяем сложность запроса (простая эвристика)
        if len(query) < 20:
            relevance += 0.1  # Короткие запросы часто общего характера
            
        # Снижаем релевантность для специфических запросов, которые лучше обрабатываются другими агентами
        if re.search(r'(код|программ|скрипт|функци)', query.lower()):
            relevance -= 0.2  # Запросы на программирование
        if re.search(r'(математик|уравнени|вычисли|решить)', query.lower()):
            relevance -= 0.2  # Математические запросы
        
        # Ограничиваем релевантность диапазоном [0.3, 0.9]
        # Общий агент не должен иметь релевантность 0, так как он может обработать любой запрос
        # Но также не должен иметь релевантность 1.0, чтобы уступать специализированным агентам
        return max(0.3, min(relevance, 0.9))
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """
        Форматирование истории диалога для использования в промпте.
        
        Args:
            history: Список сообщений из истории диалога
            
        Returns:
            str: Отформатированная история диалога
        """
        formatted_history = ""
        for message in history:
            if message.get("role") == "user":
                formatted_history += f"User: {message.get('content', '')}\n"
            elif message.get("role") == "assistant":
                formatted_history += f"Assistant: {message.get('content', '')}\n"
        return formatted_history 