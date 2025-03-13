#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с векторными хранилищами.

Предоставляет абстрактный класс для работы с различными векторными базами данных
и конкретную реализацию для Qdrant.
"""

import os
import json
import logging
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple, Type, Callable
from datetime import datetime


class VectorStore(ABC):
    """
    Абстрактный класс для работы с векторными хранилищами.
    
    Определяет интерфейс для работы с различными векторными базами данных,
    такими как Qdrant, FAISS, Pinecone и др.
    """
    
    def __init__(
        self,
        collection_name: str,
        vector_size: int,
        storage_dir: Optional[str] = None,
        distance_metric: str = "cosine"
    ):
        """
        Инициализация векторного хранилища.
        
        Args:
            collection_name: Имя коллекции векторов
            vector_size: Размерность векторов
            storage_dir: Директория для хранения данных (если применимо)
            distance_metric: Метрика расстояния (cosine, euclidean, dot)
        """
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.storage_dir = storage_dir
        self.distance_metric = distance_metric
        self.logger = logging.getLogger(f"vector_store.{collection_name}")
    
    @abstractmethod
    def add_vectors(
        self,
        vectors: List[List[float]],
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Добавляет векторы в хранилище.
        
        Args:
            vectors: Список векторов для добавления
            ids: Список идентификаторов для векторов (опционально)
            metadata: Список метаданных для векторов (опционально)
            
        Returns:
            List[str]: Список идентификаторов добавленных векторов
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Выполняет поиск ближайших векторов.
        
        Args:
            query_vector: Вектор запроса
            limit: Максимальное количество результатов
            filter_metadata: Фильтр по метаданным (опционально)
            
        Returns:
            List[Dict[str, Any]]: Список результатов поиска с метаданными и оценками
        """
        pass
    
    @abstractmethod
    def delete_vectors(self, ids: List[str]) -> bool:
        """
        Удаляет векторы из хранилища.
        
        Args:
            ids: Список идентификаторов векторов для удаления
            
        Returns:
            bool: Успешность операции
        """
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """
        Очищает хранилище.
        
        Returns:
            bool: Успешность операции
        """
        pass
    
    @abstractmethod
    def get_count(self) -> int:
        """
        Возвращает количество векторов в хранилище.
        
        Returns:
            int: Количество векторов
        """
        pass
    
    @abstractmethod
    def save(self) -> bool:
        """
        Сохраняет хранилище (если применимо).
        
        Returns:
            bool: Успешность операции
        """
        pass
    
    @abstractmethod
    def load(self) -> bool:
        """
        Загружает хранилище (если применимо).
        
        Returns:
            bool: Успешность операции
        """
        pass 