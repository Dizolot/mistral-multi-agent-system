#!/usr/bin/env python3
"""
Скрипт для запуска тестов интеграции памяти с маршрутизатором LangChain.
"""

import os
import sys
import unittest
import logging

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_tests():
    """Запуск тестов интеграции памяти с маршрутизатором"""
    logger.info("Запуск тестов интеграции памяти с маршрутизатором LangChain")
    
    # Импортируем тесты
    from tests.test_langchain_memory_integration import TestLangChainMemoryIntegration
    
    # Создаем набор тестов
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestLangChainMemoryIntegration)
    
    # Запускаем тесты
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Проверяем результаты
    if result.wasSuccessful():
        logger.info("Все тесты успешно пройдены!")
        return 0
    else:
        logger.error(f"Тесты завершены с ошибками: {len(result.errors)} ошибок, {len(result.failures)} неудач")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests()) 