#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для базовых классов и интерфейсов системы памяти.

Проверяет функциональность базовых классов сообщений и интерфейса памяти.
"""

import pytest
from datetime import datetime
import json

from src.core.memory_system.memory_base import (
    Message,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    MemoryBase
)


class TestMessage:
    """Тесты для базового класса сообщений."""
    
    def test_message_initialization(self):
        """Тест инициализации базового сообщения."""
        content = "Тестовое сообщение"
        role = "user"
        metadata = {"test_key": "test_value"}
        
        message = Message(content, role, metadata=metadata)
        
        assert message.content == content
        assert message.role == role
        assert message.metadata == metadata
        assert isinstance(message.timestamp, datetime)
    
    def test_message_to_dict(self):
        """Тест сериализации сообщения в словарь."""
        content = "Тестовое сообщение"
        role = "user"
        timestamp = datetime.now()
        metadata = {"test_key": "test_value"}
        
        message = Message(content, role, timestamp, metadata)
        message_dict = message.to_dict()
        
        assert message_dict["content"] == content
        assert message_dict["role"] == role
        assert message_dict["timestamp"] == timestamp.isoformat()
        assert message_dict["metadata"] == metadata
    
    def test_message_from_dict(self):
        """Тест десериализации сообщения из словаря."""
        content = "Тестовое сообщение"
        role = "user"
        timestamp = datetime.now()
        metadata = {"test_key": "test_value"}
        
        message_dict = {
            "content": content,
            "role": role,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata
        }
        
        message = Message.from_dict(message_dict)
        
        assert message.content == content
        assert message.role == role
        assert message.metadata == metadata
        assert isinstance(message.timestamp, datetime)
    
    def test_message_str_representation(self):
        """Тест строкового представления сообщения."""
        content = "Тестовое сообщение"
        role = "user"
        
        message = Message(content, role)
        
        assert str(message) == f"{role}: {content}"


class TestUserMessage:
    """Тесты для класса сообщений пользователя."""
    
    def test_user_message_initialization(self):
        """Тест инициализации сообщения пользователя."""
        content = "Тестовое сообщение пользователя"
        user_id = "user123"
        metadata = {"test_key": "test_value"}
        
        message = UserMessage(content, user_id, metadata=metadata)
        
        assert message.content == content
        assert message.role == "user"
        assert message.user_id == user_id
        assert message.metadata["user_id"] == user_id
        assert message.metadata["test_key"] == "test_value"


class TestAssistantMessage:
    """Тесты для класса сообщений ассистента."""
    
    def test_assistant_message_initialization(self):
        """Тест инициализации сообщения ассистента."""
        content = "Тестовое сообщение ассистента"
        agent_id = "agent123"
        metadata = {"test_key": "test_value"}
        
        message = AssistantMessage(content, agent_id, metadata=metadata)
        
        assert message.content == content
        assert message.role == "assistant"
        assert message.agent_id == agent_id
        assert message.metadata["agent_id"] == agent_id
        assert message.metadata["test_key"] == "test_value"
    
    def test_assistant_message_without_agent_id(self):
        """Тест инициализации сообщения ассистента без указания agent_id."""
        content = "Тестовое сообщение ассистента"
        
        message = AssistantMessage(content)
        
        assert message.content == content
        assert message.role == "assistant"
        assert not hasattr(message, "agent_id")
        assert "agent_id" not in message.metadata


class TestSystemMessage:
    """Тесты для класса системных сообщений."""
    
    def test_system_message_initialization(self):
        """Тест инициализации системного сообщения."""
        content = "Тестовое системное сообщение"
        metadata = {"test_key": "test_value"}
        
        message = SystemMessage(content, metadata=metadata)
        
        assert message.content == content
        assert message.role == "system"
        assert message.metadata["test_key"] == "test_value"


class MockMemory(MemoryBase):
    """Мок-класс для тестирования абстрактного базового класса памяти."""
    
    def __init__(self, memory_id, description):
        super().__init__(memory_id, description)
        self.messages = []
    
    def add_message(self, message):
        self.messages.append(message)
    
    def get_messages(self, limit=None):
        if limit is None:
            return self.messages
        return self.messages[-limit:]
    
    def clear(self):
        self.messages = []
    
    def save(self):
        pass
    
    def load(self):
        pass


class TestMemoryBase:
    """Тесты для базового класса памяти."""
    
    def test_memory_base_initialization(self):
        """Тест инициализации базового класса памяти."""
        memory_id = "test_memory"
        description = "Тестовая память"
        
        memory = MockMemory(memory_id, description)
        
        assert memory.memory_id == memory_id
        assert memory.description == description
    
    def test_memory_base_get_info(self):
        """Тест получения информации о памяти."""
        memory_id = "test_memory"
        description = "Тестовая память"
        
        memory = MockMemory(memory_id, description)
        info = memory.get_info()
        
        assert info["memory_id"] == memory_id
        assert info["description"] == description
        assert info["type"] == "MockMemory" 