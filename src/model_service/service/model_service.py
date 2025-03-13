"""
Основной сервис моделей с унифицированным API.
Обеспечивает единый интерфейс для работы с различными языковыми моделями.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union, Type

from ..model_adapter.model_adapter import ModelAdapter
from ..load_balancer.load_balancer import LoadBalancer
from ..caching.response_cache import ResponseCache
from ..metrics.metrics_collector import MetricsCollector

# Настройка логирования
logger = logging.getLogger(__name__)


class ModelService:
    """
    Унифицированный сервис моделей, предоставляющий единый интерфейс для работы
    с различными языковыми моделями через систему адаптеров, балансировку нагрузки и кэширование.
    """

    def __init__(
        self,
        default_model: str = "mistral",
        cache_size: int = 1000,
        cache_ttl: int = 3600,
        metrics_dir: str = "logs/metrics"
    ):
        """
        Инициализирует сервис моделей.

        Args:
            default_model: Модель по умолчанию
            cache_size: Размер кэша (количество элементов)
            cache_ttl: Время жизни кэша в секундах
            metrics_dir: Директория для сохранения метрик
        """
        self.default_model = default_model
        self.adapters = {}  # {model_name: adapter}
        
        # Инициализируем компоненты
        self.load_balancer = LoadBalancer()
        self.cache = ResponseCache(max_size=cache_size, ttl=cache_ttl)
        self.metrics = MetricsCollector(metrics_dir=metrics_dir)
        
        logger.info(f"Инициализирован сервис моделей с моделью по умолчанию: {default_model}")

    def register_adapter(self, model_name: str, adapter: ModelAdapter) -> None:
        """
        Регистрирует адаптер модели в сервисе.

        Args:
            model_name: Имя модели
            adapter: Экземпляр адаптера модели
        """
        if model_name in self.adapters:
            # Если адаптер для этой модели уже зарегистрирован, добавляем его в балансировщик
            self.load_balancer.register_instance(model_name, adapter)
            logger.info(f"Добавлен дополнительный экземпляр модели {model_name} в балансировщик")
        else:
            # Если это первый адаптер для модели, сохраняем его и регистрируем в балансировщике
            self.adapters[model_name] = adapter
            self.load_balancer.register_instance(model_name, adapter)
            logger.info(f"Зарегистрирована новая модель {model_name}")

    def unregister_adapter(self, model_name: str, adapter: Optional[ModelAdapter] = None) -> bool:
        """
        Удаляет адаптер модели из сервиса.

        Args:
            model_name: Имя модели
            adapter: Экземпляр адаптера модели (если None, удаляются все адаптеры для модели)

        Returns:
            True, если адаптер был успешно удален, иначе False
        """
        if model_name not in self.adapters:
            logger.warning(f"Модель {model_name} не зарегистрирована")
            return False
        
        if adapter:
            # Удаляем конкретный экземпляр из балансировщика
            result = self.load_balancer.unregister_instance(model_name, adapter)
            
            # Если больше нет экземпляров, удаляем модель полностью
            if not self.load_balancer.get_active_instances(model_name):
                del self.adapters[model_name]
                logger.info(f"Удалена модель {model_name} (нет активных экземпляров)")
            
            return result
        else:
            # Удаляем все экземпляры и саму модель
            instances = self.load_balancer.get_active_instances(model_name)
            for adapter, _ in instances:
                self.load_balancer.unregister_instance(model_name, adapter)
            
            del self.adapters[model_name]
            logger.info(f"Удалена модель {model_name} со всеми экземплярами")
            return True

    async def generate(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        use_cache: bool = True, 
        **params
    ) -> Dict[str, Any]:
        """
        Генерирует текст на основе промпта.

        Args:
            prompt: Текстовый промпт
            model: Имя модели (если не указано, используется модель по умолчанию)
            use_cache: Флаг использования кэша
            **params: Дополнительные параметры для модели

        Returns:
            Dict с результатом генерации
        """
        model_name = model or self.default_model
        
        # Проверяем наличие модели
        if model_name not in self.adapters:
            error_msg = f"Модель {model_name} не зарегистрирована в сервисе"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Конвертируем в формат сообщений для единообразия
        messages = [{"role": "user", "content": prompt}]
        
        # Проверяем кэш
        if use_cache:
            cached_result = self.cache.get(messages, model_name, params)
            if cached_result:
                return cached_result
        
        # Замеряем время выполнения
        start_time = time.time()
        
        try:
            # Вызываем метод через балансировщик
            result = await self.load_balancer.execute(model_name, "generate", prompt, **params)
            
            duration = time.time() - start_time
            
            # Записываем метрики
            tokens = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0})
            success = "error" not in result
            self.metrics.record_request(
                model=model_name,
                operation="generate",
                duration=duration,
                tokens=tokens,
                success=success,
                metadata={"prompt_length": len(prompt)}
            )
            
            # Кэшируем результат
            if use_cache and success:
                self.cache.set(messages, model_name, params, result)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Ошибка при генерации текста с моделью {model_name}: {str(e)}")
            
            # Записываем метрики с ошибкой
            self.metrics.record_request(
                model=model_name,
                operation="generate",
                duration=duration,
                tokens={"prompt_tokens": 0, "completion_tokens": 0},
                success=False,
                metadata={"error": str(e), "prompt_length": len(prompt)}
            )
            
            return {"error": str(e)}

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None, 
        use_cache: bool = True, 
        **params
    ) -> Dict[str, Any]:
        """
        Обрабатывает запрос в формате чата.

        Args:
            messages: Список сообщений
            model: Имя модели (если не указано, используется модель по умолчанию)
            use_cache: Флаг использования кэша
            **params: Дополнительные параметры для модели

        Returns:
            Dict с результатом обработки запроса
        """
        model_name = model or self.default_model
        
        # Проверяем наличие модели
        if model_name not in self.adapters:
            error_msg = f"Модель {model_name} не зарегистрирована в сервисе"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Проверяем кэш
        if use_cache:
            cached_result = self.cache.get(messages, model_name, params)
            if cached_result:
                return cached_result
        
        # Замеряем время выполнения
        start_time = time.time()
        
        try:
            # Вызываем метод через балансировщик
            result = await self.load_balancer.execute(model_name, "chat", messages=messages, **params)
            
            duration = time.time() - start_time
            
            # Записываем метрики
            tokens = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0})
            success = "error" not in result
            self.metrics.record_request(
                model=model_name,
                operation="chat",
                duration=duration,
                tokens=tokens,
                success=success,
                metadata={"messages_count": len(messages)}
            )
            
            # Кэшируем результат
            if use_cache and success:
                self.cache.set(messages, model_name, params, result)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Ошибка при обработке чата с моделью {model_name}: {str(e)}")
            
            # Записываем метрики с ошибкой
            self.metrics.record_request(
                model=model_name,
                operation="chat",
                duration=duration,
                tokens={"prompt_tokens": 0, "completion_tokens": 0},
                success=False,
                metadata={"error": str(e), "messages_count": len(messages)}
            )
            
            return {"error": str(e)}

    async def embeddings(
        self, 
        text: str, 
        model: Optional[str] = None, 
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Генерирует векторные представления для текста.

        Args:
            text: Текст для векторизации
            model: Имя модели (если не указано, используется модель по умолчанию)
            use_cache: Флаг использования кэша

        Returns:
            Dict с результатом векторизации
        """
        model_name = model or self.default_model
        
        # Проверяем наличие модели
        if model_name not in self.adapters:
            error_msg = f"Модель {model_name} не зарегистрирована в сервисе"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Оборачиваем в формат сообщений для единообразия кэширования
        messages = [{"role": "system", "content": "embeddings"}, {"role": "user", "content": text}]
        params = {}
        
        # Проверяем кэш
        if use_cache:
            cached_result = self.cache.get(messages, model_name, params)
            if cached_result:
                return cached_result
        
        # Замеряем время выполнения
        start_time = time.time()
        
        try:
            # Вызываем метод через балансировщик
            result = await self.load_balancer.execute(model_name, "embeddings", text=text)
            
            duration = time.time() - start_time
            
            # Записываем метрики
            tokens = result.get("usage", {"prompt_tokens": 0})
            success = "error" not in result
            self.metrics.record_request(
                model=model_name,
                operation="embeddings",
                duration=duration,
                tokens=tokens,
                success=success,
                metadata={"text_length": len(text)}
            )
            
            # Кэшируем результат
            if use_cache and success:
                self.cache.set(messages, model_name, params, result)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Ошибка при получении эмбеддингов с моделью {model_name}: {str(e)}")
            
            # Записываем метрики с ошибкой
            self.metrics.record_request(
                model=model_name,
                operation="embeddings",
                duration=duration,
                tokens={"prompt_tokens": 0},
                success=False,
                metadata={"error": str(e), "text_length": len(text)}
            )
            
            return {"error": str(e)}

    async def get_model_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Возвращает информацию о модели.

        Args:
            model: Имя модели (если не указано, используется модель по умолчанию)

        Returns:
            Dict с информацией о модели
        """
        model_name = model or self.default_model
        
        if model_name not in self.adapters:
            error_msg = f"Модель {model_name} не зарегистрирована в сервисе"
            logger.error(error_msg)
            return {"error": error_msg}
        
        try:
            # Получаем информацию через балансировщик для поддержки асинхронности
            return await self.load_balancer.execute(model_name, "get_model_info")
        except Exception as e:
            logger.error(f"Ошибка при получении информации о модели {model_name}: {str(e)}")
            return {"error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику использования сервиса моделей.

        Returns:
            Dict со статистикой
        """
        stats = {
            "cache": self.cache.get_stats(),
            "load_balancer": self.load_balancer.get_stats(),
            "metrics": self.metrics.get_aggregated_metrics(),
            "models": list(self.adapters.keys()),
            "default_model": self.default_model
        }
        
        return stats 