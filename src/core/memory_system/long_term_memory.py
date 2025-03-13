#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с долгосрочной памятью на основе векторного хранилища.

Предоставляет реализацию долгосрочной памяти с использованием векторного хранилища
для эффективного поиска и извлечения информации.
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple, Type, Callable
from datetime import datetime

from src.core.memory_system.memory_base import MemoryBase, Message, UserMessage, AssistantMessage, SystemMessage
from src.core.memory_system.vector_store import VectorStore
from src.core.memory_system.embedding_provider import EmbeddingProvider


class LongTermMemory(MemoryBase):
    """
    Реализация долгосрочной памяти на основе векторного хранилища.
    
    Предоставляет методы для сохранения, поиска и извлечения информации
    с использованием векторного хранилища и эмбеддингов.
    """
    
    def __init__(
        self,
        memory_id: str,
        description: str,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        storage_dir: Optional[str] = None,
        importance_threshold: float = 0.5,
        max_results: int = 10
    ):
        """
        Инициализация долгосрочной памяти.
        
        Args:
            memory_id: Идентификатор памяти
            description: Описание памяти
            vector_store: Векторное хранилище для хранения эмбеддингов
            embedding_provider: Провайдер эмбеддингов для векторизации текста
            storage_dir: Директория для хранения данных (если применимо)
            importance_threshold: Порог важности для сохранения сообщений
            max_results: Максимальное количество результатов при поиске
        """
        super().__init__(memory_id, description)
        
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.storage_dir = storage_dir
        self.importance_threshold = importance_threshold
        self.max_results = max_results
        
        # Кэш сообщений для оптимизации доступа
        self.message_cache: Dict[str, Message] = {}
        
        # Инициализация логгера
        self.logger = logging.getLogger(f"long_term_memory.{memory_id}")
    
    def add_message(self, message: Message) -> None:
        """
        Добавляет сообщение в долгосрочную память.
        
        Args:
            message: Сообщение для добавления
        """
        # Получение эмбеддинга для сообщения
        embedding = self.embedding_provider.get_embedding(message.content)
        
        # Подготовка метаданных
        metadata = {
            "role": message.role,
            "timestamp": message.timestamp.isoformat(),
            "content": message.content,
            **message.metadata
        }
        
        # Добавление эмбеддинга в векторное хранилище
        ids = self.vector_store.add_vectors(
            vectors=[embedding],
            metadata=[metadata]
        )
        
        # Сохранение сообщения в кэше
        message_id = ids[0]
        self.message_cache[message_id] = message
        
        self.logger.debug(f"Добавлено сообщение в долгосрочную память: {message_id}")
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """
        Возвращает все сообщения из долгосрочной памяти.
        
        Args:
            limit: Максимальное количество сообщений
            
        Returns:
            List[Message]: Список сообщений
        """
        # Получение количества векторов в хранилище
        count = self.vector_store.get_count()
        
        # Если хранилище пусто, возвращаем пустой список
        if count == 0:
            return []
        
        # Ограничение количества сообщений
        if limit is None or limit > count:
            limit = count
        
        # Получение всех сообщений из хранилища
        # Примечание: это не оптимальный подход для больших хранилищ,
        # но для демонстрации он подойдет
        messages = []
        
        # Здесь должна быть реализация получения всех сообщений из хранилища
        # Но так как векторное хранилище не предоставляет прямого метода для этого,
        # мы можем использовать кэш сообщений
        
        # Если кэш пуст, мы можем попробовать загрузить сообщения из хранилища
        if not self.message_cache:
            self.load()
        
        # Возвращаем сообщения из кэша
        return list(self.message_cache.values())[:limit]
    
    def search_messages(
        self,
        query: str,
        limit: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Message, float]]:
        """
        Выполняет семантический поиск сообщений по запросу.
        
        Args:
            query: Текстовый запрос для поиска
            limit: Максимальное количество результатов
            filter_metadata: Фильтр по метаданным
            
        Returns:
            List[Tuple[Message, float]]: Список пар (сообщение, оценка)
        """
        if limit is None:
            limit = self.max_results
        
        # Получение эмбеддинга для запроса
        query_embedding = self.embedding_provider.get_embedding(query)
        
        # Выполнение поиска в векторном хранилище
        search_results = self.vector_store.search(
            query_vector=query_embedding,
            limit=limit,
            filter_metadata=filter_metadata
        )
        
        # Преобразование результатов в сообщения
        messages_with_scores = []
        for result in search_results:
            message_id = result["id"]
            score = result["score"]
            metadata = result["metadata"]
            
            # Проверка наличия сообщения в кэше
            if message_id in self.message_cache:
                message = self.message_cache[message_id]
            else:
                # Создание сообщения из метаданных
                role = metadata.get("role", "system")
                content = metadata.get("content", "")
                timestamp_str = metadata.get("timestamp")
                
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()
                
                # Удаление служебных полей из метаданных
                message_metadata = {k: v for k, v in metadata.items() if k not in ["role", "content", "timestamp"]}
                
                # Создание сообщения в зависимости от роли
                if role == "user":
                    user_id = message_metadata.get("user_id", "unknown")
                    message = UserMessage(content, user_id, timestamp, message_metadata)
                elif role == "assistant":
                    agent_id = message_metadata.get("agent_id")
                    message = AssistantMessage(content, agent_id, timestamp, message_metadata)
                else:
                    message = SystemMessage(content, timestamp, message_metadata)
                
                # Сохранение сообщения в кэше
                self.message_cache[message_id] = message
            
            messages_with_scores.append((message, score))
        
        return messages_with_scores
    
    def clear(self) -> None:
        """
        Очищает долгосрочную память.
        """
        # Очистка векторного хранилища
        self.vector_store.clear()
        
        # Очистка кэша сообщений
        self.message_cache.clear()
        
        self.logger.info(f"Долгосрочная память очищена: {self.memory_id}")
    
    def save(self) -> None:
        """
        Сохраняет долгосрочную память.
        """
        # Сохранение векторного хранилища
        self.vector_store.save()
        
        # Сохранение кэша сообщений, если указана директория для хранения
        if self.storage_dir:
            os.makedirs(self.storage_dir, exist_ok=True)
            cache_path = os.path.join(self.storage_dir, f"{self.memory_id}_cache.json")
            
            # Сериализация сообщений
            serialized_cache = {}
            for message_id, message in self.message_cache.items():
                serialized_cache[message_id] = message.to_dict()
            
            # Сохранение в файл
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(serialized_cache, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Кэш сообщений сохранен: {cache_path}")
    
    def load(self) -> None:
        """
        Загружает долгосрочную память.
        """
        # Загрузка векторного хранилища
        self.vector_store.load()
        
        # Загрузка кэша сообщений, если указана директория для хранения
        if self.storage_dir:
            cache_path = os.path.join(self.storage_dir, f"{self.memory_id}_cache.json")
            
            if os.path.exists(cache_path):
                try:
                    # Загрузка из файла
                    with open(cache_path, "r", encoding="utf-8") as f:
                        serialized_cache = json.load(f)
                    
                    # Десериализация сообщений
                    self.message_cache = {}
                    for message_id, message_dict in serialized_cache.items():
                        role = message_dict.get("role", "system")
                        
                        # Создание сообщения в зависимости от роли
                        if role == "user":
                            message = UserMessage.from_dict(message_dict)
                        elif role == "assistant":
                            message = AssistantMessage.from_dict(message_dict)
                        else:
                            message = SystemMessage.from_dict(message_dict)
                        
                        self.message_cache[message_id] = message
                    
                    self.logger.info(f"Кэш сообщений загружен: {cache_path}")
                except Exception as e:
                    self.logger.error(f"Ошибка при загрузке кэша сообщений: {e}")
    
    def get_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о долгосрочной памяти.
        
        Returns:
            Dict[str, Any]: Информация о памяти
        """
        info = super().get_info()
        info.update({
            "type": "long_term_memory",
            "vector_store_type": type(self.vector_store).__name__,
            "embedding_provider_type": type(self.embedding_provider).__name__,
            "embedding_model": self.embedding_provider.model_name,
            "vector_dimension": self.embedding_provider.get_embedding_dimension(),
            "message_count": self.vector_store.get_count(),
            "importance_threshold": self.importance_threshold,
            "max_results": self.max_results
        })
        return info 