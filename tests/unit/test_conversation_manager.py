"""
Тесты для модуля conversation_manager.py
"""

import unittest
from typing import Dict, List

from telegram_bot.conversation_manager import ConversationManager, Conversation


class TestConversationManager(unittest.TestCase):
    """Тесты для класса ConversationManager."""
    
    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.manager = ConversationManager()
    
    def test_get_conversation_history_with_int_user_id(self):
        """Тест получения истории с числовым user_id."""
        user_id = 123456
        
        # Добавляем сообщения
        self.manager.add_user_message(user_id, "Привет!")
        self.manager.add_assistant_message(user_id, "Здравствуйте! Чем могу помочь?")
        self.manager.add_user_message(user_id, "Как дела?")
        
        # Получаем историю через get_conversation_history с числовым user_id
        history = self.manager.get_conversation_history(str(user_id))
        
        # Проверяем, что история содержит все сообщения
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Привет!")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "Здравствуйте! Чем могу помочь?")
        self.assertEqual(history[2]["role"], "user")
        self.assertEqual(history[2]["content"], "Как дела?")
    
    def test_get_conversation_history_with_string_user_id(self):
        """Тест получения истории с строковым user_id, который невозможно преобразовать в число."""
        user_id = "test_user"
        
        try:
            # Пытаемся добавить сообщения с строковым user_id
            # Это может вызвать исключение, если метод get_conversation не обрабатывает строковые идентификаторы
            self.manager.add_user_message(user_id, "Привет!") 
            self.manager.add_assistant_message(user_id, "Здравствуйте!")
            
            # Получаем историю
            history = self.manager.get_conversation_history(user_id)
            
            # Проверяем историю
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["role"], "user")
            self.assertEqual(history[0]["content"], "Привет!")
            self.assertEqual(history[1]["role"], "assistant")
            self.assertEqual(history[1]["content"], "Здравствуйте!")
        except Exception as e:
            self.fail(f"Тест вызвал исключение: {str(e)}")
    
    def test_get_conversation_history_empty(self):
        """Тест получения пустой истории."""
        user_id = "789"
        
        # Получаем историю для пользователя, который не добавлял сообщений
        history = self.manager.get_conversation_history(user_id)
        
        # Проверяем, что история пуста
        self.assertEqual(len(history), 0)
    
    def test_get_chat_history_for_langchain_format(self):
        """Тест функции get_chat_history_for_langchain."""
        # Импортируем функцию и глобальный экземпляр conversation_manager
        from multi_agent_system.api_server import get_chat_history_for_langchain, conversation_manager
        
        user_id = "12345"
        
        # Добавляем сообщения в глобальный экземпляр conversation_manager
        conversation_manager.add_user_message(int(user_id), "Привет!")
        conversation_manager.add_assistant_message(int(user_id), "Здравствуйте! Чем могу помочь?")
        
        # Получаем историю в формате LangChain
        history = get_chat_history_for_langchain(user_id)
        
        # Проверяем формат
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["type"], "human")
        self.assertEqual(history[0]["content"], "Привет!")
        self.assertEqual(history[1]["type"], "ai")
        self.assertEqual(history[1]["content"], "Здравствуйте! Чем могу помочь?")
        
        # Очищаем историю после теста
        conversation_manager.reset_conversation(int(user_id))


if __name__ == "__main__":
    unittest.main() 