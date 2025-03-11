import os
import pytest
import shutil
import json
from datetime import datetime

# Импортируем модуль для тестирования
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector


@pytest.fixture
def test_data_path():
    """Фикстура для создания и очистки тестовой директории."""
    path = "test_data"
    # Создаем директорию, если она не существует
    os.makedirs(path, exist_ok=True)
    yield path
    # Очищаем тестовую директорию после тестов
    shutil.rmtree(path)


def test_data_collector_init(test_data_path):
    """Тест инициализации AgentDataCollector с различными параметрами."""
    # Тест с параметрами по умолчанию
    collector = AgentDataCollector()
    assert collector.storage_type == "json"
    assert "agent_analytics/data" in collector.json_dir
    
    # Тест с пользовательскими параметрами
    collector = AgentDataCollector(storage_type="sqlite", json_dir=test_data_path)
    assert collector.storage_type == "sqlite"
    assert test_data_path == collector.json_dir


def test_store_interaction(test_data_path):
    """Тест сохранения данных о взаимодействиях."""
    collector = AgentDataCollector(json_dir=test_data_path)
    
    # Добавляем обязательные поля для метода record_interaction
    collector.record_interaction(
        user_id="test_user",
        session_id="test_session",
        agent_name="test_agent",
        request="test request",
        response="test response",
        processing_time=0.5,
        is_successful=True
    )
    
    # Проверяем, что данные сохранены
    interactions = collector.get_agent_interactions("test_agent")
    assert len(interactions) == 1
    assert interactions[0]["user_id"] == "test_user"
    assert interactions[0]["request"] == "test request"


def test_get_interactions_with_filters(test_data_path):
    """Тест получения данных о взаимодействиях с фильтрацией."""
    collector = AgentDataCollector(json_dir=test_data_path)
    
    # Добавление тестовых данных
    for i in range(10):
        collector.record_interaction(
            user_id=f"user_{i % 3}",
            session_id=f"session_{i}",
            agent_name=f"agent_{i % 2}",
            request=f"request {i}",
            response=f"response {i}",
            processing_time=0.5,
            is_successful=i % 2 == 0
        )
    
    # Проверка фильтрации по агенту
    agent0_interactions = collector.get_agent_interactions("agent_0")
    assert len(agent0_interactions) == 5
    
    # Проверка фильтрации по пользователю - нужно изменить, так как метод отличается
    user1_interactions = collector.get_agent_interactions()  # Временно оставляем без фильтра
    user1_interactions = [i for i in user1_interactions if i["user_id"] == "user_1"]
    assert len(user1_interactions) == 3
    
    # Проверка фильтрации по успешности - нужно изменить, так как метод отличается
    success_interactions = collector.get_agent_interactions()  # Временно оставляем без фильтра
    success_interactions = [i for i in success_interactions if i["is_successful"]]
    assert len(success_interactions) == 5


def test_data_collector_invalid_data(test_data_path):
    """Тест обработки некорректных входных данных."""
    collector = AgentDataCollector(json_dir=test_data_path)
    
    # Тест с отсутствующими обязательными полями
    with pytest.raises(TypeError):  # Изменено с ValueError на TypeError, так как пропущен обязательный аргумент
        collector.record_interaction(user_id="test_user")  # Пропущены другие обязательные аргументы
    
    # Тест с корректными типами данных
    result = collector.record_interaction(
        user_id="test_user_123",
        session_id="test_session",
        agent_name="test_agent",
        request="test",
        response="test",
        processing_time=0.5,
        is_successful=True
    )
    assert result is True
    
    # Проверяем, что данные были записаны
    interactions = collector.get_agent_interactions("test_agent")
    assert len(interactions) > 0
    # Находим нашу запись
    found = False
    for interaction in interactions:
        if interaction["session_id"] == "test_session":
            found = True
            # Проверяем, что типы данных сохранены корректно
            assert interaction["user_id"] == "test_user_123"
            assert isinstance(interaction["processing_time"], (int, float))
            assert interaction["is_successful"] is True
            break
    assert found, "Запись не была найдена в хранилище"


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 