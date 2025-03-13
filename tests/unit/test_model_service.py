"""
Модульные тесты для сервиса моделей с унифицированным API.
"""

import asyncio
import unittest
import os
import sys
import json
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict, Any, Optional

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/model_service_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Импорты модулей, которые будут разработаны
try:
    from src.model_service.service import ModelService
    from src.model_service.model_adapter import ModelAdapter, MistralAdapter
    from src.model_service.load_balancer import LoadBalancer
    from src.model_service.caching import ResponseCache
    from src.model_service.metrics import MetricsCollector
except ImportError:
    logger.warning("Модули сервиса моделей еще не реализованы. Тесты используются для TDD.")
    # Создаем заглушки для классов
    class ModelService:
        pass
        
    class ModelAdapter:
        pass
        
    class MistralAdapter(ModelAdapter):
        pass
        
    class LoadBalancer:
        pass
        
    class ResponseCache:
        pass
        
    class MetricsCollector:
        pass

class TestModelAdapter(unittest.TestCase):
    """
    Тесты для адаптеров моделей.
    """
    
    def test_adapter_interface(self):
        """Тест интерфейса базового адаптера"""
        adapter = ModelAdapter()
        
        # Проверяем наличие необходимых методов
        self.assertTrue(hasattr(adapter, "generate"))
        self.assertTrue(hasattr(adapter, "chat"))
        self.assertTrue(hasattr(adapter, "embeddings"))
        self.assertTrue(hasattr(adapter, "get_model_info"))
        
        logger.info("Тест интерфейса базового адаптера успешно пройден")
    
    async def test_mistral_adapter(self):
        """Тест адаптера для Mistral API"""
        # Создаем адаптер с мок-клиентом
        adapter = MistralAdapter(
            base_url="http://139.59.241.176:8000",
            model_name="mistral-small",
            timeout=10,
            api_key=""  # API ключ не требуется для локальной модели
        )
        
        # Мокируем метод execute_request
        adapter._execute_request = AsyncMock(return_value={
            "id": "test-id",
            "choices": [{"message": {"content": "Тестовый ответ модели"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        })
        
        # Тестируем метод chat
        result = await adapter.chat(
            messages=[{"role": "user", "content": "Привет"}],
            temperature=0.7,
            max_tokens=100
        )
        
        # Проверяем, что результат содержит ожидаемые поля
        self.assertIn("text", result)
        self.assertIn("usage", result)
        self.assertEqual(result["text"], "Тестовый ответ модели")
        
        logger.info("Тест адаптера Mistral успешно пройден")
    
    @patch("httpx.AsyncClient.post")
    async def test_mistral_adapter_error_handling(self, mock_post):
        """Тест обработки ошибок в адаптере Mistral"""
        # Настраиваем мок для возврата ошибки
        mock_post.side_effect = Exception("Ошибка подключения")
        
        # Создаем адаптер
        adapter = MistralAdapter(
            base_url="http://139.59.241.176:8000",
            model_name="mistral-small",
            timeout=10
        )
        
        try:
            # Вызываем метод, который должен обрабатывать ошибки
            result = await adapter.chat(
                messages=[{"role": "user", "content": "Привет"}]
            )
            
            # Проверяем, что результат содержит информацию об ошибке
            self.assertIn("error", result)
            self.assertIn("Ошибка подключения", result["error"])
        except Exception as e:
            self.fail(f"Адаптер не обрабатывает исключения: {str(e)}")
        
        logger.info("Тест обработки ошибок в адаптере Mistral успешно пройден")

class TestModelService(unittest.TestCase):
    """
    Тесты для унифицированного сервиса моделей.
    """
    
    def setUp(self):
        """Подготовка для тестов"""
        # Создаем мок-адаптеры
        self.mistral_adapter = MagicMock()
        self.mistral_adapter.chat = AsyncMock(return_value={
            "text": "Ответ от Mistral",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        })
        
        # Создаем экземпляр сервиса с мок-адаптерами
        self.model_service = ModelService()
        self.model_service.register_adapter("mistral", self.mistral_adapter)
        
        logger.info("Настройка тестового окружения завершена")
    
    async def test_default_model_selection(self):
        """Тест выбора модели по умолчанию"""
        # Вызываем метод chat без указания модели
        result = await self.model_service.chat(
            messages=[{"role": "user", "content": "Привет"}]
        )
        
        # Проверяем, что был использован Mistral адаптер
        self.mistral_adapter.chat.assert_called_once()
        self.assertIn("text", result)
        self.assertEqual(result["text"], "Ответ от Mistral")
        
        logger.info("Тест выбора модели по умолчанию успешно пройден")
    
    async def test_model_specification(self):
        """Тест явного указания модели"""
        # Регистрируем дополнительный адаптер
        another_adapter = MagicMock()
        another_adapter.chat = AsyncMock(return_value={
            "text": "Ответ от другой модели",
            "usage": {"prompt_tokens": 5, "completion_tokens": 10}
        })
        self.model_service.register_adapter("another-model", another_adapter)
        
        # Вызываем метод chat с явным указанием модели
        result = await self.model_service.chat(
            messages=[{"role": "user", "content": "Привет"}],
            model="another-model"
        )
        
        # Проверяем, что был использован другой адаптер
        another_adapter.chat.assert_called_once()
        self.assertIn("text", result)
        self.assertEqual(result["text"], "Ответ от другой модели")
        
        logger.info("Тест явного указания модели успешно пройден")
    
    async def test_parameter_passing(self):
        """Тест передачи параметров в адаптер"""
        # Вызываем метод chat с дополнительными параметрами
        await self.model_service.chat(
            messages=[{"role": "user", "content": "Привет"}],
            temperature=0.5,
            max_tokens=200,
            top_p=0.9
        )
        
        # Проверяем, что параметры правильно переданы в адаптер
        self.mistral_adapter.chat.assert_called_once()
        args, kwargs = self.mistral_adapter.chat.call_args
        self.assertEqual(kwargs["temperature"], 0.5)
        self.assertEqual(kwargs["max_tokens"], 200)
        self.assertEqual(kwargs["top_p"], 0.9)
        
        logger.info("Тест передачи параметров успешно пройден")

class TestLoadBalancer(unittest.TestCase):
    """
    Тесты для системы балансировки нагрузки.
    """
    
    def setUp(self):
        """Подготовка для тестов"""
        # Создаем мок-адаптеры
        self.adapter1 = MagicMock()
        self.adapter1.chat = AsyncMock(return_value={"text": "Ответ от адаптера 1"})
        self.adapter1.get_model_info = MagicMock(return_value={"name": "mistral-1", "max_tokens": 8000})
        
        self.adapter2 = MagicMock()
        self.adapter2.chat = AsyncMock(return_value={"text": "Ответ от адаптера 2"})
        self.adapter2.get_model_info = MagicMock(return_value={"name": "mistral-2", "max_tokens": 8000})
        
        # Создаем балансировщик
        self.load_balancer = LoadBalancer()
        self.load_balancer.register_instance("mistral", self.adapter1, weight=1)
        self.load_balancer.register_instance("mistral", self.adapter2, weight=1)
        
        logger.info("Настройка тестового окружения завершена")
    
    async def test_round_robin_balancing(self):
        """Тест балансировки запросов по принципу Round Robin"""
        # Выполняем несколько запросов
        results = []
        for _ in range(4):
            result = await self.load_balancer.execute(
                "mistral",
                "chat",
                messages=[{"role": "user", "content": "Тест"}]
            )
            results.append(result["text"])
        
        # Проверяем, что запросы распределены между адаптерами
        self.assertEqual(self.adapter1.chat.call_count, 2)
        self.assertEqual(self.adapter2.chat.call_count, 2)
        
        # Проверяем чередование ответов
        self.assertEqual(results, ["Ответ от адаптера 1", "Ответ от адаптера 2", "Ответ от адаптера 1", "Ответ от адаптера 2"])
        
        logger.info("Тест балансировки Round Robin успешно пройден")
    
    async def test_weighted_balancing(self):
        """Тест балансировки с учетом весов"""
        # Обновляем веса адаптеров (2:1)
        self.load_balancer.update_instance_weight("mistral", self.adapter1, 2)
        self.load_balancer.update_instance_weight("mistral", self.adapter2, 1)
        
        # Выполняем несколько запросов
        for _ in range(3):
            await self.load_balancer.execute(
                "mistral",
                "chat",
                messages=[{"role": "user", "content": "Тест"}]
            )
        
        # Проверяем распределение нагрузки в соответствии с весами
        self.assertEqual(self.adapter1.chat.call_count, 2)
        self.assertEqual(self.adapter2.chat.call_count, 1)
        
        logger.info("Тест взвешенной балансировки успешно пройден")
    
    async def test_failover(self):
        """Тест отказоустойчивости при недоступности экземпляра"""
        # Настраиваем первый адаптер на возврат ошибки
        self.adapter1.chat.side_effect = Exception("Ошибка сервера")
        
        # Выполняем запрос
        result = await self.load_balancer.execute(
            "mistral",
            "chat",
            messages=[{"role": "user", "content": "Тест"}]
        )
        
        # Проверяем, что запрос был перенаправлен на второй адаптер
        self.assertEqual(result["text"], "Ответ от адаптера 2")
        
        logger.info("Тест отказоустойчивости успешно пройден")

class TestCaching(unittest.TestCase):
    """
    Тесты для системы кэширования.
    """
    
    def setUp(self):
        """Подготовка для тестов"""
        # Инициализируем кэш
        self.cache = ResponseCache(max_size=100, ttl=300)
        
        logger.info("Настройка тестового окружения завершена")
    
    def test_cache_hit(self):
        """Тест попадания в кэш"""
        # Добавляем запись в кэш
        messages = [{"role": "user", "content": "Привет"}]
        model = "mistral"
        params = {"temperature": 0.7, "max_tokens": 100}
        expected_response = {"text": "Привет, как дела?", "usage": {"prompt_tokens": 5, "completion_tokens": 10}}
        
        self.cache.set(messages, model, params, expected_response)
        
        # Проверяем наличие записи в кэше
        result = self.cache.get(messages, model, params)
        self.assertIsNotNone(result)
        self.assertEqual(result, expected_response)
        
        logger.info("Тест попадания в кэш успешно пройден")
    
    def test_cache_miss(self):
        """Тест промаха в кэше"""
        # Запрашиваем запись, которой нет в кэше
        messages = [{"role": "user", "content": "Неизвестный запрос"}]
        model = "mistral"
        params = {"temperature": 0.7, "max_tokens": 100}
        
        result = self.cache.get(messages, model, params)
        self.assertIsNone(result)
        
        logger.info("Тест промаха в кэше успешно пройден")
    
    def test_parameter_sensitivity(self):
        """Тест чувствительности к параметрам"""
        # Добавляем запись в кэш
        messages = [{"role": "user", "content": "Привет"}]
        model = "mistral"
        params1 = {"temperature": 0.7, "max_tokens": 100}
        params2 = {"temperature": 0.8, "max_tokens": 100}  # Другое значение температуры
        response = {"text": "Ответ", "usage": {"prompt_tokens": 5, "completion_tokens": 10}}
        
        self.cache.set(messages, model, params1, response)
        
        # Запрашиваем с другими параметрами
        result = self.cache.get(messages, model, params2)
        self.assertIsNone(result)  # Результат должен быть None, так как параметры отличаются
        
        logger.info("Тест чувствительности к параметрам успешно пройден")
    
    def test_cache_eviction(self):
        """Тест вытеснения из кэша по размеру"""
        # Создаем кэш с ограниченным размером
        small_cache = ResponseCache(max_size=2, ttl=300)
        
        # Добавляем записи в кэш
        for i in range(3):
            messages = [{"role": "user", "content": f"Запрос {i}"}]
            model = "mistral"
            params = {"temperature": 0.7}
            response = {"text": f"Ответ {i}"}
            
            small_cache.set(messages, model, params, response)
        
        # Проверяем, что первая запись вытеснена из кэша
        result = small_cache.get([{"role": "user", "content": "Запрос 0"}], "mistral", {"temperature": 0.7})
        self.assertIsNone(result)
        
        # Но последняя запись должна быть доступна
        result = small_cache.get([{"role": "user", "content": "Запрос 2"}], "mistral", {"temperature": 0.7})
        self.assertIsNotNone(result)
        
        logger.info("Тест вытеснения из кэша успешно пройден")

async def run_async_tests():
    """
    Запуск асинхронных тестов
    """
    # Тесты для адаптера модели
    test_adapter = TestModelAdapter()
    await test_adapter.test_mistral_adapter()
    await test_adapter.test_mistral_adapter_error_handling()
    
    # Тесты для сервиса моделей
    test_service = TestModelService()
    test_service.setUp()
    await test_service.test_default_model_selection()
    await test_service.test_model_specification()
    await test_service.test_parameter_passing()
    
    # Тесты для балансировщика нагрузки
    test_balancer = TestLoadBalancer()
    test_balancer.setUp()
    await test_balancer.test_round_robin_balancing()
    await test_balancer.test_weighted_balancing()
    await test_balancer.test_failover()

def main():
    """
    Основная функция для запуска всех тестов
    """
    # Запускаем синхронные тесты
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    # Запускаем асинхронные тесты
    asyncio.run(run_async_tests())

if __name__ == "__main__":
    main() 