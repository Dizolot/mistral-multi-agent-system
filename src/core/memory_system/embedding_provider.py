#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с провайдерами эмбеддингов.

Предоставляет абстрактный класс для работы с различными моделями эмбеддингов
и конкретную реализацию для локальной модели Mistral.
"""

import os
import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple, Type, Callable
from datetime import datetime


class EmbeddingProvider(ABC):
    """
    Абстрактный класс для работы с провайдерами эмбеддингов.
    
    Определяет интерфейс для получения эмбеддингов из текста с использованием
    различных моделей, таких как Mistral, OpenAI, HuggingFace и др.
    """
    
    def __init__(self, model_name: str):
        """
        Инициализация провайдера эмбеддингов.
        
        Args:
            model_name: Имя модели для получения эмбеддингов
        """
        self.model_name = model_name
        self.logger = logging.getLogger(f"embedding_provider.{model_name}")
    
    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получает эмбеддинги для списка текстов.
        
        Args:
            texts: Список текстов для получения эмбеддингов
            
        Returns:
            List[List[float]]: Список эмбеддингов для каждого текста
        """
        pass
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """
        Получает эмбеддинг для одного текста.
        
        Args:
            text: Текст для получения эмбеддинга
            
        Returns:
            List[float]: Эмбеддинг для текста
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Возвращает размерность эмбеддингов.
        
        Returns:
            int: Размерность эмбеддингов
        """
        pass


class LocalMistralEmbeddingProvider(EmbeddingProvider):
    """
    Реализация провайдера эмбеддингов для локальной модели Mistral.
    
    Использует локально развернутую модель Mistral для получения эмбеддингов из текста.
    """
    
    # Размерности эмбеддингов для разных моделей Mistral
    EMBEDDING_DIMENSIONS = {
        "mistral-embed": 1024,
        "mistral-embed-v2": 1536
    }
    
    def __init__(
        self,
        model_name: str = "mistral-embed",
        server_url: Optional[str] = None,
        batch_size: int = 10
    ):
        """
        Инициализация провайдера эмбеддингов для локальной модели Mistral.
        
        Args:
            model_name: Имя модели для получения эмбеддингов
            server_url: URL локального сервера с моделью (если None, берется из переменной окружения)
            batch_size: Размер пакета для пакетной обработки
        """
        super().__init__(model_name)
        
        # Получение URL сервера из переменной окружения, если не указан
        if server_url is None:
            server_url = os.environ.get("MISTRAL_SERVER_URL")
            if server_url is None:
                # Пробуем получить URL из альтернативной переменной
                server_url = os.environ.get("MISTRAL_API_URL")
                if server_url is None:
                    raise ValueError("URL сервера Mistral не указан и не найден в переменных окружения (MISTRAL_SERVER_URL или MISTRAL_API_URL)")
        
        self.server_url = server_url.rstrip("/")
        self.batch_size = batch_size
        
        # Проверка поддерживаемой модели
        if model_name not in self.EMBEDDING_DIMENSIONS:
            self.logger.warning(f"Модель {model_name} не в списке поддерживаемых моделей. "
                               f"Размерность эмбеддингов может быть неизвестна.")
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получает эмбеддинги для списка текстов с использованием локальной модели Mistral.
        
        Args:
            texts: Список текстов для получения эмбеддингов
            
        Returns:
            List[List[float]]: Список эмбеддингов для каждого текста
        """
        if not texts:
            return []
        
        all_embeddings = []
        
        # Обработка текстов пакетами для оптимизации запросов
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i+self.batch_size]
            
            try:
                # Запрос эмбеддингов через локальный сервер
                response = requests.post(
                    f"{self.server_url}/embeddings",
                    json={
                        "model": self.model_name,
                        "inputs": batch_texts
                    }
                )
                response.raise_for_status()
                
                # Извлечение эмбеддингов из ответа
                result = response.json()
                batch_embeddings = [data["embedding"] for data in result["data"]]
                all_embeddings.extend(batch_embeddings)
                
                self.logger.debug(f"Получены эмбеддинги для пакета {i//self.batch_size + 1} "
                                 f"из {(len(texts) + self.batch_size - 1)//self.batch_size}")
            except Exception as e:
                self.logger.error(f"Ошибка при получении эмбеддингов: {e}")
                # Добавляем пустые эмбеддинги для текстов, которые не удалось обработать
                all_embeddings.extend([[0.0] * self.get_embedding_dimension() for _ in range(len(batch_texts))])
        
        return all_embeddings
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Получает эмбеддинг для одного текста с использованием локальной модели Mistral.
        
        Args:
            text: Текст для получения эмбеддинга
            
        Returns:
            List[float]: Эмбеддинг для текста
        """
        try:
            # Запрос эмбеддинга через локальный сервер
            response = requests.post(
                f"{self.server_url}/embeddings",
                json={
                    "model": self.model_name,
                    "inputs": [text]
                }
            )
            response.raise_for_status()
            
            # Извлечение эмбеддинга из ответа
            result = response.json()
            embedding = result["data"][0]["embedding"]
            return embedding
        except Exception as e:
            self.logger.error(f"Ошибка при получении эмбеддинга: {e}")
            # Возвращаем пустой эмбеддинг в случае ошибки
            return [0.0] * self.get_embedding_dimension()
    
    def get_embedding_dimension(self) -> int:
        """
        Возвращает размерность эмбеддингов для модели Mistral.
        
        Returns:
            int: Размерность эмбеддингов
        """
        return self.EMBEDDING_DIMENSIONS.get(self.model_name, 1024)


# Alias для совместимости с тестами
MistralEmbeddingProvider = LocalMistralEmbeddingProvider 