"""
Тесты для модуля интеграции тестирования агентов с памятью диалогов.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, call

# Добавляем корневую директорию проекта в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from multi_agent_system.agent_developer.testing_memory_integration import TestingMemoryIntegration, create_auto_improvement_cycle


class TestTestingMemoryIntegration(unittest.TestCase):
    """
    Тесты для класса TestingMemoryIntegration.
    """
    
    def setUp(self):
        """
        Подготовка к тестам.
        """
        self.memory_manager = Mock()
        self.agent_tester = Mock()
        self.agent_optimizer = Mock()
        self.version_manager = Mock()
        self.data_collector = Mock()
        
        self.integration = TestingMemoryIntegration(
            memory_manager=self.memory_manager,
            agent_tester=self.agent_tester,
            agent_optimizer=self.agent_optimizer,
            version_manager=self.version_manager,
            data_collector=self.data_collector
        )
    
    def test_init(self):
        """
        Тест инициализации класса.
        """
        self.assertEqual(self.integration.memory_manager, self.memory_manager)
        self.assertEqual(self.integration.agent_tester, self.agent_tester)
        self.assertEqual(self.integration.agent_optimizer, self.agent_optimizer)
        self.assertEqual(self.integration.version_manager, self.version_manager)
        self.assertEqual(self.integration.data_collector, self.data_collector)
    
    def test_create_test_dataset_from_memory(self):
        """
        Тест создания тестового набора данных из памяти диалогов.
        """
        # Мокаем получение списка пользователей
        self.memory_manager.get_all_users.return_value = ["user1", "user2"]
        
        # Мокаем получение истории диалога для первого пользователя
        chat_history_1 = [
            SystemMessage(content="System message"),
            HumanMessage(content="Hello, this is a long message for test purposes." * 5),  # Длинное сообщение
            AIMessage(content="Response to user1", additional_kwargs={"agent_name": "test_agent"}),
        ]
        
        # Мокаем получение истории диалога для второго пользователя
        chat_history_2 = [
            HumanMessage(content="Another test message that is also quite long." * 5),  # Длинное сообщение
            AIMessage(content="Response to user2", additional_kwargs={"agent_name": "test_agent"}),
        ]
        
        # Настраиваем моки для возврата истории диалогов
        self.memory_manager.get_chat_history.side_effect = lambda user_id: chat_history_1 if user_id == "user1" else chat_history_2
        
        # Мокаем создание тестового набора данных
        test_dataset_id = "test_dataset_123"
        self.agent_tester.create_test_dataset.return_value = test_dataset_id
        
        # Вызываем тестируемый метод
        result = self.integration.create_test_dataset_from_memory(
            agent_name="test_agent",
            sample_size=2,
            min_message_length=50
        )
        
        # Проверяем результаты
        self.assertEqual(result, test_dataset_id)
        self.memory_manager.get_all_users.assert_called_once()
        self.assertEqual(self.memory_manager.get_chat_history.call_count, 2)
        self.agent_tester.create_test_dataset.assert_called_once()
        
        # Проверяем, что созданы правильные тестовые случаи
        args, kwargs = self.agent_tester.create_test_dataset.call_args
        self.assertEqual(kwargs["agent_name"], "test_agent")
        self.assertEqual(len(kwargs["test_cases"]), 2)  # Должно быть 2 тестовых случая
    
    def test_improve_agent_from_memory(self):
        """Тест улучшения агента на основе памяти диалогов."""
        # Настраиваем моки
        self.memory_manager.get_chat_history.return_value = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте!"}
        ]
        
        # Настраиваем результаты тестирования
        test_result = {"success_rate": 0.9, "is_better": True}
        self.agent_tester.evaluate_improvement.return_value = test_result
        
        # Вызываем тестируемый метод
        integration = TestingMemoryIntegration(
            memory_manager=self.memory_manager,
            agent_tester=self.agent_tester,
            agent_optimizer=self.agent_optimizer,
            version_manager=self.version_manager,
            data_collector=self.data_collector
        )
        
        result = integration.improve_agent_from_memory(
            agent_name="test_agent",
            agent_system_prompt="Вы - тестовый агент",
            agent_description="Тестовый агент для проверки"
        )
        
        # Проверяем результаты
        self.assertEqual(result["test_results"], test_result)
        self.assertEqual(result["agent_name"], "test_agent")
        self.assertTrue("improvement_id" in result)
        
        # Проверяем, что методы были вызваны с правильными параметрами
        self.memory_manager.get_chat_history.assert_called()
        self.agent_optimizer.create_improvement.assert_called_once()
        self.agent_tester.evaluate_improvement.assert_called_once()
        self.version_manager.save_version.assert_called_once()


class TestCreateAutoImprovementCycle(unittest.TestCase):
    """Тесты для функции создания цикла автоматического улучшения агентов."""
    
    def test_create_auto_improvement_cycle(self):
        """Тест создания цикла автоматического улучшения агентов."""
        # Создаем моки для необходимых компонентов
        memory_manager = Mock()
        agent_tester = Mock()
        agent_optimizer = Mock()
        version_manager = Mock()
        data_collector = Mock()
        
        # Настраиваем моки
        agents = ["agent1", "agent2", "agent3"]
        version_manager.get_all_agents.return_value = agents
        
        # Настраиваем версии агентов
        agent_versions = {
            "agent1": {"system_prompt": "Вы - агент 1", "description": "Описание агента 1"},
            "agent2": {"system_prompt": "Вы - агент 2", "description": "Описание агента 2"},
            "agent3": {"system_prompt": "Вы - агент 3", "description": "Описание агента 3"}
        }
        
        version_manager.load_agent_version = lambda agent_name: agent_versions.get(agent_name)
        
        # Настраиваем результаты для каждого агента
        improvement_results = {
            "agent1": {
                "improvement_generated": True, 
                "deployed": True,
                "test_results": {"success_rate": 0.9, "is_better": True}
            },
            "agent2": {
                "improvement_generated": True, 
                "deployed": False,
                "test_results": {"success_rate": 0.85, "is_better": False}
            },
            "agent3": {
                "improvement_generated": False, 
                "deployed": False,
                "test_results": None
            }
        }
        
        # Создаем мок для интеграции тестирования и памяти
        testing_integration = Mock()
        testing_integration.improve_agent_from_memory.side_effect = lambda agent_name, agent_system_prompt, agent_description, test_improvement=True, deploy_if_better=True: improvement_results[agent_name]
        
        # Патчим конструктор класса TestingMemoryIntegration
        with patch('multi_agent_system.agent_developer.testing_memory_integration.TestingMemoryIntegration', 
                  return_value=testing_integration):
            # Вызываем тестируемую функцию
            result = create_auto_improvement_cycle(
                memory_manager=memory_manager,
                agent_tester=agent_tester,
                agent_optimizer=agent_optimizer,
                version_manager=version_manager,
                data_collector=data_collector
            )
            
            # Проверяем результаты
            self.assertEqual(result["agents_processed"], 3)
            self.assertEqual(result["agents_improved"], 2)
            self.assertEqual(result["agents_deployed"], 1)
            
            # Проверяем, что методы были вызваны с правильными параметрами
            version_manager.get_all_agents.assert_called_once()
            self.assertEqual(testing_integration.improve_agent_from_memory.call_count, 3)


if __name__ == '__main__':
    unittest.main() 