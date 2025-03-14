#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для модуля отслеживания улучшений кода.

Проверяет работу ImprovementTracker и его интеграцию с CodeImprovementAgent.
"""

import os
import sys
import asyncio
import logging
import unittest
import shutil
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.improvement_tracker import ImprovementTracker, CodeVersion, ImprovementSuggestion
from src.agents.code_improvement_agent import CodeImprovementAgent
from src.core.memory_system.memory_manager import MemoryManager
from src.model_service.model_adapter.mistral_adapter import MistralAdapter
from src.core.memory_system.embedding_provider import EmbeddingProvider
from src.utils.logger import setup_logger

# Настройка логирования
logger = setup_logger("test_improvement_tracker")

# Тестовый код
TEST_CODE = """
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

def main():
    n = 10
    print(f"The factorial of {n} is {factorial(n)}")

if __name__ == "__main__":
    main()
"""

IMPROVED_CODE = """
def factorial(n: int) -> int:
    \"\"\"Calculate the factorial of a number.\"\"\"
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

def main() -> None:
    \"\"\"Main function to demonstrate factorial calculation.\"\"\"
    n = 10
    print(f"The factorial of {n} is {factorial(n)}")

if __name__ == "__main__":
    main()
"""

# Тестовые предложения по улучшению
TEST_SUGGESTIONS = [
    {
        "type": "documentation",
        "message": "Добавить документацию к функциям",
        "location": {"line": 1, "column": 1}
    },
    {
        "type": "typing",
        "message": "Добавить типы аргументов и возвращаемых значений",
        "location": {"line": 1, "column": 1}
    }
]

class TestImprovementTracker(unittest.TestCase):
    """Тесты для ImprovementTracker."""
    
    def setUp(self):
        """Подготовка к тестам."""
        # Создаем временную директорию для тестов
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_improvements")
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Создаем трекер улучшений
        self.tracker = ImprovementTracker(self.test_dir)
    
    def tearDown(self):
        """Очистка после тестов."""
        # Удаляем временную директорию
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_code_version(self):
        """Тест класса CodeVersion."""
        version = CodeVersion(code=TEST_CODE)
        
        self.assertEqual(version.code, TEST_CODE)
        self.assertEqual(version.language, "python")
        self.assertIsNotNone(version.version_id)
        self.assertIsNotNone(version.timestamp)
        
        # Проверка хеширования
        self.assertEqual(version.get_hash(), CodeVersion(code=TEST_CODE).get_hash())
        self.assertNotEqual(version.get_hash(), CodeVersion(code=IMPROVED_CODE).get_hash())
    
    def test_improvement_suggestion(self):
        """Тест класса ImprovementSuggestion."""
        suggestion = ImprovementSuggestion(
            type="documentation",
            message="Добавить документацию к функциям"
        )
        
        self.assertEqual(suggestion.type, "documentation")
        self.assertEqual(suggestion.message, "Добавить документацию к функциям")
        self.assertFalse(suggestion.applied)
        
        # Проверка сериализации
        suggestion_dict = suggestion.to_dict()
        self.assertIn("type", suggestion_dict)
        self.assertIn("message", suggestion_dict)
        self.assertIn("applied", suggestion_dict)
    
    def test_track_code(self):
        """Тест отслеживания версий кода."""
        # Выполняем асинхронный тест через event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        version_id = loop.run_until_complete(self.tracker.track_code(TEST_CODE, "test_user"))
        
        self.assertIsNotNone(version_id)
        self.assertIn(version_id, self.tracker.versions)
        self.assertIn("test_user", self.tracker.user_improvements)
        self.assertIn(version_id, self.tracker.user_improvements["test_user"])
        
        # Проверка повторного добавления того же кода (должен быть обнаружен дубликат)
        loop.run_until_complete(self.tracker.track_code(TEST_CODE, "test_user"))
        self.assertEqual(len(self.tracker.user_improvements["test_user"]), 1)
        
        # Проверка добавления другого кода
        version_id2 = loop.run_until_complete(self.tracker.track_code(IMPROVED_CODE, "test_user"))
        self.assertEqual(len(self.tracker.user_improvements["test_user"]), 2)
        
        loop.close()
    
    def test_add_improvement_suggestions(self):
        """Тест добавления предложений по улучшению."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Сначала отслеживаем код
        version_id = loop.run_until_complete(self.tracker.track_code(TEST_CODE, "test_user"))
        
        # Добавляем предложения
        suggestion_ids = loop.run_until_complete(
            self.tracker.add_improvement_suggestions(version_id, TEST_SUGGESTIONS)
        )
        
        self.assertEqual(len(suggestion_ids), len(TEST_SUGGESTIONS))
        self.assertIn(version_id, self.tracker.suggestions)
        self.assertEqual(len(self.tracker.suggestions[version_id]), len(TEST_SUGGESTIONS))
        
        loop.close()
    
    def test_record_improvement_result(self):
        """Тест записи результата улучшения."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Отслеживаем код и добавляем предложения
        version_id = loop.run_until_complete(self.tracker.track_code(TEST_CODE, "test_user"))
        suggestion_ids = loop.run_until_complete(
            self.tracker.add_improvement_suggestions(version_id, TEST_SUGGESTIONS)
        )
        
        # Записываем результат улучшения
        result_id = loop.run_until_complete(
            self.tracker.record_improvement_result(
                version_id,
                IMPROVED_CODE,
                suggestion_ids
            )
        )
        
        self.assertIsNotNone(result_id)
        self.assertIn(result_id, self.tracker.results)
        
        # Проверяем, что предложения отмечены как примененные
        for suggestion in self.tracker.suggestions[version_id]:
            self.assertTrue(suggestion.applied)
        
        # Проверяем, что метрики изменений рассчитаны
        self.assertIsNotNone(self.tracker.results[result_id].metrics_changes)
        
        loop.close()
    
    def test_get_improvement_history(self):
        """Тест получения истории улучшений."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Создаем историю улучшений
        version_id = loop.run_until_complete(self.tracker.track_code(TEST_CODE, "test_user"))
        suggestion_ids = loop.run_until_complete(
            self.tracker.add_improvement_suggestions(version_id, TEST_SUGGESTIONS)
        )
        result_id = loop.run_until_complete(
            self.tracker.record_improvement_result(
                version_id,
                IMPROVED_CODE,
                suggestion_ids
            )
        )
        
        # Получаем историю
        history = self.tracker.get_improvement_history("test_user")
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["result_id"], result_id)
        
        loop.close()
    
    def test_get_code_diff(self):
        """Тест получения разницы между версиями кода."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Создаем две версии кода
        original_id = loop.run_until_complete(self.tracker.track_code(TEST_CODE, "test_user"))
        improved_id = loop.run_until_complete(self.tracker.track_code(IMPROVED_CODE, "test_user"))
        
        # Получаем разницу
        diff = self.tracker.get_code_diff(original_id, improved_id)
        
        self.assertIsInstance(diff, list)
        self.assertGreater(len(diff), 0)
        
        loop.close()
    
    def test_save_and_load_data(self):
        """Тест сохранения и загрузки данных."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Создаем историю улучшений
        version_id = loop.run_until_complete(self.tracker.track_code(TEST_CODE, "test_user"))
        suggestion_ids = loop.run_until_complete(
            self.tracker.add_improvement_suggestions(version_id, TEST_SUGGESTIONS)
        )
        loop.run_until_complete(
            self.tracker.record_improvement_result(
                version_id,
                IMPROVED_CODE,
                suggestion_ids
            )
        )
        
        # Сохраняем данные
        self.tracker._save_data()
        
        # Создаем новый трекер и загружаем данные
        new_tracker = ImprovementTracker(self.test_dir)
        
        # Проверяем, что данные загружены
        self.assertIn(version_id, new_tracker.versions)
        self.assertIn(version_id, new_tracker.suggestions)
        self.assertEqual(len(new_tracker.results), 1)
        
        loop.close()

class MockEmbeddingProvider(EmbeddingProvider):
    """Мок-класс для EmbeddingProvider для тестирования."""
    
    def __init__(self, model_name: str = "mock-model"):
        """
        Инициализация мок-провайдера эмбеддингов.
        
        Args:
            model_name: Имя модели
        """
        super().__init__(model_name)
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Мок-метод для получения нескольких эмбеддингов.
        
        Args:
            texts: Список текстов для эмбеддинга
            
        Returns:
            List[List[float]]: Список мок-эмбеддингов
        """
        # Возвращаем список мок-эмбеддингов
        return [[0.1] * 384 for _ in texts]
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Мок-метод для получения эмбеддинга.
        
        Args:
            text: Текст для эмбеддинга
            
        Returns:
            List[float]: Мок-эмбеддинг
        """
        # Возвращаем простой мок-эмбеддинг фиксированной длины
        return [0.1] * 384  # Стандартная длина эмбеддинга
    
    def get_embedding_dimension(self) -> int:
        """
        Возвращает размерность эмбеддинга.
        
        Returns:
            int: Размерность эмбеддинга
        """
        return 384

class TestIntegration(unittest.TestCase):
    """Интеграционные тесты для ImprovementTracker и CodeImprovementAgent."""
    
    def setUp(self):
        """Подготовка к тестам."""
        # Создаем временную директорию для тестов
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_integration")
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Создаем мок-провайдер эмбеддингов
        embedding_provider = MockEmbeddingProvider()
        
        # Создаем менеджер памяти с трекером улучшений
        self.memory_manager = MemoryManager(
            storage_dir=self.test_dir,
            embedding_provider=embedding_provider
        )
        
        # Создаем мок-адаптер модели
        self.model_adapter = MockMistralAdapter()
        
        # Создаем агента улучшения кода
        self.agent = CodeImprovementAgent(
            model_adapter=self.model_adapter,
            memory_manager=self.memory_manager
        )
    
    def tearDown(self):
        """Очистка после тестов."""
        # Удаляем временную директорию
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_agent_workflow(self):
        """Тест полного рабочего процесса агента."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Контекст с идентификатором пользователя
        context = {"user_id": "test_user", "language": "python"}
        
        # Анализируем код
        analysis_result = loop.run_until_complete(self.agent.analyze_code(TEST_CODE, context))
        
        # Проверяем, что версия кода сохранена
        self.assertIsNotNone(context.get("version_id"))
        
        # Предлагаем улучшения
        improvements = loop.run_until_complete(
            self.agent.suggest_improvements(TEST_CODE, analysis_result, context)
        )
        
        # Проверяем, что предложения сохранены
        self.assertIsNotNone(context.get("suggestion_ids"))
        
        # Применяем улучшения
        improved_code = loop.run_until_complete(
            self.agent.apply_improvements(TEST_CODE, improvements, context)
        )
        
        # Проверяем, что результат улучшения сохранен
        self.assertIsNotNone(context.get("result_id"))
        
        # Получаем историю улучшений
        history = loop.run_until_complete(self.agent.get_improvement_history("test_user"))
        
        # Проверяем, что история не пуста
        self.assertEqual(len(history), 1)
        
        loop.close()

class MockMistralAdapter(MistralAdapter):
    """Мок-класс для MistralAdapter для тестирования."""
    
    def __init__(self):
        """Инициализация мок-адаптера."""
        # Не вызываем родительский __init__ для избежания запросов к API
        self.model_name = "mock-model"
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Мок-метод для генерации текста.
        
        Args:
            prompt: Промпт для генерации
            **kwargs: Дополнительные параметры
            
        Returns:
            str: Сгенерированный текст
        """
        # Всегда возвращаем улучшенный код
        return IMPROVED_CODE
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Мок-метод для получения эмбеддинга.
        
        Args:
            text: Текст для эмбеддинга
            
        Returns:
            List[float]: Мок-эмбеддинг
        """
        # Возвращаем простой мок-эмбеддинг фиксированной длины
        return [0.1] * 384  # Стандартная длина эмбеддинга Mistral
    
    def get_embedding_dimension(self) -> int:
        """
        Возвращает размерность эмбеддинга.
        
        Returns:
            int: Размерность эмбеддинга
        """
        return 384  # Стандартная длина эмбеддинга Mistral

if __name__ == "__main__":
    unittest.main() 