#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Реализация векторного хранилища на основе Qdrant.

Предоставляет конкретную реализацию VectorStore для работы с Qdrant.
"""

import os
import json
import uuid
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple, Type, Callable
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.memory_system.vector_store import VectorStore


class QdrantVectorStore(VectorStore):
    """
    Реализация векторного хранилища на основе Qdrant.
    
    Предоставляет методы для работы с Qdrant, включая добавление,
    поиск и удаление векторов.
    """
    
    def __init__(
        self,
        collection_name: str,
        vector_size: int,
        storage_dir: Optional[str] = None,
        distance_metric: str = "cosine",
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None
    ):
        """
        Инициализация векторного хранилища Qdrant.
        
        Args:
            collection_name: Имя коллекции векторов
            vector_size: Размерность векторов
            storage_dir: Директория для хранения данных (для локального хранилища)
            distance_metric: Метрика расстояния (cosine, euclidean, dot)
            host: Хост Qdrant сервера (для удаленного хранилища)
            port: Порт Qdrant сервера (для удаленного хранилища)
            api_key: API ключ для Qdrant Cloud (для удаленного хранилища)
            url: URL Qdrant сервера (для удаленного хранилища)
        """
        super().__init__(collection_name, vector_size, storage_dir, distance_metric)
        
        # Инициализация клиента Qdrant
        if url:
            # Подключение к Qdrant Cloud по URL
            self.client = QdrantClient(url=url, api_key=api_key)
        elif host and port:
            # Подключение к удаленному Qdrant серверу
            self.client = QdrantClient(host=host, port=port, api_key=api_key)
        elif storage_dir:
            # Подключение к локальному Qdrant серверу
            os.makedirs(storage_dir, exist_ok=True)
            self.client = QdrantClient(path=storage_dir)
        else:
            # Подключение к локальному Qdrant серверу в памяти
            self.client = QdrantClient(":memory:")
        
        # Преобразование метрики расстояния в формат Qdrant
        distance_mapping = {
            "cosine": qdrant_models.Distance.COSINE,
            "euclidean": qdrant_models.Distance.EUCLID,
            "dot": qdrant_models.Distance.DOT
        }
        self.qdrant_distance = distance_mapping.get(distance_metric, qdrant_models.Distance.COSINE)
        
        # Создание коллекции, если она не существует
        self._create_collection_if_not_exists()
    
    def _create_collection_if_not_exists(self) -> None:
        """
        Создает коллекцию в Qdrant, если она не существует.
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qdrant_models.VectorParams(
                        size=self.vector_size,
                        distance=self.qdrant_distance
                    )
                )
                self.logger.info(f"Создана новая коллекция: {self.collection_name}")
        except Exception as e:
            self.logger.error(f"Ошибка при создании коллекции: {e}")
            raise
    
    def add_vectors(
        self,
        vectors: List[List[float]],
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Добавляет векторы в хранилище Qdrant.
        
        Args:
            vectors: Список векторов для добавления
            ids: Список идентификаторов для векторов (опционально)
            metadata: Список метаданных для векторов (опционально)
            
        Returns:
            List[str]: Список идентификаторов добавленных векторов
        """
        if not vectors:
            return []
        
        # Генерация идентификаторов, если они не предоставлены
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        
        # Подготовка метаданных
        if metadata is None:
            metadata = [{} for _ in range(len(vectors))]
        
        # Проверка соответствия размеров
        if len(vectors) != len(ids) or len(vectors) != len(metadata):
            raise ValueError("Размеры списков vectors, ids и metadata должны совпадать")
        
        # Подготовка точек для добавления
        points = [
            qdrant_models.PointStruct(
                id=id,
                vector=vector,
                payload=meta
            )
            for id, vector, meta in zip(ids, vectors, metadata)
        ]
        
        try:
            # Добавление точек в коллекцию
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            self.logger.info(f"Добавлено {len(vectors)} векторов в коллекцию {self.collection_name}")
            return ids
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении векторов: {e}")
            raise
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Выполняет поиск ближайших векторов в Qdrant.
        
        Args:
            query_vector: Вектор запроса
            limit: Максимальное количество результатов
            filter_metadata: Фильтр по метаданным (опционально)
            
        Returns:
            List[Dict[str, Any]]: Список результатов поиска с метаданными и оценками
        """
        try:
            # Преобразование фильтра метаданных в формат Qdrant
            filter_condition = None
            if filter_metadata:
                filter_condition = qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key=key,
                            match=qdrant_models.MatchValue(value=value)
                        )
                        for key, value in filter_metadata.items()
                    ]
                )
            
            # Выполнение поиска
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=filter_condition
            )
            
            # Преобразование результатов в удобный формат
            results = []
            for scored_point in search_result:
                results.append({
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "metadata": scored_point.payload
                })
            
            return results
        except Exception as e:
            self.logger.error(f"Ошибка при поиске векторов: {e}")
            raise
    
    def delete_vectors(self, ids: List[str]) -> bool:
        """
        Удаляет векторы из хранилища Qdrant.
        
        Args:
            ids: Список идентификаторов векторов для удаления
            
        Returns:
            bool: Успешность операции
        """
        if not ids:
            return True
        
        try:
            # Удаление точек из коллекции
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=ids
                )
            )
            self.logger.info(f"Удалено {len(ids)} векторов из коллекции {self.collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при удалении векторов: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Очищает хранилище Qdrant.
        
        Returns:
            bool: Успешность операции
        """
        try:
            # Удаление коллекции
            self.client.delete_collection(collection_name=self.collection_name)
            self.logger.info(f"Коллекция {self.collection_name} удалена")
            
            # Создание новой коллекции
            self._create_collection_if_not_exists()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при очистке хранилища: {e}")
            return False
    
    def get_count(self) -> int:
        """
        Возвращает количество векторов в хранилище Qdrant.
        
        Returns:
            int: Количество векторов
        """
        try:
            # Получение информации о коллекции
            collection_info = self.client.get_collection(collection_name=self.collection_name)
            return collection_info.vectors_count
        except Exception as e:
            self.logger.error(f"Ошибка при получении количества векторов: {e}")
            return 0
    
    def save(self) -> bool:
        """
        Сохраняет хранилище Qdrant (для локального хранилища).
        
        Returns:
            bool: Успешность операции
        """
        # Для Qdrant не требуется явное сохранение, так как оно происходит автоматически
        return True
    
    def load(self) -> bool:
        """
        Загружает хранилище Qdrant (для локального хранилища).
        
        Returns:
            bool: Успешность операции
        """
        # Для Qdrant не требуется явная загрузка, так как она происходит автоматически
        return True 