"""
Тесты для проверки интеграции обновленной системы памяти.
"""

import asyncio
import unittest
import os
import sys
import uuid
import logging
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Создаем директорию для логов
os.makedirs('logs', exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/memory_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Импорты модулей системы
from src.core.memory_system.memory_manager import MemoryManager
from src.core.memory_system.buffer_memory import BufferMemory
from src.core.memory_system.summary_memory import SummaryMemory

class TestMemoryIntegration(unittest.TestCase):
    """
    Тесты для проверки интеграции обновленной системы памяти.
    """
    
    def setUp(self):
        """Подготовка для тестов"""
        # Создаем временную директорию для хранения памяти
        self.test_storage_dir = f"test_memory_storage_{uuid.uuid4().hex}"
        os.makedirs(self.test_storage_dir, exist_ok=True)
        
        # Инициализируем менеджер памяти
        self.memory_manager = MemoryManager(
            storage_dir=self.test_storage_dir,
            max_buffer_length=5
        )
        
        logger.info("Настройка тестового окружения завершена")
    
    def tearDown(self):
        """Очистка после тестов"""
        # Удаляем временную директорию
        import shutil
        if os.path.exists(self.test_storage_dir):
            shutil.rmtree(self.test_storage_dir)
        
        logger.info("Очистка тестового окружения завершена")
    
    def test_add_message_to_buffer(self):
        """Тест добавления сообщений в буферную память"""
        user_id = "test_user_1"
        
        # Добавляем сообщения
        self.memory_manager.add_message(user_id, "user", "Привет, как дела?")
        self.memory_manager.add_message(user_id, "assistant", "Привет! У меня все хорошо. Чем могу помочь?")
        self.memory_manager.add_message(user_id, "user", "Расскажи о погоде")
        
        # Получаем историю
        history = self.memory_manager.get_conversation_history(user_id)
        
        # Проверяем, что история содержит добавленные сообщения
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Привет, как дела?")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[2]["role"], "user")
        self.assertEqual(history[2]["content"], "Расскажи о погоде")
        
        logger.info("Тест добавления сообщений в буферную память успешно пройден")
    
    def test_buffer_trimming(self):
        """Тест обрезки буфера при превышении максимальной длины"""
        user_id = "test_user_2"
        
        # Добавляем 7 сообщений (больше максимальной длины буфера)
        for i in range(7):
            self.memory_manager.add_message(user_id, "user" if i % 2 == 0 else "assistant", f"Сообщение {i}")
        
        # Получаем историю
        history = self.memory_manager.get_conversation_history(user_id)
        
        # Проверяем, что буфер обрезан до 5 сообщений
        self.assertEqual(len(history), 5)
        self.assertEqual(history[0]["content"], "Сообщение 2")
        self.assertEqual(history[4]["content"], "Сообщение 6")
        
        logger.info("Тест обрезки буфера успешно пройден")
    
    def test_summary_generation(self):
        """Тест генерации и обновления саммари"""
        user_id = "test_user_3"
        
        # Мокируем метод сжатия истории
        original_summarize = self.memory_manager.summarize_conversation
        self.memory_manager.summarize_conversation = MagicMock(return_value="Краткое содержание диалога")
        
        # Добавляем сообщения
        for i in range(10):
            self.memory_manager.add_message(user_id, "user" if i % 2 == 0 else "assistant", f"Длинное сообщение {i} " + "текст " * 20)
        
        # Получаем полную историю с саммари
        full_history = self.memory_manager.get_full_conversation_history(user_id)
        
        # Проверяем наличие саммари
        self.assertIn("Краткое содержание диалога", str(full_history))
        
        # Восстанавливаем оригинальный метод
        self.memory_manager.summarize_conversation = original_summarize
        
        logger.info("Тест генерации саммари успешно пройден")
    
    def test_reset_memory(self):
        """Тест сброса памяти пользователя"""
        user_id = "test_user_4"
        
        # Добавляем сообщения
        for i in range(5):
            self.memory_manager.add_message(user_id, "user" if i % 2 == 0 else "assistant", f"Сообщение {i}")
        
        # Проверяем, что история не пуста
        self.assertNotEqual(len(self.memory_manager.get_conversation_history(user_id)), 0)
        
        # Сбрасываем память
        self.memory_manager.reset_memory(user_id)
        
        # Проверяем, что история пуста
        self.assertEqual(len(self.memory_manager.get_conversation_history(user_id)), 0)
        
        logger.info("Тест сброса памяти успешно пройден")
    
    @patch('src.core.memory_system.memory_manager.MemoryManager.save_to_file')
    def test_error_handling(self, mock_save):
        """Тест обработки ошибок при сохранении"""
        user_id = "test_user_5"
        
        # Мокируем метод сохранения, чтобы он вызывал исключение
        mock_save.side_effect = Exception("Ошибка сохранения")
        
        # Добавляем сообщение
        try:
            self.memory_manager.add_message(user_id, "user", "Тестовое сообщение")
            # Если мы здесь, то исключение перехвачено и обработано
            self.assertTrue(True)
        except Exception:
            self.fail("add_message не должен пробрасывать исключение")
        
        logger.info("Тест обработки ошибок успешно пройден")

async def run_tests():
    """Асинхронный запуск тестов"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMemoryIntegration)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1) 