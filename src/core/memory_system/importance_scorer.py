#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для оценки важности информации в системе памяти.

Предоставляет абстрактный класс и конкретные реализации для оценки
важности сообщений и информации в системе памяти.
"""

import os
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple, Type, Callable, Set
from datetime import datetime, timedelta

from src.core.memory_system.memory_base import Message
from src.core.memory_system.embedding_provider import EmbeddingProvider


class ImportanceScorer(ABC):
    """
    Абстрактный класс для оценки важности информации.
    
    Определяет интерфейс для различных алгоритмов оценки важности
    сообщений и информации в системе памяти.
    """
    
    def __init__(self, name: str):
        """
        Инициализация оценщика важности.
        
        Args:
            name: Имя оценщика
        """
        self.name = name
        self.logger = logging.getLogger(f"importance_scorer.{name}")
    
    @abstractmethod
    def score_message(self, message: Message) -> float:
        """
        Оценивает важность сообщения.
        
        Args:
            message: Сообщение для оценки
            
        Returns:
            float: Оценка важности (от 0 до 1)
        """
        pass
    
    @abstractmethod
    def score_messages(self, messages: List[Message]) -> List[float]:
        """
        Оценивает важность списка сообщений.
        
        Args:
            messages: Список сообщений для оценки
            
        Returns:
            List[float]: Список оценок важности (от 0 до 1)
        """
        pass


class KeywordBasedScorer(ImportanceScorer):
    """
    Оценщик важности на основе ключевых слов.
    
    Оценивает важность сообщений на основе наличия ключевых слов
    и их весов.
    """
    
    def __init__(
        self,
        keywords: Dict[str, float],
        case_sensitive: bool = False,
        default_score: float = 0.1
    ):
        """
        Инициализация оценщика важности на основе ключевых слов.
        
        Args:
            keywords: Словарь ключевых слов и их весов
            case_sensitive: Учитывать ли регистр при поиске ключевых слов
            default_score: Оценка по умолчанию для сообщений без ключевых слов
        """
        super().__init__("keyword_based_scorer")
        
        self.keywords = keywords
        self.case_sensitive = case_sensitive
        self.default_score = default_score
        
        # Компиляция регулярных выражений для ключевых слов
        self.keyword_patterns = {}
        for keyword, weight in self.keywords.items():
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', 
                                re.IGNORECASE if not case_sensitive else 0)
            self.keyword_patterns[pattern] = weight
    
    def score_message(self, message: Message) -> float:
        """
        Оценивает важность сообщения на основе ключевых слов.
        
        Args:
            message: Сообщение для оценки
            
        Returns:
            float: Оценка важности (от 0 до 1)
        """
        content = message.content
        
        # Если контент пустой, возвращаем оценку по умолчанию
        if not content:
            return self.default_score
        
        # Поиск ключевых слов в контенте
        total_weight = 0.0
        found_keywords = set()
        
        for pattern, weight in self.keyword_patterns.items():
            matches = pattern.findall(content)
            if matches:
                found_keywords.add(pattern.pattern)
                total_weight += weight * len(matches)
        
        # Если ключевые слова не найдены, возвращаем оценку по умолчанию
        if not found_keywords:
            return self.default_score
        
        # Нормализация оценки (от 0 до 1)
        normalized_score = min(1.0, total_weight / len(self.keywords))
        
        return max(self.default_score, normalized_score)
    
    def score_messages(self, messages: List[Message]) -> List[float]:
        """
        Оценивает важность списка сообщений на основе ключевых слов.
        
        Args:
            messages: Список сообщений для оценки
            
        Returns:
            List[float]: Список оценок важности (от 0 до 1)
        """
        return [self.score_message(message) for message in messages]


class SemanticScorer(ImportanceScorer):
    """
    Оценщик важности на основе семантического сходства.
    
    Оценивает важность сообщений на основе их семантического сходства
    с заданными эталонными текстами.
    """
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        reference_texts: List[str],
        default_score: float = 0.1
    ):
        """
        Инициализация оценщика важности на основе семантического сходства.
        
        Args:
            embedding_provider: Провайдер эмбеддингов
            reference_texts: Список эталонных текстов
            default_score: Оценка по умолчанию для сообщений без сходства
        """
        super().__init__("semantic_scorer")
        
        self.embedding_provider = embedding_provider
        self.reference_texts = reference_texts
        self.default_score = default_score
        
        # Получение эмбеддингов для эталонных текстов
        self.reference_embeddings = self.embedding_provider.get_embeddings(reference_texts)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Вычисляет косинусное сходство между двумя векторами.
        
        Args:
            vec1: Первый вектор
            vec2: Второй вектор
            
        Returns:
            float: Косинусное сходство (от -1 до 1)
        """
        import numpy as np
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (norm1 * norm2)
    
    def score_message(self, message: Message) -> float:
        """
        Оценивает важность сообщения на основе семантического сходства.
        
        Args:
            message: Сообщение для оценки
            
        Returns:
            float: Оценка важности (от 0 до 1)
        """
        content = message.content
        
        # Если контент пустой, возвращаем оценку по умолчанию
        if not content:
            return self.default_score
        
        try:
            # Получение эмбеддинга для сообщения
            message_embedding = self.embedding_provider.get_embedding(content)
            
            # Вычисление сходства с каждым эталонным текстом
            similarities = []
            for reference_embedding in self.reference_embeddings:
                similarity = self._cosine_similarity(message_embedding, reference_embedding)
                similarities.append(similarity)
            
            # Выбор максимального сходства
            max_similarity = max(similarities) if similarities else 0.0
            
            # Нормализация оценки (от 0 до 1)
            normalized_score = (max_similarity + 1) / 2  # Преобразование из [-1, 1] в [0, 1]
            
            return max(self.default_score, normalized_score)
        except Exception as e:
            self.logger.error(f"Ошибка при оценке важности сообщения: {e}")
            return self.default_score
    
    def score_messages(self, messages: List[Message]) -> List[float]:
        """
        Оценивает важность списка сообщений на основе семантического сходства.
        
        Args:
            messages: Список сообщений для оценки
            
        Returns:
            List[float]: Список оценок важности (от 0 до 1)
        """
        return [self.score_message(message) for message in messages]


class RecencyScorer(ImportanceScorer):
    """
    Оценщик важности на основе времени создания сообщения.
    
    Оценивает важность сообщений на основе их времени создания,
    придавая большую важность более новым сообщениям.
    """
    
    def __init__(
        self,
        max_age: timedelta = timedelta(days=30),
        min_score: float = 0.1,
        decay_factor: float = 0.5
    ):
        """
        Инициализация оценщика важности на основе времени.
        
        Args:
            max_age: Максимальный возраст сообщения для оценки
            min_score: Минимальная оценка для старых сообщений
            decay_factor: Фактор затухания важности со временем
        """
        super().__init__("recency_scorer")
        
        self.max_age = max_age
        self.min_score = min_score
        self.decay_factor = decay_factor
    
    def score_message(self, message: Message) -> float:
        """
        Оценивает важность сообщения на основе времени создания.
        
        Args:
            message: Сообщение для оценки
            
        Returns:
            float: Оценка важности (от 0 до 1)
        """
        # Получение времени создания сообщения
        timestamp = message.timestamp
        
        # Вычисление возраста сообщения
        now = datetime.now()
        age = now - timestamp
        
        # Если сообщение старше максимального возраста, возвращаем минимальную оценку
        if age > self.max_age:
            return self.min_score
        
        # Вычисление оценки на основе возраста
        age_ratio = age.total_seconds() / self.max_age.total_seconds()
        score = 1.0 - (age_ratio ** self.decay_factor)
        
        return max(self.min_score, score)
    
    def score_messages(self, messages: List[Message]) -> List[float]:
        """
        Оценивает важность списка сообщений на основе времени создания.
        
        Args:
            messages: Список сообщений для оценки
            
        Returns:
            List[float]: Список оценок важности (от 0 до 1)
        """
        return [self.score_message(message) for message in messages]


class CompositeScorer(ImportanceScorer):
    """
    Композитный оценщик важности.
    
    Объединяет несколько оценщиков важности с разными весами.
    """
    
    def __init__(
        self,
        scorers: List[Tuple[ImportanceScorer, float]],
        normalization: str = "weighted_average"
    ):
        """
        Инициализация композитного оценщика важности.
        
        Args:
            scorers: Список пар (оценщик, вес)
            normalization: Метод нормализации ("weighted_average", "max", "min")
        """
        super().__init__("composite_scorer")
        
        self.scorers = scorers
        self.normalization = normalization
        
        # Проверка весов
        total_weight = sum(weight for _, weight in scorers)
        if total_weight <= 0:
            raise ValueError("Сумма весов должна быть положительной")
        
        # Нормализация весов
        self.normalized_weights = [(scorer, weight / total_weight) for scorer, weight in scorers]
    
    def score_message(self, message: Message) -> float:
        """
        Оценивает важность сообщения с использованием всех оценщиков.
        
        Args:
            message: Сообщение для оценки
            
        Returns:
            float: Оценка важности (от 0 до 1)
        """
        scores = []
        weights = []
        
        for scorer, weight in self.normalized_weights:
            score = scorer.score_message(message)
            scores.append(score)
            weights.append(weight)
        
        # Применение метода нормализации
        if self.normalization == "weighted_average":
            return sum(score * weight for score, weight in zip(scores, weights))
        elif self.normalization == "max":
            return max(scores)
        elif self.normalization == "min":
            return min(scores)
        else:
            # По умолчанию используем взвешенное среднее
            return sum(score * weight for score, weight in zip(scores, weights))
    
    def score_messages(self, messages: List[Message]) -> List[float]:
        """
        Оценивает важность списка сообщений с использованием всех оценщиков.
        
        Args:
            messages: Список сообщений для оценки
            
        Returns:
            List[float]: Список оценок важности (от 0 до 1)
        """
        return [self.score_message(message) for message in messages] 