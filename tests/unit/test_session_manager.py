"""
Тесты для модуля управления сессиями.
"""

import os
import time
import json
import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.model_service.service.session_manager import Session, SessionManager


class TestSession:
    """Тесты для класса Session."""

    def test_session_initialization(self):
        """Тест инициализации сессии."""
        session_id = "test_session_id"
        model = "test_model"
        max_history_length = 10
        metadata = {"user_id": "test_user"}

        session = Session(
            session_id=session_id,
            model=model,
            max_history_length=max_history_length,
            metadata=metadata
        )

        assert session.session_id == session_id
        assert session.model == model
        assert session.max_history_length == max_history_length
        assert session.metadata == metadata
        assert len(session.messages) == 0
        assert session.summary is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)

    def test_add_message(self):
        """Тест добавления сообщения в сессию."""
        session = Session(
            session_id="test_session_id",
            model="test_model",
            max_history_length=3
        )

        # Добавляем первое сообщение
        message1 = {"role": "user", "content": "Hello"}
        session.add_message(message1)
        assert len(session.messages) == 1
        assert session.messages[0] == message1

        # Добавляем второе сообщение
        message2 = {"role": "assistant", "content": "Hi there!"}
        session.add_message(message2)
        assert len(session.messages) == 2
        assert session.messages[1] == message2

        # Добавляем третье сообщение
        message3 = {"role": "user", "content": "How are you?"}
        session.add_message(message3)
        assert len(session.messages) == 3
        assert session.messages[2] == message3

        # Добавляем четвертое сообщение, должно удалиться первое
        message4 = {"role": "assistant", "content": "I'm fine, thanks!"}
        session.add_message(message4)
        assert len(session.messages) == 3
        assert session.messages[0] == message2
        assert session.messages[1] == message3
        assert session.messages[2] == message4

    def test_update_summary(self):
        """Тест обновления саммари сессии."""
        session = Session(
            session_id="test_session_id",
            model="test_model"
        )

        # Проверяем, что изначально саммари пустое
        assert session.summary is None

        # Обновляем саммари
        summary = "This is a test conversation about greetings."
        session.update_summary(summary)
        assert session.summary == summary

        # Обновляем саммари еще раз
        new_summary = "This is an updated summary about the conversation."
        session.update_summary(new_summary)
        assert session.summary == new_summary

    def test_get_context_messages(self):
        """Тест получения контекстных сообщений."""
        session = Session(
            session_id="test_session_id",
            model="test_model"
        )

        # Добавляем сообщения
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm fine, thanks!"}
        ]
        for message in messages:
            session.add_message(message)

        # Проверяем получение всех сообщений
        context_messages = session.get_context_messages()
        assert len(context_messages) == 4
        assert context_messages == messages

        # Обновляем саммари
        summary = "This is a test conversation about greetings."
        session.update_summary(summary)

        # Проверяем получение сообщений с саммари
        context_messages_with_summary = session.get_context_messages(include_summary=True)
        assert len(context_messages_with_summary) == 5
        assert context_messages_with_summary[0] == {"role": "system", "content": summary}
        assert context_messages_with_summary[1:] == messages

    def test_to_dict_and_from_dict(self):
        """Тест сериализации и десериализации сессии."""
        session_id = "test_session_id"
        model = "test_model"
        max_history_length = 10
        metadata = {"user_id": "test_user"}
        
        # Создаем сессию
        session = Session(
            session_id=session_id,
            model=model,
            max_history_length=max_history_length,
            metadata=metadata
        )
        
        # Добавляем сообщения
        session.add_message({"role": "user", "content": "Hello"})
        session.add_message({"role": "assistant", "content": "Hi there!"})
        
        # Обновляем саммари
        session.update_summary("Test conversation")
        
        # Сериализуем сессию
        session_dict = session.to_dict()
        
        # Проверяем, что все поля сохранены
        assert session_dict["session_id"] == session_id
        assert session_dict["model"] == model
        assert session_dict["max_history_length"] == max_history_length
        assert session_dict["metadata"] == metadata
        assert session_dict["summary"] == "Test conversation"
        assert len(session_dict["messages"]) == 2
        assert isinstance(session_dict["created_at"], str)
        assert isinstance(session_dict["last_activity"], str)
        
        # Десериализуем сессию
        new_session = Session.from_dict(session_dict)
        
        # Проверяем, что все поля восстановлены
        assert new_session.session_id == session_id
        assert new_session.model == model
        assert new_session.max_history_length == max_history_length
        assert new_session.metadata == metadata
        assert new_session.summary == "Test conversation"
        assert len(new_session.messages) == 2
        assert new_session.messages[0]["role"] == "user"
        assert new_session.messages[0]["content"] == "Hello"
        assert new_session.messages[1]["role"] == "assistant"
        assert new_session.messages[1]["content"] == "Hi there!"
        assert isinstance(new_session.created_at, datetime)
        assert isinstance(new_session.last_activity, datetime)


class TestSessionManager:
    """Тесты для класса SessionManager."""

    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_session_manager_initialization(self, temp_dir):
        """Тест инициализации менеджера сессий."""
        session_ttl = 3600  # 1 час
        max_sessions = 100
        
        manager = SessionManager(
            session_ttl=session_ttl,
            max_sessions=max_sessions,
            storage_path=temp_dir
        )
        
        assert manager.session_ttl == session_ttl
        assert manager.max_sessions == max_sessions
        assert manager.storage_path == temp_dir
        assert len(manager.sessions) == 0

    def test_create_session(self, temp_dir):
        """Тест создания сессии."""
        manager = SessionManager(
            session_ttl=3600,
            max_sessions=100,
            storage_path=temp_dir
        )
        
        # Создаем сессию
        session_id = "test_session_id"
        model = "test_model"
        max_history_length = 10
        metadata = {"user_id": "test_user"}
        
        session = manager.create_session(
            session_id=session_id,
            model=model,
            max_history_length=max_history_length,
            metadata=metadata
        )
        
        # Проверяем, что сессия создана и добавлена в менеджер
        assert session.session_id == session_id
        assert session.model == model
        assert session.max_history_length == max_history_length
        assert session.metadata == metadata
        assert session_id in manager.sessions
        assert manager.sessions[session_id] == session

    def test_get_session(self, temp_dir):
        """Тест получения сессии."""
        manager = SessionManager(
            session_ttl=3600,
            max_sessions=100,
            storage_path=temp_dir
        )
        
        # Создаем сессию
        session_id = "test_session_id"
        session = manager.create_session(session_id=session_id)
        
        # Получаем сессию
        retrieved_session = manager.get_session(session_id)
        assert retrieved_session == session
        
        # Пытаемся получить несуществующую сессию
        non_existent_session = manager.get_session("non_existent_id")
        assert non_existent_session is None

    def test_add_message(self, temp_dir):
        """Тест добавления сообщения в сессию."""
        manager = SessionManager(
            session_ttl=3600,
            max_sessions=100,
            storage_path=temp_dir
        )
        
        # Создаем сессию
        session_id = "test_session_id"
        session = manager.create_session(session_id=session_id)
        
        # Добавляем сообщение
        message = {"role": "user", "content": "Hello"}
        manager.add_message(session_id, message)
        
        # Проверяем, что сообщение добавлено
        assert len(session.messages) == 1
        assert session.messages[0] == message
        
        # Пытаемся добавить сообщение в несуществующую сессию
        with pytest.raises(ValueError):
            manager.add_message("non_existent_id", message)

    def test_delete_session(self, temp_dir):
        """Тест удаления сессии."""
        manager = SessionManager(
            session_ttl=3600,
            max_sessions=100,
            storage_path=temp_dir
        )
        
        # Создаем сессию
        session_id = "test_session_id"
        manager.create_session(session_id=session_id)
        
        # Проверяем, что сессия существует
        assert session_id in manager.sessions
        
        # Удаляем сессию
        manager.delete_session(session_id)
        
        # Проверяем, что сессия удалена
        assert session_id not in manager.sessions
        
        # Пытаемся удалить несуществующую сессию
        manager.delete_session("non_existent_id")  # Не должно вызывать исключение

    def test_cleanup_expired_sessions(self, temp_dir):
        """Тест очистки истекших сессий."""
        # Создаем менеджер с коротким TTL
        manager = SessionManager(
            session_ttl=1,  # 1 секунда
            max_sessions=100,
            storage_path=temp_dir
        )
        
        # Создаем сессии
        session1_id = "test_session_1"
        session2_id = "test_session_2"
        
        manager.create_session(session_id=session1_id)
        manager.create_session(session_id=session2_id)
        
        # Проверяем, что обе сессии существуют
        assert session1_id in manager.sessions
        assert session2_id in manager.sessions
        
        # Ждем, чтобы сессии истекли
        time.sleep(2)
        
        # Запускаем очистку
        manager.cleanup_expired_sessions()
        
        # Проверяем, что обе сессии удалены
        assert session1_id not in manager.sessions
        assert session2_id not in manager.sessions

    def test_max_sessions_limit(self, temp_dir):
        """Тест ограничения максимального количества сессий."""
        # Создаем менеджер с ограничением в 2 сессии
        manager = SessionManager(
            session_ttl=3600,
            max_sessions=2,
            storage_path=temp_dir
        )
        
        # Создаем 3 сессии
        session1_id = "test_session_1"
        session2_id = "test_session_2"
        session3_id = "test_session_3"
        
        manager.create_session(session_id=session1_id)
        manager.create_session(session_id=session2_id)
        
        # Проверяем, что обе сессии существуют
        assert session1_id in manager.sessions
        assert session2_id in manager.sessions
        
        # Создаем третью сессию, должна удалиться самая старая (первая)
        manager.create_session(session_id=session3_id)
        
        # Проверяем, что первая сессия удалена, а вторая и третья существуют
        assert session1_id not in manager.sessions
        assert session2_id in manager.sessions
        assert session3_id in manager.sessions

    @pytest.mark.asyncio
    async def test_save_and_load_sessions(self, temp_dir):
        """Тест сохранения и загрузки сессий."""
        # Создаем менеджер
        manager = SessionManager(
            session_ttl=3600,
            max_sessions=100,
            storage_path=temp_dir
        )
        
        # Создаем сессии
        session1_id = "test_session_1"
        session2_id = "test_session_2"
        
        session1 = manager.create_session(session_id=session1_id, model="model1")
        session2 = manager.create_session(session_id=session2_id, model="model2")
        
        # Добавляем сообщения
        manager.add_message(session1_id, {"role": "user", "content": "Hello from session 1"})
        manager.add_message(session2_id, {"role": "user", "content": "Hello from session 2"})
        
        # Сохраняем сессии
        await manager.save_sessions()
        
        # Проверяем, что файлы созданы
        assert os.path.exists(os.path.join(temp_dir, f"{session1_id}.json"))
        assert os.path.exists(os.path.join(temp_dir, f"{session2_id}.json"))
        
        # Создаем новый менеджер и загружаем сессии
        new_manager = SessionManager(
            session_ttl=3600,
            max_sessions=100,
            storage_path=temp_dir
        )
        
        await new_manager.load_sessions()
        
        # Проверяем, что сессии загружены
        assert session1_id in new_manager.sessions
        assert session2_id in new_manager.sessions
        
        # Проверяем содержимое сессий
        loaded_session1 = new_manager.get_session(session1_id)
        loaded_session2 = new_manager.get_session(session2_id)
        
        assert loaded_session1.model == "model1"
        assert loaded_session2.model == "model2"
        assert len(loaded_session1.messages) == 1
        assert len(loaded_session2.messages) == 1
        assert loaded_session1.messages[0]["content"] == "Hello from session 1"
        assert loaded_session2.messages[0]["content"] == "Hello from session 2" 