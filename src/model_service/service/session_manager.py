"""
Менеджер сессий для ModelService.
Обеспечивает сохранение и управление контекстом сессий пользователей.
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Union
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class Session:
    """
    Класс для хранения контекста отдельной сессии пользователя.
    """
    def __init__(
        self,
        session_id: str,
        model: str,
        max_history_length: int = 10,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализирует сессию.

        Args:
            session_id: Уникальный идентификатор сессии
            model: Модель, используемая в сессии
            max_history_length: Максимальное количество сообщений в истории
            metadata: Дополнительные метаданные сессии
        """
        self.session_id = session_id
        self.model = model
        self.max_history_length = max_history_length
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.metadata = metadata or {}
        self.summary: Optional[str] = None
        
        logger.debug(f"Создана новая сессия {session_id} для модели {model}")
    
    def add_message(self, message: Dict[str, str]) -> None:
        """
        Добавляет сообщение в историю сессии.

        Args:
            message: Сообщение в формате {"role": "...", "content": "..."}
        """
        self.messages.append(message)
        self.last_activity = datetime.now()
        
        # Если превышен лимит истории, удаляем старые сообщения
        if len(self.messages) > self.max_history_length:
            excess = len(self.messages) - self.max_history_length
            removed_messages = self.messages[:excess]
            self.messages = self.messages[excess:]
            
            # Обновляем или создаем суммаризацию удаленных сообщений
            self._update_summary(removed_messages)
    
    def _update_summary(self, removed_messages: List[Dict[str, str]]) -> None:
        """
        Обновляет суммаризацию удаленных сообщений для сохранения контекста.
        В будущем здесь может быть использован вызов специализированного агента
        для суммаризации, а пока используем простое объединение.

        Args:
            removed_messages: Список удаленных сообщений
        """
        # Простая реализация - просто объединяем содержимое удаленных сообщений
        summary_text = ""
        for msg in removed_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            summary_text += f"{role}: {content[:100]}...\n"
        
        if self.summary:
            self.summary += "\n" + summary_text
        else:
            self.summary = f"Суммаризация предыдущей истории:\n{summary_text}"
    
    def get_context_messages(self) -> List[Dict[str, str]]:
        """
        Возвращает все сообщения контекста включая суммаризацию.

        Returns:
            Список сообщений для отправки модели
        """
        result = []
        
        # Добавляем суммаризацию как системное сообщение, если она есть
        if self.summary:
            result.append({"role": "system", "content": self.summary})
        
        # Добавляем текущие сообщения
        result.extend(self.messages)
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует сессию в словарь для сериализации.

        Returns:
            Словарь с данными сессии
        """
        return {
            "session_id": self.session_id,
            "model": self.model,
            "max_history_length": self.max_history_length,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
            "summary": self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """
        Создает сессию из словаря.

        Args:
            data: Словарь с данными сессии

        Returns:
            Объект сессии
        """
        session = cls(
            session_id=data["session_id"],
            model=data["model"],
            max_history_length=data["max_history_length"],
            metadata=data.get("metadata", {})
        )
        
        session.messages = data["messages"]
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.summary = data.get("summary")
        
        return session


class SessionManager:
    """
    Управляет сессиями пользователей для эффективного использования контекста.
    """
    def __init__(
        self,
        ttl: int = 3600,  # Время жизни сессии в секундах (по умолчанию 1 час)
        cleanup_interval: int = 600,  # Интервал очистки устаревших сессий (10 минут)
        max_sessions: int = 1000,  # Максимальное количество сессий в памяти
        storage_path: Optional[str] = None  # Путь для хранения сессий на диске
    ):
        """
        Инициализирует менеджер сессий.

        Args:
            ttl: Время жизни сессии в секундах
            cleanup_interval: Интервал очистки устаревших сессий в секундах
            max_sessions: Максимальное количество сессий в памяти
            storage_path: Путь для сохранения сессий на диск (если None, сохранение отключено)
        """
        self.sessions: Dict[str, Session] = {}
        self.ttl = ttl
        self.cleanup_interval = cleanup_interval
        self.max_sessions = max_sessions
        self.storage_path = storage_path
        self._cleanup_task = None
        
        logger.info(f"Инициализирован менеджер сессий с TTL={ttl}с, интервалом очистки={cleanup_interval}с")
    
    async def start_cleanup_task(self) -> None:
        """
        Запускает периодическую задачу очистки устаревших сессий.
        """
        if self._cleanup_task is None:
            logger.info("Запуск задачи периодической очистки сессий")
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup_task(self) -> None:
        """
        Останавливает задачу очистки сессий.
        """
        if self._cleanup_task is not None:
            logger.info("Остановка задачи очистки сессий")
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_loop(self) -> None:
        """
        Периодически очищает устаревшие сессии.
        """
        while True:
            try:
                self.cleanup_expired_sessions()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                logger.info("Задача очистки сессий отменена")
                break
            except Exception as e:
                logger.error(f"Ошибка при очистке сессий: {e}")
                await asyncio.sleep(10)  # Короткая пауза перед повторной попыткой
    
    def create_session(
        self,
        session_id: str,
        model: str,
        max_history_length: int = 10,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Создает новую сессию.

        Args:
            session_id: Уникальный идентификатор сессии
            model: Модель, используемая в сессии
            max_history_length: Максимальное количество сообщений в истории
            metadata: Дополнительные метаданные сессии

        Returns:
            Созданная сессия
        """
        # Проверяем, не превышен ли лимит сессий
        if len(self.sessions) >= self.max_sessions:
            self._evict_sessions()
        
        # Создаем новую сессию
        session = Session(
            session_id=session_id,
            model=model,
            max_history_length=max_history_length,
            metadata=metadata
        )
        
        self.sessions[session_id] = session
        logger.debug(f"Создана сессия {session_id} для модели {model}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Получает сессию по идентификатору.

        Args:
            session_id: Идентификатор сессии

        Returns:
            Объект сессии или None, если сессия не найдена
        """
        session = self.sessions.get(session_id)
        if session:
            # Обновляем время последней активности
            session.last_activity = datetime.now()
        return session
    
    def add_message_to_session(
        self,
        session_id: str,
        message: Dict[str, str],
        create_if_not_exists: bool = False,
        model: Optional[str] = None
    ) -> Optional[Session]:
        """
        Добавляет сообщение в сессию.

        Args:
            session_id: Идентификатор сессии
            message: Сообщение для добавления
            create_if_not_exists: Создать сессию, если она не существует
            model: Модель для новой сессии (требуется, если create_if_not_exists=True)

        Returns:
            Объект сессии или None, если сессия не найдена и не создана
        """
        session = self.get_session(session_id)
        
        if not session and create_if_not_exists:
            if not model:
                logger.error("Невозможно создать сессию: не указана модель")
                return None
                
            session = self.create_session(session_id, model)
        
        if session:
            session.add_message(message)
            return session
            
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        Удаляет сессию.

        Args:
            session_id: Идентификатор сессии

        Returns:
            True, если сессия была удалена, иначе False
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug(f"Удалена сессия {session_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Очищает устаревшие сессии.

        Returns:
            Количество удаленных сессий
        """
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            # Вычисляем время бездействия
            idle_time = (now - session.last_activity).total_seconds()
            
            if idle_time > self.ttl:
                expired_sessions.append(session_id)
        
        # Удаляем устаревшие сессии
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Очищено {len(expired_sessions)} устаревших сессий")
        
        return len(expired_sessions)
    
    def _evict_sessions(self) -> int:
        """
        Удаляет наименее активные сессии при превышении лимита.

        Returns:
            Количество удаленных сессий
        """
        # Если количество сессий не превышает 90% от лимита, ничего не делаем
        if len(self.sessions) < self.max_sessions * 0.9:
            return 0
        
        # Сортируем сессии по времени последней активности
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_activity
        )
        
        # Удаляем 10% наименее активных сессий
        sessions_to_remove = int(len(sorted_sessions) * 0.1)
        if sessions_to_remove < 1:
            sessions_to_remove = 1
        
        for i in range(sessions_to_remove):
            session_id, _ = sorted_sessions[i]
            del self.sessions[session_id]
        
        logger.info(f"Удалено {sessions_to_remove} наименее активных сессий")
        return sessions_to_remove
    
    async def save_sessions(self) -> bool:
        """
        Сохраняет все сессии на диск.

        Returns:
            True в случае успеха, иначе False
        """
        if not self.storage_path:
            logger.warning("Не указан путь для сохранения сессий")
            return False
            
        try:
            # Преобразуем сессии в словари для сериализации
            sessions_data = {
                session_id: session.to_dict()
                for session_id, session in self.sessions.items()
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(sessions_data, f, indent=2)
                
            logger.info(f"Сохранено {len(self.sessions)} сессий в {self.storage_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении сессий: {e}")
            return False
    
    async def load_sessions(self) -> int:
        """
        Загружает сессии с диска.

        Returns:
            Количество загруженных сессий
        """
        if not self.storage_path:
            logger.warning("Не указан путь для загрузки сессий")
            return 0
            
        try:
            if not os.path.exists(self.storage_path):
                logger.info(f"Файл сессий {self.storage_path} не существует")
                return 0
                
            with open(self.storage_path, 'r') as f:
                sessions_data = json.load(f)
            
            # Очищаем текущие сессии
            self.sessions.clear()
            
            # Загружаем сессии из файла
            for session_id, session_data in sessions_data.items():
                try:
                    session = Session.from_dict(session_data)
                    self.sessions[session_id] = session
                except Exception as e:
                    logger.error(f"Ошибка при загрузке сессии {session_id}: {e}")
            
            logger.info(f"Загружено {len(self.sessions)} сессий из {self.storage_path}")
            return len(self.sessions)
        except Exception as e:
            logger.error(f"Ошибка при загрузке сессий: {e}")
            return 0 