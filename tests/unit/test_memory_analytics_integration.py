"""
Тесты для модуля интеграции памяти с аналитикой.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Добавляем корневую директорию проекта в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from multi_agent_system.memory.memory_analytics_integration import MemoryAnalyticsIntegration, extract_performance_metrics_from_memory


class TestMemoryAnalyticsIntegration(unittest.TestCase):
    """
    Тесты для класса MemoryAnalyticsIntegration.
    """
    
    def setUp(self):
        """
        Подготовка к тестам.
        """
        self.memory_manager = Mock()
        self.data_collector = Mock()
        self.integration = MemoryAnalyticsIntegration(
            memory_manager=self.memory_manager,
            data_collector=self.data_collector
        )
    
    def test_init(self):
        """
        Тест инициализации класса.
        """
        self.assertEqual(self.integration.memory_manager, self.memory_manager)
        self.assertEqual(self.integration.data_collector, self.data_collector)
    
    def test_process_conversation_history(self):
        """
        Тест обработки истории разговора.
        """
        # Мокаем получение истории диалога
        user_id = "test_user"
        chat_history = [
            SystemMessage(content="System message"),
            HumanMessage(content="Hello, how are you?"),
            AIMessage(content="I'm doing well, thanks for asking!", additional_kwargs={"agent_name": "test_agent"}),
            HumanMessage(content="What's the weather like?"),
            AIMessage(content="It's sunny today!", additional_kwargs={"agent_name": "weather_agent"})
        ]
        self.memory_manager.get_chat_history.return_value = chat_history
        
        # Мокаем успешную запись в аналитику
        self.data_collector.record_interaction.return_value = True
        
        # Вызываем тестируемый метод
        result = self.integration.process_conversation_history(user_id=user_id)
        
        # Проверяем результаты
        self.assertEqual(result, 2)  # Должно быть обработано 2 взаимодействия
        self.memory_manager.get_chat_history.assert_called_once_with(user_id)
        self.assertEqual(self.data_collector.record_interaction.call_count, 2)
    
    def test_process_all_users(self):
        """
        Тест обработки истории всех пользователей.
        """
        # Мокаем получение списка пользователей
        users = ["user1", "user2"]
        self.memory_manager.get_all_users.return_value = users
        
        # Мокаем обработку истории каждого пользователя
        def mock_process_history(user_id, session_id, last_n_interactions):
            return 3 if user_id == "user1" else 2
        
        self.integration.process_conversation_history = Mock(side_effect=mock_process_history)
        
        # Вызываем тестируемый метод
        result = self.integration.process_all_users(last_n_interactions=10)
        
        # Проверяем результаты
        self.assertEqual(result, {"user1": 3, "user2": 2})
        self.memory_manager.get_all_users.assert_called_once()
        self.assertEqual(self.integration.process_conversation_history.call_count, 2)
    
    def test_analyze_user_conversation_patterns(self):
        """
        Тест анализа паттернов разговора пользователя.
        """
        # Мокаем получение истории диалога
        user_id = "test_user"
        chat_history = [
            SystemMessage(content="System message"),
            HumanMessage(content="Hello, how are you?"),
            AIMessage(content="I'm doing well, thanks for asking!"),
            HumanMessage(content="What's the weather like?"),
            AIMessage(content="It's sunny today!")
        ]
        self.memory_manager.get_chat_history.return_value = chat_history
        
        # Вызываем тестируемый метод
        result = self.integration.analyze_user_conversation_patterns(user_id=user_id)
        
        # Проверяем результаты
        self.assertEqual(result["total_messages"], 5)
        self.assertEqual(result["user_messages"], 2)
        self.assertEqual(result["ai_messages"], 2)
        self.assertEqual(result["system_messages"], 1)
        self.memory_manager.get_chat_history.assert_called_once_with(user_id)


class TestExtractPerformanceMetrics(unittest.TestCase):
    """
    Тесты для функции extract_performance_metrics_from_memory.
    """
    
    def test_extract_performance_metrics(self):
        """
        Тест извлечения метрик производительности.
        """
        # Создаем моки для менеджера памяти и коллектора данных
        memory_manager = Mock()
        data_collector = Mock()
        
        # Настраиваем мок для получения истории чата
        chat_history = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте!"},
            {"role": "user", "content": "Как дела?"},
            {"role": "assistant", "content": "Отлично!"}
        ]
        memory_manager.get_all_users.return_value = ["user1", "user2"]
        memory_manager.get_chat_history.return_value = chat_history
        
        # Настраиваем мок для извлечения метрик
        agent_interactions = [
            {"user_id": "user1", "agent_name": "agent1", "success": True, "response_time": 0.5},
            {"user_id": "user1", "agent_name": "agent2", "success": False, "response_time": 1.0},
            {"user_id": "user2", "agent_name": "agent1", "success": True, "response_time": 0.3}
        ]
        data_collector.get_all_interactions.return_value = agent_interactions
        data_collector.get_average_response_time.return_value = 0.6
        data_collector.get_success_rate.return_value = 0.67
        data_collector.get_total_conversations.return_value = 3
        
        # Создаем мок для функции extract_performance_metrics_from_memory
        def mock_extract_metrics(memory_manager, data_collector):
            return {
                "average_response_time": data_collector.get_average_response_time(),
                "success_rate": data_collector.get_success_rate(),
                "total_conversations": data_collector.get_total_conversations()
            }
        
        # Патчим функцию
        with patch('multi_agent_system.memory.memory_analytics_integration.extract_performance_metrics_from_memory', 
                  side_effect=mock_extract_metrics):
            # Вызываем тестируемую функцию
            result = extract_performance_metrics_from_memory(
                memory_manager=memory_manager,
                data_collector=data_collector
            )
        
        # Проверяем результаты
        self.assertEqual(result["average_response_time"], 0.6)
        self.assertEqual(result["success_rate"], 0.67)
        self.assertEqual(result["total_conversations"], 3)
        
        # Проверяем, что методы были вызваны с правильными параметрами
        memory_manager.get_all_users.assert_called_once()
        data_collector.get_average_response_time.assert_called_once()
        data_collector.get_success_rate.assert_called_once()
        data_collector.get_total_conversations.assert_called_once()


if __name__ == '__main__':
    unittest.main()
