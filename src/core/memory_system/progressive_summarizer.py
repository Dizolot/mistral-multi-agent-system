#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для прогрессивной суммаризации сообщений.

Предоставляет реализацию прогрессивной суммаризации для эффективного
сжатия длинных диалогов с сохранением важной информации.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Type, Callable
from datetime import datetime

from src.core.memory_system.memory_base import Message


class ProgressiveSummarizer:
    """
    Реализация прогрессивной суммаризации для сообщений.
    
    Прогрессивная суммаризация - это метод, при котором текст сжимается
    в несколько этапов, каждый раз сохраняя все более важную информацию.
    """
    
    def __init__(
        self,
        model_adapter: Any,
        max_tokens_per_level: List[int] = [1000, 500, 250, 100],
        temperature: float = 0.3,
        cache_dir: Optional[str] = None
    ):
        """
        Инициализация прогрессивного суммаризатора.
        
        Args:
            model_adapter: Адаптер модели для генерации текста
            max_tokens_per_level: Максимальное количество токенов для каждого уровня суммаризации
            temperature: Температура генерации
            cache_dir: Директория для кэширования результатов
        """
        self.model_adapter = model_adapter
        self.max_tokens_per_level = max_tokens_per_level
        self.temperature = temperature
        self.cache_dir = cache_dir
        
        # Создание директории для кэширования, если указана
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        
        # Инициализация кэша
        self.cache: Dict[str, Dict[int, str]] = {}
        
        # Инициализация логгера
        self.logger = logging.getLogger("progressive_summarizer")
    
    def _get_cache_key(self, messages: List[Message]) -> str:
        """
        Генерирует ключ для кэширования на основе сообщений.
        
        Args:
            messages: Список сообщений
            
        Returns:
            str: Ключ для кэширования
        """
        # Простой хэш на основе содержимого и времени сообщений
        message_hashes = []
        for message in messages:
            content_hash = hash(message.content)
            time_hash = hash(message.timestamp.isoformat())
            message_hashes.append(f"{content_hash}_{time_hash}")
        
        return "_".join(message_hashes)
    
    def _load_cache(self, cache_key: str) -> Optional[Dict[int, str]]:
        """
        Загружает кэш для указанного ключа.
        
        Args:
            cache_key: Ключ для кэширования
            
        Returns:
            Optional[Dict[int, str]]: Кэш для указанного ключа или None
        """
        # Проверка наличия кэша в памяти
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Проверка наличия кэша на диске
        if self.cache_dir:
            cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)
                    
                    # Преобразование ключей из строк в числа
                    cache = {int(k): v for k, v in cache_data.items()}
                    
                    # Сохранение в памяти
                    self.cache[cache_key] = cache
                    
                    return cache
                except Exception as e:
                    self.logger.error(f"Ошибка при загрузке кэша: {e}")
        
        return None
    
    def _save_cache(self, cache_key: str, cache: Dict[int, str]) -> None:
        """
        Сохраняет кэш для указанного ключа.
        
        Args:
            cache_key: Ключ для кэширования
            cache: Кэш для сохранения
        """
        # Сохранение в памяти
        self.cache[cache_key] = cache
        
        # Сохранение на диск
        if self.cache_dir:
            cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.logger.error(f"Ошибка при сохранении кэша: {e}")
    
    def _format_messages_for_summarization(self, messages: List[Message]) -> str:
        """
        Форматирует сообщения для суммаризации.
        
        Args:
            messages: Список сообщений
            
        Returns:
            str: Отформатированный текст
        """
        formatted_text = ""
        
        for message in messages:
            role_prefix = {
                "user": "Пользователь",
                "assistant": "Ассистент",
                "system": "Система"
            }.get(message.role, "Неизвестный")
            
            formatted_text += f"{role_prefix}: {message.content}\n\n"
        
        return formatted_text
    
    def _summarize_text(self, text: str, max_tokens: int) -> str:
        """
        Суммаризирует текст с использованием модели.
        
        Args:
            text: Текст для суммаризации
            max_tokens: Максимальное количество токенов в резюме
            
        Returns:
            str: Суммаризированный текст
        """
        prompt = f"""Суммаризируй следующий диалог, сохраняя важную информацию и контекст. 
Резюме должно быть информативным и содержать ключевые моменты диалога.
Максимальная длина резюме: {max_tokens} токенов.

Диалог:
{text}

Резюме:"""
        
        try:
            response = self.model_adapter.generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=self.temperature
            )
            
            return response.strip()
        except Exception as e:
            self.logger.error(f"Ошибка при суммаризации: {e}")
            return f"Ошибка при суммаризации: {e}"
    
    def summarize(
        self,
        messages: List[Message],
        current_summary: Optional[str] = None,
        level: int = 0
    ) -> str:
        """
        Выполняет прогрессивную суммаризацию сообщений.
        
        Args:
            messages: Список сообщений для суммаризации
            current_summary: Текущее резюме (если есть)
            level: Уровень суммаризации (0 - первый уровень, 1 - второй и т.д.)
            
        Returns:
            str: Суммаризированный текст
        """
        # Проверка наличия сообщений
        if not messages:
            return current_summary or ""
        
        # Проверка уровня суммаризации
        if level >= len(self.max_tokens_per_level):
            level = len(self.max_tokens_per_level) - 1
        
        # Получение максимального количества токенов для текущего уровня
        max_tokens = self.max_tokens_per_level[level]
        
        # Генерация ключа для кэширования
        cache_key = self._get_cache_key(messages)
        
        # Загрузка кэша
        cache = self._load_cache(cache_key)
        
        # Проверка наличия кэша для текущего уровня
        if cache and level in cache:
            return cache[level]
        
        # Если есть текущее резюме и это не первый уровень, используем его
        if current_summary and level > 0:
            text_to_summarize = current_summary
        else:
            # Форматирование сообщений для суммаризации
            text_to_summarize = self._format_messages_for_summarization(messages)
        
        # Суммаризация текста
        summary = self._summarize_text(text_to_summarize, max_tokens)
        
        # Сохранение в кэш
        if not cache:
            cache = {}
        
        cache[level] = summary
        self._save_cache(cache_key, cache)
        
        return summary
    
    def get_multi_level_summary(self, messages: List[Message]) -> Dict[int, str]:
        """
        Возвращает многоуровневое резюме для сообщений.
        
        Args:
            messages: Список сообщений для суммаризации
            
        Returns:
            Dict[int, str]: Словарь с резюме для каждого уровня
        """
        # Генерация ключа для кэширования
        cache_key = self._get_cache_key(messages)
        
        # Загрузка кэша
        cache = self._load_cache(cache_key)
        
        # Если кэш существует и содержит все уровни, возвращаем его
        if cache and all(level in cache for level in range(len(self.max_tokens_per_level))):
            return cache
        
        # Инициализация кэша, если он не существует
        if not cache:
            cache = {}
        
        # Суммаризация для каждого уровня
        current_summary = None
        for level in range(len(self.max_tokens_per_level)):
            # Проверка наличия кэша для текущего уровня
            if level in cache:
                current_summary = cache[level]
                continue
            
            # Суммаризация для текущего уровня
            current_summary = self.summarize(messages, current_summary, level)
            
            # Сохранение в кэш
            cache[level] = current_summary
        
        # Сохранение кэша
        self._save_cache(cache_key, cache)
        
        return cache
    
    def create_summarizer_function(self) -> Callable[[List[Message], Optional[str]], str]:
        """
        Создает функцию суммаризатора для использования в MemoryManager.
        
        Returns:
            Callable: Функция суммаризатора
        """
        def summarizer(messages: List[Message], current_summary: Optional[str] = None) -> str:
            return self.summarize(messages, current_summary)
        
        return summarizer 