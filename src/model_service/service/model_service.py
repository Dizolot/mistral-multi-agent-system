"""
Основной сервис моделей с унифицированным API.
Обеспечивает единый интерфейс для работы с различными языковыми моделями.
"""

import logging
import time
import os
import uuid
import asyncio
from typing import Dict, List, Any, Optional, Union, Type

from ..model_adapter.model_adapter import ModelAdapter
from ..load_balancer.load_balancer import LoadBalancer
from ..caching.response_cache import ResponseCache
from ..metrics.metrics_collector import MetricsCollector
from .session_manager import SessionManager
from .request_queue import RequestQueue, RequestPriority, QueueFullError

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
        metrics_dir: str = "logs/metrics",
        session_ttl: int = 3600,  # Время жизни сессии (1 час)
        max_sessions: int = 1000,  # Максимальное количество сессий
        sessions_storage_path: Optional[str] = None,  # Путь для хранения сессий
        max_workers: int = 5,  # Максимальное число параллельных запросов
        max_queue_size: int = 100,  # Размер очереди запросов
        request_timeout: int = 60  # Таймаут запроса (в секундах)
    ):
        """
        Инициализирует сервис моделей.

        Args:
            default_model: Модель по умолчанию
            cache_size: Размер кэша (количество элементов)
            cache_ttl: Время жизни кэша в секундах
            metrics_dir: Директория для сохранения метрик
            session_ttl: Время жизни сессии в секундах
            max_sessions: Максимальное количество сессий
            sessions_storage_path: Путь для хранения сессий на диске
            max_workers: Максимальное число параллельных запросов
            max_queue_size: Размер очереди запросов
            request_timeout: Таймаут запроса в секундах
        """
        self.default_model = default_model
        self.adapters = {}  # {model_name: adapter}
        
        # Инициализируем компоненты
        self.load_balancer = LoadBalancer()
        self.cache = ResponseCache(max_size=cache_size, ttl=cache_ttl)
        self.metrics = MetricsCollector(metrics_dir=metrics_dir)
        
        # Инициализируем менеджер сессий
        if sessions_storage_path:
            os.makedirs(os.path.dirname(sessions_storage_path), exist_ok=True)
        self.session_manager = SessionManager(
            ttl=session_ttl,
            max_sessions=max_sessions,
            storage_path=sessions_storage_path
        )
        
        # Инициализируем очередь запросов
        self.request_queue = RequestQueue(
            max_workers=max_workers,
            max_queue_size=max_queue_size,
            timeout=request_timeout
        )
        
        logger.info(f"Инициализирован сервис моделей с моделью по умолчанию: {default_model}")

    async def start(self):
        """
        Запускает необходимые фоновые задачи сервиса.
        """
        await self.session_manager.start_cleanup_task()
        await self.request_queue.start()
        logger.info("Запущены фоновые задачи сервиса моделей")

    async def stop(self):
        """
        Останавливает фоновые задачи и сохраняет состояние.
        """
        # Останавливаем очередь запросов
        await self.request_queue.stop()
        
        # Останавливаем менеджер сессий
        await self.session_manager.stop_cleanup_task()
        
        # Сохраняем состояние сессий
        if self.session_manager.storage_path:
            await self.session_manager.save_sessions()
            
        logger.info("Остановлены фоновые задачи сервиса моделей")

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

    async def chat_with_session(
        self, 
        message: Dict[str, str], 
        session_id: Optional[str] = None,
        model: Optional[str] = None, 
        use_cache: bool = True,
        max_history_length: int = 10,
        metadata: Optional[Dict[str, Any]] = None,
        **params
    ) -> Dict[str, Any]:
        """
        Обрабатывает запрос в формате чата с использованием сессий для сохранения контекста.

        Args:
            message: Сообщение пользователя
            session_id: Идентификатор сессии (если None, будет создана новая сессия)
            model: Имя модели (если не указано, используется модель по умолчанию)
            use_cache: Флаг использования кэша
            max_history_length: Максимальное количество сообщений в истории
            metadata: Дополнительные метаданные сессии
            **params: Дополнительные параметры для модели

        Returns:
            Dict с результатом обработки запроса и идентификатором сессии
        """
        model_name = model or self.default_model
        
        # Проверяем наличие модели
        if model_name not in self.adapters:
            error_msg = f"Модель {model_name} не зарегистрирована в сервисе"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Если сессия не указана, создаем новую
        if not session_id:
            session_id = str(uuid.uuid4())
            session = self.session_manager.create_session(
                session_id=session_id,
                model=model_name,
                max_history_length=max_history_length,
                metadata=metadata
            )
            logger.debug(f"Создана новая сессия {session_id} для модели {model_name}")
        else:
            # Получаем существующую сессию или создаем новую с указанным ID
            session = self.session_manager.get_session(session_id)
            if not session:
                session = self.session_manager.create_session(
                    session_id=session_id,
                    model=model_name,
                    max_history_length=max_history_length,
                    metadata=metadata
                )
                logger.debug(f"Создана сессия {session_id} для модели {model_name}")
        
        # Добавляем сообщение пользователя в сессию
        user_message = {"role": message.get("role", "user"), "content": message.get("content", "")}
        session.add_message(user_message)
        
        # Получаем полный контекст сессии для отправки модели
        context_messages = session.get_context_messages()
        
        # Замеряем время выполнения
        start_time = time.time()
        
        try:
            # Вызываем метод через балансировщик
            result = await self.load_balancer.execute(
                model_name, 
                "chat", 
                messages=context_messages, 
                **params
            )
            
            duration = time.time() - start_time
            
            # Добавляем ответ модели в историю сессии
            if "text" in result and not "error" in result:
                assistant_message = {"role": "assistant", "content": result["text"]}
                session.add_message(assistant_message)
            
            # Записываем метрики
            tokens = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0})
            success = "error" not in result
            self.metrics.record_request(
                model=model_name,
                operation="chat_with_session",
                duration=duration,
                tokens=tokens,
                success=success,
                metadata={"session_id": session_id, "messages_count": len(context_messages)}
            )
            
            # Добавляем информацию о сессии в результат
            result["session_id"] = session_id
            result["session_history_length"] = len(session.messages)
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Ошибка при обработке чата с сессией {session_id}, модель {model_name}: {str(e)}")
            
            # Записываем метрики с ошибкой
            self.metrics.record_request(
                model=model_name,
                operation="chat_with_session",
                duration=duration,
                tokens={"prompt_tokens": 0, "completion_tokens": 0},
                success=False,
                metadata={"session_id": session_id, "error": str(e)}
            )
            
            return {"error": str(e), "session_id": session_id}
    
    async def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """
        Возвращает историю сообщений сессии.

        Args:
            session_id: Идентификатор сессии

        Returns:
            Dict с историей сообщений или ошибкой
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return {"error": f"Сессия {session_id} не найдена"}
        
        return {
            "session_id": session_id,
            "model": session.model,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "messages": session.messages,
            "message_count": len(session.messages),
            "metadata": session.metadata
        }
    
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Удаляет сессию.

        Args:
            session_id: Идентификатор сессии

        Returns:
            Dict с результатом операции
        """
        if self.session_manager.delete_session(session_id):
            return {"success": True, "message": f"Сессия {session_id} удалена"}
        else:
            return {"error": f"Сессия {session_id} не найдена"}

    async def generate_async(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        use_cache: bool = True,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: Optional[int] = None,
        **params
    ) -> Dict[str, Any]:
        """
        Асинхронно генерирует текст на основе промпта через очередь запросов.

        Args:
            prompt: Текстовый промпт
            model: Имя модели (если не указано, используется модель по умолчанию)
            use_cache: Флаг использования кэша
            priority: Приоритет запроса
            timeout: Таймаут выполнения (если None, используется таймаут очереди)
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
        
        try:
            # Ставим запрос в очередь
            request_id = str(uuid.uuid4())
            future = await self.request_queue.enqueue(
                self.generate,  # Используем обычный метод generate
                prompt=prompt,
                model=model_name,
                use_cache=use_cache,
                **params,
                priority=priority,
                timeout=timeout,
                request_id=request_id
            )
            
            # Ожидаем результат
            result = await future
            return result
            
        except QueueFullError as e:
            logger.error(f"Очередь запросов заполнена: {e}")
            return {"error": f"Сервис перегружен, попробуйте позже. Ошибка: {str(e)}"}
            
        except asyncio.TimeoutError as e:
            logger.error(f"Превышено время выполнения запроса: {e}")
            return {"error": f"Превышено время выполнения запроса: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Ошибка при асинхронной генерации текста с моделью {model_name}: {str(e)}")
            return {"error": str(e)}

    async def chat_async(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None, 
        use_cache: bool = True,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: Optional[int] = None,
        **params
    ) -> Dict[str, Any]:
        """
        Асинхронно обрабатывает запрос в формате чата через очередь запросов.

        Args:
            messages: Список сообщений
            model: Имя модели (если не указано, используется модель по умолчанию)
            use_cache: Флаг использования кэша
            priority: Приоритет запроса
            timeout: Таймаут выполнения (если None, используется таймаут очереди)
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
        
        try:
            # Ставим запрос в очередь
            request_id = str(uuid.uuid4())
            future = await self.request_queue.enqueue(
                self.chat,  # Используем обычный метод chat
                messages=messages,
                model=model_name,
                use_cache=use_cache,
                **params,
                priority=priority,
                timeout=timeout,
                request_id=request_id
            )
            
            # Ожидаем результат
            result = await future
            return result
            
        except QueueFullError as e:
            logger.error(f"Очередь запросов заполнена: {e}")
            return {"error": f"Сервис перегружен, попробуйте позже. Ошибка: {str(e)}"}
            
        except asyncio.TimeoutError as e:
            logger.error(f"Превышено время выполнения запроса: {e}")
            return {"error": f"Превышено время выполнения запроса: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Ошибка при асинхронной обработке чата с моделью {model_name}: {str(e)}")
            return {"error": str(e)}

    async def chat_with_session_async(
        self, 
        message: Dict[str, str], 
        session_id: Optional[str] = None,
        model: Optional[str] = None, 
        use_cache: bool = True,
        max_history_length: int = 10,
        metadata: Optional[Dict[str, Any]] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: Optional[int] = None,
        **params
    ) -> Dict[str, Any]:
        """
        Асинхронно обрабатывает запрос в формате чата с использованием сессий через очередь запросов.

        Args:
            message: Сообщение пользователя
            session_id: Идентификатор сессии (если None, будет создана новая сессия)
            model: Имя модели (если не указано, используется модель по умолчанию)
            use_cache: Флаг использования кэша
            max_history_length: Максимальное количество сообщений в истории
            metadata: Дополнительные метаданные сессии
            priority: Приоритет запроса
            timeout: Таймаут выполнения (если None, используется таймаут очереди)
            **params: Дополнительные параметры для модели

        Returns:
            Dict с результатом обработки запроса и идентификатором сессии
        """
        model_name = model or self.default_model
        
        # Проверяем наличие модели
        if model_name not in self.adapters:
            error_msg = f"Модель {model_name} не зарегистрирована в сервисе"
            logger.error(error_msg)
            return {"error": error_msg}
        
        try:
            # Ставим запрос в очередь
            request_id = str(uuid.uuid4())
            future = await self.request_queue.enqueue(
                self.chat_with_session,  # Используем обычный метод chat_with_session
                message=message,
                session_id=session_id,
                model=model_name,
                use_cache=use_cache,
                max_history_length=max_history_length,
                metadata=metadata,
                **params,
                priority=priority,
                timeout=timeout,
                request_id=request_id
            )
            
            # Ожидаем результат
            result = await future
            return result
            
        except QueueFullError as e:
            logger.error(f"Очередь запросов заполнена: {e}")
            return {"error": f"Сервис перегружен, попробуйте позже. Ошибка: {str(e)}"}
            
        except asyncio.TimeoutError as e:
            logger.error(f"Превышено время выполнения запроса: {e}")
            return {"error": f"Превышено время выполнения запроса: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Ошибка при асинхронной обработке чата с сессией {session_id}, модель {model_name}: {str(e)}")
            return {"error": str(e), "session_id": session_id} 