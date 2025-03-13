#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер памяти для управления различными типами памяти для разных пользователей.

Предоставляет единый интерфейс для работы с памятью в мульти-агентной системе,
абстрагируя детали реализации конкретных типов памяти.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Type, Callable
from datetime import datetime

from src.core.memory_system.memory_base import MemoryBase, Message, UserMessage, AssistantMessage, SystemMessage
from src.core.memory_system.buffer_memory import BufferMemory
from src.core.memory_system.summary_memory import SummaryMemory
from src.core.memory_system.long_term_memory import LongTermMemory
from src.core.memory_system.vector_store import VectorStore
from src.core.memory_system.qdrant_vector_store import QdrantVectorStore
from src.core.memory_system.embedding_provider import EmbeddingProvider, MistralEmbeddingProvider


class MemoryManager:
    """
    Менеджер памяти для управления различными типами памяти для разных пользователей.
    
    Предоставляет единый интерфейс для работы с памятью в мульти-агентной системе,
    абстрагируя детали реализации конкретных типов памяти.
    """
    
    def __init__(
        self,
        storage_dir: str = "data/memory",
        default_buffer_size: int = 50,
        default_summarize_threshold: int = 10,
        summarizer: Optional[Callable[[List[Message], Optional[str]], str]] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store_factory: Optional[Callable[[str], VectorStore]] = None
    ):
        """
        Инициализация менеджера памяти.
        
        Args:
            storage_dir: Директория для хранения данных памяти
            default_buffer_size: Размер буфера по умолчанию
            default_summarize_threshold: Порог суммаризации по умолчанию
            summarizer: Функция для суммаризации сообщений
            embedding_provider: Провайдер эмбеддингов для векторизации текста
            vector_store_factory: Фабрика для создания векторных хранилищ
        """
        self.storage_dir = storage_dir
        self.default_buffer_size = default_buffer_size
        self.default_summarize_threshold = default_summarize_threshold
        self.summarizer = summarizer
        self.logger = logging.getLogger("memory_manager")
        
        # Создание директорий для хранения данных
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(os.path.join(storage_dir, "buffer"), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, "summary"), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, "long_term"), exist_ok=True)
        
        # Словари для хранения экземпляров памяти
        self.buffer_memories: Dict[str, BufferMemory] = {}
        self.summary_memories: Dict[str, SummaryMemory] = {}
        self.long_term_memories: Dict[str, LongTermMemory] = {}
        
        # Инициализация провайдера эмбеддингов
        self.embedding_provider = embedding_provider
        
        # Инициализация фабрики векторных хранилищ
        self.vector_store_factory = vector_store_factory
    
    def get_buffer_memory(self, user_id: str) -> BufferMemory:
        """
        Возвращает буферную память для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            BufferMemory: Буферная память пользователя
        """
        if user_id not in self.buffer_memories:
            # Создание новой буферной памяти
            buffer_memory = BufferMemory(
                memory_id=f"buffer_{user_id}",
                description=f"Буферная память для пользователя {user_id}",
                max_messages=self.default_buffer_size
            )
            
            # Загрузка данных, если они существуют
            buffer_path = os.path.join(self.storage_dir, "buffer", f"{user_id}.json")
            if os.path.exists(buffer_path):
                try:
                    with open(buffer_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    for message_data in data.get("messages", []):
                        role = message_data.get("role", "system")
                        
                        if role == "user":
                            message = UserMessage.from_dict(message_data)
                        elif role == "assistant":
                            message = AssistantMessage.from_dict(message_data)
                        else:
                            message = SystemMessage.from_dict(message_data)
                        
                        buffer_memory.add_message(message)
                    
                    self.logger.info(f"Загружена буферная память для пользователя {user_id}")
                except Exception as e:
                    self.logger.error(f"Ошибка при загрузке буферной памяти для пользователя {user_id}: {e}")
            
            self.buffer_memories[user_id] = buffer_memory
        
        return self.buffer_memories[user_id]
    
    def get_summary_memory(self, user_id: str) -> SummaryMemory:
        """
        Возвращает память с резюме для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            SummaryMemory: Память с резюме пользователя
        """
        if user_id not in self.summary_memories:
            # Создание новой памяти с резюме
            summary_memory = SummaryMemory(
                memory_id=f"summary_{user_id}",
                description=f"Память с резюме для пользователя {user_id}",
                summarize_threshold=self.default_summarize_threshold,
                summarizer=self.summarizer
            )
            
            # Загрузка данных, если они существуют
            summary_path = os.path.join(self.storage_dir, "summary", f"{user_id}.json")
            if os.path.exists(summary_path):
                try:
                    with open(summary_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    summary_memory.summary = data.get("summary", "")
                    
                    for message_data in data.get("messages", []):
                        role = message_data.get("role", "system")
                        
                        if role == "user":
                            message = UserMessage.from_dict(message_data)
                        elif role == "assistant":
                            message = AssistantMessage.from_dict(message_data)
                        else:
                            message = SystemMessage.from_dict(message_data)
                        
                        summary_memory.add_message(message)
                    
                    self.logger.info(f"Загружена память с резюме для пользователя {user_id}")
                except Exception as e:
                    self.logger.error(f"Ошибка при загрузке памяти с резюме для пользователя {user_id}: {e}")
            
            self.summary_memories[user_id] = summary_memory
        
        return self.summary_memories[user_id]
    
    def get_long_term_memory(self, user_id: str) -> LongTermMemory:
        """
        Возвращает долгосрочную память для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            LongTermMemory: Долгосрочная память пользователя
        """
        if user_id not in self.long_term_memories:
            # Проверка наличия провайдера эмбеддингов
            if self.embedding_provider is None:
                # Создание провайдера эмбеддингов по умолчанию
                self.embedding_provider = MistralEmbeddingProvider()
            
            # Проверка наличия фабрики векторных хранилищ
            if self.vector_store_factory is None:
                # Создание фабрики векторных хранилищ по умолчанию
                def default_vector_store_factory(collection_name: str) -> VectorStore:
                    # Путь к хранилищу Qdrant
                    qdrant_storage_path = os.path.join(self.storage_dir, "long_term", "qdrant")
                    
                    # Проверка наличия файла блокировки
                    lock_file_path = os.path.join(qdrant_storage_path, ".lock")
                    if os.path.exists(lock_file_path):
                        try:
                            # Попытка удалить файл блокировки, если он существует
                            os.remove(lock_file_path)
                            self.logger.warning(f"Удален файл блокировки Qdrant: {lock_file_path}")
                        except Exception as e:
                            self.logger.error(f"Не удалось удалить файл блокировки Qdrant: {e}")
                    
                    try:
                        # Создание векторного хранилища
                        return QdrantVectorStore(
                            collection_name=collection_name,
                            vector_size=self.embedding_provider.get_embedding_dimension(),
                            storage_dir=qdrant_storage_path
                        )
                    except Exception as e:
                        error_message = str(e)
                        if "already accessed by another instance" in error_message:
                            # Если ошибка связана с блокировкой, попробовать использовать in-memory хранилище
                            self.logger.warning(f"Не удалось инициализировать Qdrant на диске: {error_message}")
                            self.logger.warning("Используем in-memory хранилище Qdrant как запасной вариант")
                            return QdrantVectorStore(
                                collection_name=collection_name,
                                vector_size=self.embedding_provider.get_embedding_dimension(),
                                storage_dir=None  # None указывает на использование режима в памяти
                            )
                        else:
                            # Другие ошибки пробрасываем дальше
                            raise
                
                self.vector_store_factory = default_vector_store_factory
            
            try:
                # Создание векторного хранилища
                vector_store = self.vector_store_factory(f"long_term_{user_id}")
                
                # Создание новой долгосрочной памяти
                long_term_memory = LongTermMemory(
                    memory_id=f"long_term_{user_id}",
                    description=f"Долгосрочная память для пользователя {user_id}",
                    vector_store=vector_store,
                    embedding_provider=self.embedding_provider,
                    storage_dir=os.path.join(self.storage_dir, "long_term")
                )
                
                # Загрузка данных
                long_term_memory.load()
                
                self.long_term_memories[user_id] = long_term_memory
            except Exception as e:
                self.logger.error(f"Ошибка при инициализации долгосрочной памяти: {e}")
                # Создаем заглушку для долгосрочной памяти, чтобы не блокировать работу системы
                # Можно использовать другую реализацию памяти без векторного хранилища
                raise RuntimeError(f"Не удалось инициализировать долгосрочную память: {e}")
        
        return self.long_term_memories[user_id]
    
    def add_user_message(self, user_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Добавляет сообщение пользователя в память.
        
        Args:
            user_id: Идентификатор пользователя
            content: Содержимое сообщения
            metadata: Дополнительные метаданные сообщения
        """
        # Создание сообщения пользователя
        message = UserMessage(
            content=content,
            user_id=user_id,
            metadata=metadata
        )
        
        # Добавление сообщения в буферную память
        buffer_memory = self.get_buffer_memory(user_id)
        buffer_memory.add_message(message)
        
        # Добавление сообщения в память с резюме
        summary_memory = self.get_summary_memory(user_id)
        summary_memory.add_message(message)
        
        # Добавление сообщения в долгосрочную память
        long_term_memory = self.get_long_term_memory(user_id)
        long_term_memory.add_message(message)
        
        self.logger.debug(f"Добавлено сообщение пользователя {user_id}: {content[:50]}...")
    
    def add_assistant_message(
        self,
        user_id: str,
        content: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Добавляет сообщение ассистента в память.
        
        Args:
            user_id: Идентификатор пользователя
            content: Содержимое сообщения
            agent_id: Идентификатор агента (опционально)
            metadata: Дополнительные метаданные сообщения
        """
        # Создание сообщения ассистента
        message = AssistantMessage(
            content=content,
            agent_id=agent_id,
            metadata=metadata
        )
        
        # Добавление сообщения в буферную память
        buffer_memory = self.get_buffer_memory(user_id)
        buffer_memory.add_message(message)
        
        # Добавление сообщения в память с резюме
        summary_memory = self.get_summary_memory(user_id)
        summary_memory.add_message(message)
        
        # Добавление сообщения в долгосрочную память
        long_term_memory = self.get_long_term_memory(user_id)
        long_term_memory.add_message(message)
        
        self.logger.debug(f"Добавлено сообщение ассистента для пользователя {user_id}: {content[:50]}...")
    
    def add_ai_message(
        self,
        user_id: str,
        content: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Алиас для метода add_assistant_message для совместимости с интерфейсом langchain_router.
        
        Args:
            user_id: Идентификатор пользователя
            content: Содержимое сообщения
            agent_name: Имя агента (опционально) - переименовано из agent_id для совместимости
            metadata: Дополнительные метаданные сообщения
        """
        return self.add_assistant_message(
            user_id=user_id,
            content=content,
            agent_id=agent_name,  # Пересылаем agent_name как agent_id
            metadata=metadata
        )
    
    def add_system_message(self, user_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Добавляет системное сообщение в память.
        
        Args:
            user_id: Идентификатор пользователя
            content: Содержимое сообщения
            metadata: Дополнительные метаданные сообщения
        """
        # Создание системного сообщения
        message = SystemMessage(
            content=content,
            metadata=metadata
        )
        
        # Добавление сообщения в буферную память
        buffer_memory = self.get_buffer_memory(user_id)
        buffer_memory.add_message(message)
        
        # Добавление сообщения в память с резюме
        summary_memory = self.get_summary_memory(user_id)
        summary_memory.add_message(message)
        
        # Добавление сообщения в долгосрочную память
        long_term_memory = self.get_long_term_memory(user_id)
        long_term_memory.add_message(message)
        
        self.logger.debug(f"Добавлено системное сообщение для пользователя {user_id}: {content[:50]}...")
    
    def get_chat_history(self, user_id: str, limit: Optional[int] = None) -> List[Message]:
        """
        Возвращает историю чата для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            limit: Максимальное количество сообщений
            
        Returns:
            List[Message]: История чата
        """
        buffer_memory = self.get_buffer_memory(user_id)
        return buffer_memory.get_messages(limit)
    
    def get_chat_summary(self, user_id: str) -> str:
        """
        Возвращает резюме чата для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            str: Резюме чата
        """
        summary_memory = self.get_summary_memory(user_id)
        return summary_memory.get_summary()
    
    def search_long_term_memory(
        self,
        user_id: str,
        query: str,
        limit: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Message, float]]:
        """
        Выполняет семантический поиск в долгосрочной памяти.
        
        Args:
            user_id: Идентификатор пользователя
            query: Текстовый запрос для поиска
            limit: Максимальное количество результатов
            filter_metadata: Фильтр по метаданным
            
        Returns:
            List[Tuple[Message, float]]: Список пар (сообщение, оценка)
        """
        long_term_memory = self.get_long_term_memory(user_id)
        return long_term_memory.search_messages(query, limit, filter_metadata)
    
    def get_context(self, user_id: str) -> Dict[str, Any]:
        """
        Возвращает контекст для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Dict[str, Any]: Контекст пользователя
        """
        return {
            "chat_history": self.get_chat_history(user_id),
            "summary": self.get_chat_summary(user_id)
        }
    
    def clear_memory(self, user_id: str) -> None:
        """
        Очищает память для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
        """
        # Очистка буферной памяти
        if user_id in self.buffer_memories:
            self.buffer_memories[user_id].clear()
        
        # Очистка памяти с резюме
        if user_id in self.summary_memories:
            self.summary_memories[user_id].clear()
        
        # Очистка долгосрочной памяти
        if user_id in self.long_term_memories:
            self.long_term_memories[user_id].clear()
        
        self.logger.info(f"Очищена память для пользователя {user_id}")
    
    def save_all(self) -> None:
        """
        Сохраняет всю память для всех пользователей.
        """
        # Сохранение буферной памяти
        for user_id, buffer_memory in self.buffer_memories.items():
            buffer_path = os.path.join(self.storage_dir, "buffer", f"{user_id}.json")
            
            try:
                data = {
                    "messages": [message.to_dict() for message in buffer_memory.get_messages()]
                }
                
                with open(buffer_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.logger.debug(f"Сохранена буферная память для пользователя {user_id}")
            except Exception as e:
                self.logger.error(f"Ошибка при сохранении буферной памяти для пользователя {user_id}: {e}")
        
        # Сохранение памяти с резюме
        for user_id, summary_memory in self.summary_memories.items():
            summary_path = os.path.join(self.storage_dir, "summary", f"{user_id}.json")
            
            try:
                data = {
                    "summary": summary_memory.get_summary(),
                    "messages": [message.to_dict() for message in summary_memory.get_messages()]
                }
                
                with open(summary_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.logger.debug(f"Сохранена память с резюме для пользователя {user_id}")
            except Exception as e:
                self.logger.error(f"Ошибка при сохранении памяти с резюме для пользователя {user_id}: {e}")
        
        # Сохранение долгосрочной памяти
        for user_id, long_term_memory in self.long_term_memories.items():
            try:
                long_term_memory.save()
                self.logger.debug(f"Сохранена долгосрочная память для пользователя {user_id}")
            except Exception as e:
                self.logger.error(f"Ошибка при сохранении долгосрочной памяти для пользователя {user_id}: {e}")
    
    def get_all_users(self) -> List[str]:
        """
        Возвращает список всех пользователей.
        
        Returns:
            List[str]: Список идентификаторов пользователей
        """
        # Получение списка файлов в директории буферной памяти
        buffer_dir = os.path.join(self.storage_dir, "buffer")
        users = set()
        
        if os.path.exists(buffer_dir):
            for filename in os.listdir(buffer_dir):
                if filename.endswith(".json"):
                    user_id = filename[:-5]  # Удаление расширения .json
                    users.add(user_id)
        
        return list(users)
    
    def get_formatted_history(
        self,
        user_id: str,
        include_system_messages: bool = False,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Возвращает отформатированную историю чата для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            include_system_messages: Включать ли системные сообщения
            limit: Максимальное количество сообщений
            
        Returns:
            List[Dict[str, str]]: Отформатированная история чата
        """
        messages = self.get_chat_history(user_id, limit)
        formatted_history = []
        
        for message in messages:
            if not include_system_messages and message.role == "system":
                continue
            
            formatted_history.append({
                "role": message.role,
                "content": message.content
            })
        
        return formatted_history
    
    def get_relevant_context(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        include_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Возвращает релевантный контекст для указанного запроса.
        
        Args:
            user_id: Идентификатор пользователя
            query: Текстовый запрос
            limit: Максимальное количество результатов
            include_summary: Включать ли резюме
            
        Returns:
            Dict[str, Any]: Релевантный контекст
        """
        # Получение последних сообщений из буферной памяти
        recent_messages = self.get_chat_history(user_id, limit)
        
        # Поиск релевантных сообщений в долгосрочной памяти
        relevant_messages = self.search_long_term_memory(user_id, query, limit)
        
        # Получение резюме
        summary = self.get_chat_summary(user_id) if include_summary else ""
        
        return {
            "recent_messages": recent_messages,
            "relevant_messages": [message for message, score in relevant_messages],
            "relevant_scores": [score for message, score in relevant_messages],
            "summary": summary
        } 