#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для суммаризаторов.

Проверяет функциональность различных реализаций суммаризаторов,
используемых в системе памяти.
"""

import pytest
from typing import List, Optional, Any
from unittest.mock import MagicMock

from src.core.memory_system.memory_base import Message, UserMessage, AssistantMessage
from src.core.memory_system.summarizers import (
    create_simple_summarizer,
    create_keyword_summarizer,
    create_default_summarizer
)


class TestSimpleSummarizer:
    """Тесты для простого суммаризатора."""
    
    def test_simple_summarizer_creation(self):
        """Тест создания простого суммаризатора."""
        summarizer = create_simple_summarizer()
        
        assert callable(summarizer)
    
    def test_simple_summarizer_without_current_summary(self):
        """Тест простого суммаризатора без текущего резюме."""
        summarizer = create_simple_summarizer()
        
        messages = [
            UserMessage("Привет, как дела?", "user123"),
            AssistantMessage("Привет! У меня всё хорошо, спасибо.", "agent123"),
            UserMessage("Расскажи мне о погоде.", "user123")
        ]
        
        summary = summarizer(messages)
        
        assert "Новые сообщения:" in summary
        assert "user: Привет, как дела?" in summary
        assert "assistant: Привет! У меня всё" in summary
        assert "user: Расскажи мне о погод" in summary
    
    def test_simple_summarizer_with_current_summary(self):
        """Тест простого суммаризатора с текущим резюме."""
        summarizer = create_simple_summarizer()
        
        current_summary = "Предыдущее резюме диалога."
        
        messages = [
            UserMessage("Какая сегодня погода?", "user123"),
            AssistantMessage("Сегодня солнечно, температура +25°C.", "agent123")
        ]
        
        summary = summarizer(messages, current_summary)
        
        assert current_summary in summary
        assert "Новые сообщения:" in summary
        assert "user: Какая сегодня погод" in summary
        assert "assistant: Сегодня солнеч" in summary
    
    def test_simple_summarizer_with_long_messages(self):
        """Тест простого суммаризатора с длинными сообщениями."""
        summarizer = create_simple_summarizer()
        
        long_message = "Это очень длинное сообщение, которое должно быть сокращено в резюме. " * 10
        
        messages = [
            UserMessage(long_message, "user123")
        ]
        
        summary = summarizer(messages)
        
        assert "..." in summary  # Проверяем, что длинное сообщение сокращено
        assert len(summary.split("\n")[-1]) < len(long_message)


class TestKeywordSummarizer:
    """Тесты для суммаризатора на основе ключевых слов."""
    
    def test_keyword_summarizer_creation(self):
        """Тест создания суммаризатора на основе ключевых слов."""
        summarizer = create_keyword_summarizer()
        
        assert callable(summarizer)
    
    def test_keyword_summarizer_without_current_summary(self):
        """Тест суммаризатора на основе ключевых слов без текущего резюме."""
        summarizer = create_keyword_summarizer()
        
        messages = [
            UserMessage("Привет, расскажи мне о погоде в Москве сегодня.", "user123"),
            AssistantMessage("В Москве сегодня солнечно, температура +25°C.", "agent123"),
            UserMessage("А какая погода будет завтра в Москве?", "user123"),
            AssistantMessage("Завтра в Москве ожидается переменная облачность, температура +23°C.", "agent123")
        ]
        
        summary = summarizer(messages)
        
        assert "Ключевые темы обсуждения:" in summary
        assert "москве" in summary.lower()  # Ключевое слово должно быть в резюме
        assert "температура" in summary.lower()  # Ключевое слово должно быть в резюме
        assert "Диалог содержит 4 сообщений" in summary
        assert "Последнее сообщение" in summary
    
    def test_keyword_summarizer_with_current_summary(self):
        """Тест суммаризатора на основе ключевых слов с текущим резюме."""
        summarizer = create_keyword_summarizer()
        
        current_summary = "Предыдущее резюме диалога о погоде."
        
        messages = [
            UserMessage("Какая погода будет на выходных?", "user123"),
            AssistantMessage("На выходных ожидается солнечная погода, температура +27°C.", "agent123")
        ]
        
        summary = summarizer(messages, current_summary)
        
        assert current_summary in summary
        assert "Ключевые темы обсуждения:" in summary
        assert "погода" in summary  # Ключевое слово должно быть в резюме
        assert "выходных" in summary  # Ключевое слово должно быть в резюме
        assert "Диалог содержит 2 сообщений" in summary
    
    def test_keyword_summarizer_with_long_messages(self):
        """Тест суммаризатора на основе ключевых слов с длинными сообщениями."""
        summarizer = create_keyword_summarizer()
        
        long_message = "Погода сегодня отличная. Солнечно и тепло. " * 10
        
        messages = [
            UserMessage("Какая сегодня погода?", "user123"),
            AssistantMessage(long_message, "agent123")
        ]
        
        summary = summarizer(messages)
        
        assert "Ключевые темы обсуждения:" in summary
        assert "погода" in summary  # Ключевое слово должно быть в резюме
        assert "солнечно" in summary  # Ключевое слово должно быть в резюме
        assert "..." in summary  # Проверяем, что длинное сообщение сокращено


class TestDefaultSummarizer:
    """Тесты для суммаризатора по умолчанию."""
    
    def test_default_summarizer_creation(self):
        """Тест создания суммаризатора по умолчанию."""
        # Создаем мок для адаптера модели
        model_adapter = MagicMock()
        model_adapter.generate_text.return_value = "Резюме диалога: обсуждение погоды."
        
        summarizer = create_default_summarizer(model_adapter)
        
        assert callable(summarizer)
    
    def test_default_summarizer_without_current_summary(self):
        """Тест суммаризатора по умолчанию без текущего резюме."""
        # Создаем мок для адаптера модели
        model_adapter = MagicMock()
        model_adapter.generate_text.return_value = "Резюме диалога: обсуждение погоды."
        
        summarizer = create_default_summarizer(model_adapter)
        
        messages = [
            UserMessage("Привет, расскажи мне о погоде.", "user123"),
            AssistantMessage("Сегодня солнечно, температура +25°C.", "agent123")
        ]
        
        summary = summarizer(messages)
        
        # Проверяем, что модель была вызвана с правильными параметрами
        model_adapter.generate_text.assert_called_once()
        args, kwargs = model_adapter.generate_text.call_args
        
        assert "Пожалуйста, создай резюме следующего диалога" in kwargs["user_prompt"]
        assert "user: Привет, расскажи мне о погоде" in kwargs["user_prompt"]
        assert "assistant: Сегодня солнечно" in kwargs["user_prompt"]
        
        # Проверяем результат
        assert summary == "Резюме диалога: обсуждение погоды."
    
    def test_default_summarizer_with_current_summary(self):
        """Тест суммаризатора по умолчанию с текущим резюме."""
        # Создаем мок для адаптера модели
        model_adapter = MagicMock()
        model_adapter.generate_text.return_value = "Обновленное резюме диалога: обсуждение погоды и планов на выходные."
        
        summarizer = create_default_summarizer(model_adapter)
        
        current_summary = "Резюме диалога: обсуждение погоды."
        
        messages = [
            UserMessage("Какие у тебя планы на выходные?", "user123"),
            AssistantMessage("Планирую отдохнуть и погулять в парке.", "agent123")
        ]
        
        summary = summarizer(messages, current_summary)
        
        # Проверяем, что модель была вызвана с правильными параметрами
        model_adapter.generate_text.assert_called_once()
        args, kwargs = model_adapter.generate_text.call_args
        
        assert "Пожалуйста, создай резюме следующего диалога" in kwargs["user_prompt"]
        assert f"Текущее резюме диалога:\n{current_summary}" in kwargs["user_prompt"]
        assert "user: Какие у тебя планы на выходные" in kwargs["user_prompt"]
        assert "assistant: Планирую отдохнуть" in kwargs["user_prompt"]
        
        # Проверяем результат
        assert summary == "Обновленное резюме диалога: обсуждение погоды и планов на выходные."
    
    def test_default_summarizer_with_error(self):
        """Тест суммаризатора по умолчанию при возникновении ошибки."""
        # Создаем мок для адаптера модели, который вызывает исключение
        model_adapter = MagicMock()
        model_adapter.generate_text.side_effect = Exception("Ошибка генерации текста")
        
        summarizer = create_default_summarizer(model_adapter)
        
        current_summary = "Резюме диалога: обсуждение погоды."
        
        messages = [
            UserMessage("Какие у тебя планы на выходные?", "user123")
        ]
        
        # При ошибке должно вернуться текущее резюме
        summary = summarizer(messages, current_summary)
        assert summary == current_summary
        
        # Если текущего резюме нет, должна вернуться пустая строка
        summary = summarizer(messages)
        assert summary == "" 