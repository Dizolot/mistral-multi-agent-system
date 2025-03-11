"""
Тесты для модуля телеграм-бота с интеграцией Mistral.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, AsyncMock, call

# Добавляем корневую директорию проекта в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from telegram import Update, User, Message, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ApplicationBuilder

from multi_agent_system.memory.conversation_memory import ConversationMemoryManager
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector
from multi_agent_system.memory.memory_analytics_integration import MemoryAnalyticsIntegration

# Создаем заглушку для LangChainRouter, так как модуль может отсутствовать
class MockLangChainRouter:
    """
    Заглушка для класса LangChainRouter.
    """
    def __init__(self):
        pass
    
    async def route_message(self, message, user_id, history=None):
        return {
            "response": "Response from LangChain Router",
            "agent_name": "mock_agent",
            "processing_time": 0.5
        }

# Патчим импорт LangChainRouter
sys.modules['multi_agent_system.langchain_integration.langchain_router'] = Mock()
sys.modules['multi_agent_system.langchain_integration.langchain_router'].LangChainRouter = MockLangChainRouter

from telegram_bot.mistral_telegram_bot import MistralTelegramBot


class TestMistralTelegramBot(unittest.TestCase):
    """
    Тесты для класса MistralTelegramBot.
    """
    
    def setUp(self):
        """
        Подготовка к тестам.
        """
        # Мокаем компоненты
        self.memory_manager = Mock(spec=ConversationMemoryManager)
        self.data_collector = Mock(spec=AgentDataCollector)
        self.langchain_router = MockLangChainRouter()
        
        # Мокаем класс ApplicationBuilder для создания приложения
        self.app_builder_mock = Mock()
        patcher = patch('telegram.ext.ApplicationBuilder', return_value=self.app_builder_mock)
        self.addCleanup(patcher.stop)
        patcher.start()
        
        # Мокаем методы ApplicationBuilder
        self.app_mock = Mock()
        self.app_builder_mock.token.return_value = self.app_builder_mock
        self.app_builder_mock.build.return_value = self.app_mock
        
        # Создаем бота для тестирования
        self.bot = MistralTelegramBot(
            telegram_token="test_token",
            memory_manager=self.memory_manager,
            data_collector=self.data_collector
        )
        
        # Мокаем LangChainRouter в боте
        self.bot.langchain_router = self.langchain_router
    
    def test_init(self):
        """
        Тест инициализации класса.
        """
        # Создаем экземпляр бота
        bot = MistralTelegramBot(
            telegram_token="test_token",
            memory_manager=self.memory_manager,
            data_collector=self.data_collector
        )
        
        # Проверяем, что атрибуты установлены правильно
        self.assertEqual(bot.telegram_token, "test_token")
        self.assertEqual(bot.memory_manager, self.memory_manager)
        self.assertEqual(bot.data_collector, self.data_collector)
        self.assertTrue(isinstance(bot.memory_analytics, MemoryAnalyticsIntegration))
        self.assertEqual(bot.application, self.app_mock)
        
        # Проверяем, что обработчики команд добавлены
        self.assertEqual(self.app_mock.add_handler.call_count, 12)
        
        # Не проверяем вызов run_polling, так как он может вызываться отдельно
        # self.app_mock.run_polling.assert_called_once()
    
    @patch('telegram.Update')
    @patch('telegram.ext.ContextTypes.DEFAULT_TYPE')
    async def test_start_command(self, mock_context, mock_update):
        """
        Тест команды /start.
        """
        # Настраиваем мок для update
        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.first_name = "Test User"
        
        mock_message = AsyncMock(spec=Message)
        mock_update.effective_user = mock_user
        mock_update.message = mock_message
        
        # Вызываем тестируемый метод
        await self.bot.start_command(mock_update, mock_context)
        
        # Проверяем результаты
        self.memory_manager.add_system_message.assert_called_once()
        mock_message.reply_text.assert_called_once()
    
    @patch('telegram.Update')
    @patch('telegram.ext.ContextTypes.DEFAULT_TYPE')
    async def test_help_command(self, mock_context, mock_update):
        """
        Тест команды /help.
        """
        # Настраиваем мок для update
        mock_message = AsyncMock(spec=Message)
        mock_update.message = mock_message
        
        # Вызываем тестируемый метод
        await self.bot.help_command(mock_update, mock_context)
        
        # Проверяем результаты
        mock_message.reply_text.assert_called_once()
    
    @patch('telegram.Update')
    @patch('telegram.ext.ContextTypes.DEFAULT_TYPE')
    async def test_reset_command(self, mock_context, mock_update):
        """
        Тест команды /reset.
        """
        # Настраиваем мок для update
        mock_user = Mock(spec=User)
        mock_user.id = 123
        
        mock_message = AsyncMock(spec=Message)
        mock_update.effective_user = mock_user
        mock_update.message = mock_message
        
        # Мокаем метод process_conversation_history
        self.bot.memory_analytics.process_conversation_history = Mock(return_value=5)
        
        # Вызываем тестируемый метод
        await self.bot.reset_command(mock_update, mock_context)
        
        # Проверяем результаты
        self.bot.memory_analytics.process_conversation_history.assert_called_once_with(
            user_id="123",
            process_all=True
        )
        self.memory_manager.clear_memory.assert_called_once_with("123")
        mock_message.reply_text.assert_called_once()
    
    @patch('telegram.Update')
    @patch('telegram.ext.ContextTypes.DEFAULT_TYPE')
    async def test_mode_command(self, mock_context, mock_update):
        """
        Тест команды /mode.
        """
        # Настраиваем мок для update
        mock_message = AsyncMock(spec=Message)
        mock_update.message = mock_message
        
        # Вызываем тестируемый метод
        await self.bot.mode_command(mock_update, mock_context)
        
        # Проверяем результаты
        mock_message.reply_text.assert_called_once()
        
        # Проверяем, что в аргументах есть reply_markup
        args, kwargs = mock_message.reply_text.call_args
        self.assertIn("reply_markup", kwargs)
        self.assertTrue(isinstance(kwargs["reply_markup"], InlineKeyboardMarkup))
    
    @patch('telegram.Update')
    @patch('telegram.ext.ContextTypes.DEFAULT_TYPE')
    async def test_handle_callback_mistral(self, mock_context, mock_update):
        """
        Тест обработки колбэка для выбора режима Mistral API.
        """
        # Настраиваем мок для callback_query
        mock_query = AsyncMock()
        mock_query.data = "mode_mistral"
        mock_query.from_user = Mock(spec=User)
        mock_query.from_user.id = 123
        
        mock_update.callback_query = mock_query
        
        # Вызываем тестируемый метод
        await self.bot.handle_callback(mock_update, mock_context)
        
        # Проверяем результаты
        mock_query.answer.assert_called_once()
        mock_query.edit_message_text.assert_called_once_with("Режим работы изменен на Mistral API")
        self.assertFalse(self.bot.use_langchain_router)
    
    @patch('telegram.Update')
    @patch('telegram.ext.ContextTypes.DEFAULT_TYPE')
    async def test_handle_callback_langchain(self, mock_context, mock_update):
        """
        Тест обработки колбэка для выбора режима LangChain Router.
        """
        # Настраиваем мок для callback_query
        mock_query = AsyncMock()
        mock_query.data = "mode_langchain"
        mock_query.from_user = Mock(spec=User)
        mock_query.from_user.id = 123
        
        mock_update.callback_query = mock_query
        
        # Сначала устанавливаем режим Mistral
        self.bot.use_langchain_router = False
        
        # Вызываем тестируемый метод
        await self.bot.handle_callback(mock_update, mock_context)
        
        # Проверяем результаты
        mock_query.answer.assert_called_once()
        mock_query.edit_message_text.assert_called_once_with("Режим работы изменен на LangChain Router")
        self.assertTrue(self.bot.use_langchain_router)
    
    @patch('telegram.Update')
    @patch('telegram.ext.ContextTypes.DEFAULT_TYPE')
    @patch('telegram_bot.mistral_telegram_bot.MistralTelegramBot._send_message_to_mistral')
    async def test_handle_message_mistral_mode(self, mock_send_to_mistral, mock_context, mock_update):
        """
        Тест обработки сообщения в режиме Mistral API.
        """
        # Настраиваем мок для update
        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.first_name = "Test User"
        
        mock_chat = Mock(spec=Chat)
        mock_chat.id = 123
        
        mock_message = AsyncMock(spec=Message)
        mock_message.text = "Test message"
        
        mock_update.effective_user = mock_user
        mock_update.effective_chat = mock_chat
        mock_update.message = mock_message
        
        # Мокаем бота в контексте
        mock_context.bot = AsyncMock()
        
        # Мокаем ответ от Mistral
        mock_send_to_mistral.return_value = {
            "response": "Test response",
            "agent_name": "test_agent",
            "processing_time": 1.0
        }
        
        # Устанавливаем режим Mistral
        self.bot.use_langchain_router = False
        
        # Вызываем тестируемый метод
        await self.bot.handle_message(mock_update, mock_context)
        
        # Проверяем результаты
        self.memory_manager.add_user_message.assert_called_once_with("123", "Test message")
        mock_context.bot.send_chat_action.assert_called_once()
        mock_send_to_mistral.assert_called_once()
        mock_message.reply_text.assert_called_once_with("Test response")
        self.memory_manager.add_ai_message.assert_called_once()


if __name__ == '__main__':
    unittest.main() 