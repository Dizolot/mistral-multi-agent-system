#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль с реализациями суммаризаторов для системы памяти.

Предоставляет различные реализации функций для суммаризации сообщений
в системе памяти, используя различные модели и подходы.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime

from src.core.memory_system.memory_base import Message


def create_default_summarizer(
    model_adapter: Any,
    max_tokens: int = 500,
    temperature: float = 0.3
) -> Callable[[List[Message], Optional[str]], str]:
    """
    Создает функцию суммаризатора по умолчанию, использующую переданный адаптер модели.
    
    Args:
        model_adapter: Адаптер модели для генерации текста
        max_tokens: Максимальное количество токенов в резюме
        temperature: Температура генерации
        
    Returns:
        Callable: Функция суммаризатора
    """
    logger = logging.getLogger("default_summarizer")
    
    def summarizer(messages: List[Message], current_summary: Optional[str] = None) -> str:
        """
        Суммаризирует сообщения, используя переданный адаптер модели.
        
        Args:
            messages: Список сообщений для суммаризации
            current_summary: Текущее резюме (если есть)
            
        Returns:
            str: Обновленное резюме
        """
        # Форматируем сообщения для модели
        formatted_messages = []
        for message in messages:
            formatted_messages.append({
                "role": message.role,
                "content": message.content
            })
        
        # Создаем промпт для суммаризации
        system_prompt = """Ты - система суммаризации диалогов. Твоя задача - создать краткое и информативное резюме диалога.
Резюме должно включать:
1. Основные темы обсуждения
2. Ключевые вопросы и ответы
3. Важные решения или выводы
4. Нерешенные вопросы или задачи

Резюме должно быть кратким, но содержательным, и не должно превышать 500 слов.
"""
        
        user_prompt = "Пожалуйста, создай резюме следующего диалога:\n\n"
        
        # Добавляем текущее резюме, если оно есть
        if current_summary:
            user_prompt += f"Текущее резюме диалога:\n{current_summary}\n\n"
        
        user_prompt += "Новые сообщения для суммаризации:\n"
        for message in messages:
            user_prompt += f"{message.role}: {message.content}\n"
        
        # Генерируем резюме
        try:
            response = model_adapter.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Если есть текущее резюме, объединяем их
            if current_summary:
                logger.info("Обновлено существующее резюме")
                return response
            else:
                logger.info("Создано новое резюме")
                return response
        except Exception as e:
            logger.error(f"Ошибка при генерации резюме: {e}")
            # В случае ошибки возвращаем текущее резюме или пустую строку
            return current_summary or ""
    
    return summarizer


def create_simple_summarizer() -> Callable[[List[Message], Optional[str]], str]:
    """
    Создает простой суммаризатор, который просто объединяет сообщения без использования модели.
    
    Полезно для тестирования или когда нет доступа к модели.
    
    Returns:
        Callable: Функция суммаризатора
    """
    logger = logging.getLogger("simple_summarizer")
    
    def summarizer(messages: List[Message], current_summary: Optional[str] = None) -> str:
        """
        Простой суммаризатор, который объединяет сообщения.
        
        Args:
            messages: Список сообщений для суммаризации
            current_summary: Текущее резюме (если есть)
            
        Returns:
            str: Обновленное резюме
        """
        # Создаем простое резюме
        summary_lines = []
        
        # Добавляем текущее резюме, если оно есть
        if current_summary:
            summary_lines.append(current_summary)
        
        # Добавляем новые сообщения
        summary_lines.append("Новые сообщения:")
        for message in messages:
            # Сокращаем длинные сообщения
            content = message.content
            if len(content) > 100:
                content = content[:97] + "..."
            
            summary_lines.append(f"- {message.role}: {content}")
        
        logger.info("Создано простое резюме")
        return "\n".join(summary_lines)
    
    return summarizer


def create_keyword_summarizer() -> Callable[[List[Message], Optional[str]], str]:
    """
    Создает суммаризатор на основе ключевых слов.
    
    Извлекает ключевые слова из сообщений и создает резюме на их основе.
    
    Returns:
        Callable: Функция суммаризатора
    """
    logger = logging.getLogger("keyword_summarizer")
    
    def summarizer(messages: List[Message], current_summary: Optional[str] = None) -> str:
        """
        Суммаризатор на основе ключевых слов.
        
        Args:
            messages: Список сообщений для суммаризации
            current_summary: Текущее резюме (если есть)
            
        Returns:
            str: Обновленное резюме
        """
        # Извлекаем ключевые слова из сообщений
        all_text = " ".join([message.content for message in messages])
        words = all_text.split()
        
        # Простой алгоритм для выделения ключевых слов (частотный анализ)
        word_count = {}
        for word in words:
            word = word.lower().strip(".,!?;:()[]{}\"'")
            if len(word) > 3:  # Игнорируем короткие слова
                word_count[word] = word_count.get(word, 0) + 1
        
        # Сортируем слова по частоте
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        
        # Берем топ-10 ключевых слов
        top_keywords = [word for word, count in sorted_words[:10]]
        
        # Создаем резюме
        summary_lines = []
        
        # Добавляем текущее резюме, если оно есть
        if current_summary:
            summary_lines.append(current_summary)
        
        # Добавляем ключевые слова
        summary_lines.append("Ключевые темы обсуждения:")
        summary_lines.append(", ".join(top_keywords))
        
        # Добавляем краткое описание диалога
        summary_lines.append(f"\nДиалог содержит {len(messages)} сообщений.")
        
        # Добавляем последнее сообщение
        if messages:
            last_message = messages[-1]
            summary_lines.append(f"\nПоследнее сообщение ({last_message.role}):")
            
            # Сокращаем длинные сообщения
            content = last_message.content
            if len(content) > 100:
                content = content[:97] + "..."
            
            summary_lines.append(content)
        
        logger.info("Создано резюме на основе ключевых слов")
        return "\n".join(summary_lines)
    
    return summarizer 