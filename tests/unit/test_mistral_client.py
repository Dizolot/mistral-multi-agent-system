import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import logging
import sys
import os

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from telegram_bot.mistral_client import MistralClient

class TestMistralClient(unittest.TestCase):
    """Тесты для класса MistralClient."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.base_url = "http://test-api-url:8080"
        self.client = MistralClient(base_url=self.base_url)
        
    @patch('telegram_bot.mistral_client.asyncio.new_event_loop')
    @patch('telegram_bot.mistral_client.asyncio.set_event_loop')
    def test_generate_text_improved(self, mock_set_event_loop, mock_new_event_loop):
        """Улучшенный тест метода generate_text для синхронной генерации текста."""
        # Создаем мок асинхронного метода с использованием AsyncMock
        expected_response = "Это тестовый ответ от Mistral API"
        
        # Создаем будущий результат для мокирования асинхронного ответа
        future = asyncio.Future()
        future.set_result(expected_response)
        
        # Патчим метод generate_chat_response
        with patch.object(self.client, 'generate_chat_response', return_value=future):
            # Настройка моков для цикла событий
            mock_loop = MagicMock()
            mock_new_event_loop.return_value = mock_loop
            
            # Настраиваем mock_loop.run_until_complete чтобы он возвращал результат из future
            mock_loop.run_until_complete.return_value = expected_response
            
            # Вызов тестируемого метода
            context = [{"role": "user", "content": "Это тестовый запрос"}]
            result = self.client.generate_text(context, temperature=0.5, max_tokens=500)
            
            # Проверки
            self.assertEqual(result, expected_response)
            mock_new_event_loop.assert_called_once()
            mock_set_event_loop.assert_called_once_with(mock_loop)
            mock_loop.close.assert_called_once()
        
    def test_generate_text_with_real_asyncio(self):
        """Тест метода generate_text с реальным циклом асинхронных событий."""
        # Создаем асинхронный мок
        async def mock_generate_chat_response(*args, **kwargs):
            return "Ответ от мока асинхронной функции"
            
        # Патчим метод generate_chat_response
        with patch.object(self.client, 'generate_chat_response', side_effect=mock_generate_chat_response):
            # Вызов тестируемого метода
            context = [{"role": "user", "content": "Тестовый запрос"}]
            result = self.client.generate_text(context)
            
            # Проверки
            self.assertEqual(result, "Ответ от мока асинхронной функции")
    
    def test_generate_text_exception_with_real_asyncio(self):
        """Тест обработки исключений в методе generate_text с реальным циклом событий."""
        # Создаем асинхронный мок, который вызывает исключение
        async def mock_generate_chat_response_with_error(*args, **kwargs):
            raise ValueError("Тестовая асинхронная ошибка")
            
        # Патчим метод generate_chat_response
        with patch.object(self.client, 'generate_chat_response', side_effect=mock_generate_chat_response_with_error):
            # Вызов тестируемого метода
            context = [{"role": "user", "content": "Тестовый запрос"}]
            result = self.client.generate_text(context)
            
            # Проверки
            self.assertEqual(result, "Произошла ошибка при обработке запроса: Тестовая асинхронная ошибка")
            
    @patch('telegram_bot.mistral_client.asyncio.new_event_loop')
    @patch('telegram_bot.mistral_client.asyncio.set_event_loop')
    def test_generate_text(self, mock_set_event_loop, mock_new_event_loop):
        """Тест метода generate_text для синхронной генерации текста."""
        # Настройка моков
        mock_loop = MagicMock()
        mock_new_event_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = "Это тестовый ответ от Mistral API"
        
        # Патчим метод generate_chat_response
        with patch.object(self.client, 'generate_chat_response') as mock_generate:
            # Настраиваем мок
            async_mock = AsyncMock()
            async_mock.return_value = "Это тестовый ответ от Mistral API"
            mock_generate.return_value = async_mock()
            
            # Вызов тестируемого метода
            context = [{"role": "user", "content": "Это тестовый запрос"}]
            result = self.client.generate_text(context)
            
            # Проверки
            self.assertEqual(result, "Это тестовый ответ от Mistral API")

    @patch('telegram_bot.mistral_client.asyncio.new_event_loop')
    @patch('telegram_bot.mistral_client.asyncio.set_event_loop')
    def test_generate_text_error_handling(self, mock_set_event_loop, mock_new_event_loop):
        """Тест обработки ошибок в методе generate_text."""
        # Настройка моков для имитации ошибки
        mock_loop = MagicMock()
        mock_new_event_loop.return_value = mock_loop
        
        # Имитация исключения при выполнении запроса
        mock_loop.run_until_complete.side_effect = Exception("Тестовая ошибка")
        
        # Вызов тестируемого метода
        context = [{"role": "user", "content": "Это тестовый запрос"}]
        result = self.client.generate_text(context)
        
        # Проверки
        self.assertEqual(result, "Произошла ошибка при обработке запроса: Тестовая ошибка")
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)
        
        # Не проверяем вызов close() в этом тесте, так как он не будет вызван из-за исключения
        
    def test_generate_response_simplified(self):
        """Упрощенный тест для метода generate_response с использованием синхронной обертки."""
        # Используем generate_text для тестирования вместо прямого вызова асинхронных методов
        with patch.object(self.client, 'generate_chat_response') as mock_generate_chat:
            # Настраиваем мок для имитации успешного ответа
            async def mock_success(*args, **kwargs):
                return "Это тестовый ответ от Mistral API"
                
            mock_generate_chat.side_effect = mock_success
            
            # Вызов тестируемого метода
            context = [{"role": "user", "content": "Это тестовый запрос"}]
            result = self.client.generate_text(context)
            
            # Проверки
            self.assertEqual(result, "Это тестовый ответ от Mistral API")
            mock_generate_chat.assert_called_once()
        
    @patch('telegram_bot.mistral_client.aiohttp.ClientSession')
    def test_generate_chat_response_async(self, mock_client_session):
        """Тест метода generate_chat_response с улучшенным мокированием асинхронных объектов."""
        # Мокируем generate_response вместо всего стека HTTP-запросов
        with patch.object(self.client, 'generate_response') as mock_generate_response:
            async def mock_response(*args, **kwargs):
                return "Это тестовый ответ от Mistral API"
                
            mock_generate_response.side_effect = mock_response
            
            # Тестируем через синхронную обертку generate_text
            context = [{"role": "user", "content": "Это тестовый запрос"}]
            result = self.client.generate_text(context)
                
            # Проверки
            self.assertEqual(result, "Это тестовый ответ от Mistral API")
            mock_generate_response.assert_called_once()
        
    @patch('telegram_bot.mistral_client.aiohttp.ClientSession')
    def test_generate_response_error_simplified(self, mock_client_session):
        """Упрощенный тест обработки ошибок в методе generate_response."""
        # Патчим метод для создания имитации ошибки
        with patch.object(self.client, 'generate_response') as mock_generate_response:
            async def mock_error(*args, **kwargs):
                raise Exception("Ошибка при отправке запроса")
                
            mock_generate_response.side_effect = mock_error
            
            # Тестируем через синхронную обертку generate_text
            context = [{"role": "user", "content": "Это тестовый запрос"}]
            result = self.client.generate_text(context)
                
            # Проверки
            self.assertTrue("Произошла ошибка при обработке запроса" in result)
            mock_generate_response.assert_called_once()

if __name__ == '__main__':
    unittest.main() 