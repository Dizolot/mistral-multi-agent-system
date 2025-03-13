"""
Клиент для взаимодействия с сервисом моделей (ModelService).
Обеспечивает унифицированный доступ к различным моделям через единый интерфейс.
"""

import asyncio
import logging
import json
import time
import random
from typing import Dict, Any, List, Optional, Union, Callable

# Настройка логирования
logger = logging.getLogger('model_service_client')

class ModelServiceClient:
    """
    Клиент для взаимодействия с сервисом моделей.
    Поддерживает асинхронную работу с различными моделями через унифицированный API.
    """
    
    def __init__(self, 
                 service_instance=None, 
                 model_name: str = "mistral-small",
                 max_retries: int = 3,
                 initial_backoff: float = 1.0,
                 max_backoff: float = 30.0,
                 backoff_factor: float = 2.0,
                 jitter: float = 0.1):
        """
        Инициализация клиента сервиса моделей.
        
        Args:
            service_instance: Экземпляр сервиса моделей. Если None, будет создан.
            model_name: Название модели по умолчанию.
            max_retries: Максимальное количество повторных попыток.
            initial_backoff: Начальная задержка между повторными попытками (сек).
            max_backoff: Максимальная задержка между попытками (сек).
            backoff_factor: Множитель для экспоненциальной задержки.
            jitter: Случайный разброс для предотвращения "грозовых" обращений.
        """
        # Импорт внутри метода, чтобы избежать циклических зависимостей
        if service_instance is None:
            try:
                from src.model_service import ModelService, MistralAdapter
                
                # Создаем адаптер для Mistral
                mistral_adapter = MistralAdapter(
                    base_url="http://139.59.241.176:8080",
                    model_name=model_name,
                    timeout=60
                )
                
                # Создаем экземпляр сервиса моделей
                self._service = ModelService()
                self._service.register_adapter("mistral", mistral_adapter)
                
                logger.info(f"Создан новый экземпляр ModelService с адаптером для модели {model_name}")
            except ImportError as e:
                logger.error(f"Не удалось импортировать модули сервиса моделей: {str(e)}")
                raise
        else:
            self._service = service_instance
            logger.info("Используется существующий экземпляр ModelService")
        
        self._default_model = model_name
        self._max_retries = max_retries
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff
        self._backoff_factor = backoff_factor
        self._jitter = jitter
        
        # Кэш для хранения последних ответов
        self._response_cache = {}
        self._cache_size = 50  # Максимальный размер кэша
        
        logger.info(f"Инициализирован клиент сервиса моделей с моделью по умолчанию: {self._default_model}")
    
    async def generate_text(self, prompt: str, **params) -> str:
        """
        Генерирует текст на основе одиночного промпта.
        
        Args:
            prompt: Текстовый промпт.
            **params: Дополнительные параметры (temperature, max_tokens и т.д.).
            
        Returns:
            Сгенерированный текст.
        """
        logger.info("Запрос generate_text")
        
        try:
            # Добавляем модель по умолчанию, если не указана
            if "model" not in params:
                params["model"] = self._default_model
            
            # Выполняем запрос с повторными попытками
            result = await self._execute_with_retry(
                lambda: self._service.generate(prompt, **params)
            )
            
            # Проверяем на наличие ошибки
            if "error" in result:
                logger.error(f"Ошибка при генерации текста: {result['error']}")
                return f"Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
            
            return result["text"]
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при генерации текста: {str(e)}", exc_info=True)
            return f"Произошла непредвиденная ошибка: {str(e)}"
    
    async def generate_chat_response(self, 
                                   messages: List[Dict[str, str]], 
                                   temperature: float = 0.7, 
                                   max_tokens: int = 1000,
                                   model: Optional[str] = None,
                                   **params) -> str:
        """
        Генерирует ответ на основе истории сообщений в формате чата.
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "Привет"}, ...].
            temperature: Параметр температуры (0.0-1.0).
            max_tokens: Максимальное число токенов.
            model: Название модели (если None, используется модель по умолчанию).
            **params: Дополнительные параметры.
            
        Returns:
            Сгенерированный ответ.
        """
        logger.info(f"Запрос generate_chat_response с {len(messages)} сообщениями")
        
        # Проверяем кэш, если температура низкая (детерминированные ответы)
        if temperature < 0.2:
            cache_key = self._get_cache_key(messages, temperature, max_tokens, model)
            cached_response = self._response_cache.get(cache_key)
            if cached_response:
                logger.info("Найден ответ в кэше")
                return cached_response
        
        try:
            # Подготавливаем параметры
            params.update({
                "temperature": temperature,
                "max_tokens": max_tokens,
                "model": model or self._default_model
            })
            
            # Выполняем запрос с повторными попытками
            result = await self._execute_with_retry(
                lambda: self._service.chat(messages, **params)
            )
            
            # Проверяем на наличие ошибки
            if "error" in result:
                logger.error(f"Ошибка при генерации ответа в чате: {result['error']}")
                return f"Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
            
            response_text = result["text"]
            
            # Сохраняем в кэш, если температура низкая
            if temperature < 0.2:
                cache_key = self._get_cache_key(messages, temperature, max_tokens, model)
                self._add_to_cache(cache_key, response_text)
            
            return response_text
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при генерации ответа в чате: {str(e)}", exc_info=True)
            return f"Произошла непредвиденная ошибка: {str(e)}"
    
    async def generate_embeddings(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Генерирует векторное представление (эмбеддинги) для текста.
        
        Args:
            text: Текст для векторизации.
            model: Название модели (если None, используется модель по умолчанию).
            
        Returns:
            Список векторных значений (эмбеддингов).
        """
        logger.info("Запрос generate_embeddings")
        
        try:
            params = {}
            if model:
                params["model"] = model
            else:
                params["model"] = self._default_model
            
            # Выполняем запрос с повторными попытками
            result = await self._execute_with_retry(
                lambda: self._service.embeddings(text, **params)
            )
            
            # Проверяем на наличие ошибки
            if "error" in result:
                logger.error(f"Ошибка при генерации эмбеддингов: {result['error']}")
                return []
            
            return result["embeddings"]
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при генерации эмбеддингов: {str(e)}", exc_info=True)
            return []
    
    async def get_model_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает информацию о модели.
        
        Args:
            model: Название модели (если None, используется модель по умолчанию).
            
        Returns:
            Словарь с информацией о модели.
        """
        try:
            model_name = model or self._default_model
            return await self._service.get_model_info(model_name)
        except Exception as e:
            logger.error(f"Ошибка при получении информации о модели: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    async def _execute_with_retry(self, operation: Callable[[], Any]) -> Any:
        """
        Выполняет операцию с механизмом повторных попыток и экспоненциальной задержкой.
        
        Args:
            operation: Функция для выполнения.
            
        Returns:
            Результат операции.
        """
        retries = 0
        last_exception = None
        
        while retries <= self._max_retries:
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                logger.warning(f"Ошибка при выполнении операции (попытка {retries+1}/{self._max_retries+1}): {str(e)}")
                
                # Увеличиваем счетчик попыток
                retries += 1
                
                # Если достигнут лимит попыток, выходим
                if retries > self._max_retries:
                    break
                
                # Вычисляем время задержки с экспоненциальным ростом
                backoff = min(
                    self._max_backoff,
                    self._initial_backoff * (self._backoff_factor ** (retries - 1))
                )
                
                # Добавляем случайный разброс (jitter)
                jitter_amount = backoff * self._jitter
                backoff = backoff + random.uniform(-jitter_amount, jitter_amount)
                
                logger.info(f"Повторная попытка через {backoff:.2f} секунд...")
                await asyncio.sleep(backoff)
        
        # Если все попытки исчерпаны, возвращаем ответ с ошибкой
        logger.error(f"Все попытки исчерпаны. Последняя ошибка: {str(last_exception)}")
        return {"error": str(last_exception) if last_exception else "Превышено количество попыток"}
    
    def _get_cache_key(self, messages: List[Dict[str, str]], temperature: float, 
                      max_tokens: int, model: Optional[str]) -> str:
        """
        Генерирует ключ кэша на основе параметров запроса.
        
        Args:
            messages: Список сообщений.
            temperature: Параметр температуры.
            max_tokens: Максимальное число токенов.
            model: Название модели.
            
        Returns:
            Строковый ключ кэша.
        """
        model_name = model or self._default_model
        # Сериализуем сообщения и объединяем с другими параметрами
        return f"{json.dumps(messages)}_{temperature}_{max_tokens}_{model_name}"
    
    def _add_to_cache(self, key: str, value: str) -> None:
        """
        Добавляет значение в кэш с контролем размера.
        
        Args:
            key: Ключ кэша.
            value: Значение для сохранения.
        """
        # Если кэш переполнен, удаляем самый старый элемент
        if len(self._response_cache) >= self._cache_size:
            # Получаем первый ключ (самый старый)
            oldest_key = next(iter(self._response_cache))
            del self._response_cache[oldest_key]
        
        # Добавляем новое значение
        self._response_cache[key] = value
        
    def close(self) -> None:
        """
        Освобождает ресурсы, используемые клиентом.
        """
        # Очищаем кэш
        self._response_cache.clear()
        logger.info("Ресурсы клиента сервиса моделей освобождены") 