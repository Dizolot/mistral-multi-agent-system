"""
Клиент для взаимодействия с сервисом моделей (ModelService).
Обеспечивает унифицированный доступ к различным моделям через единый интерфейс.
"""

import asyncio
import logging
import json
import time
import random
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable
import requests

# Настройка расширенного логирования
def setup_client_logging():
    """Настройка расширенного логирования для клиента моделей"""
    logger = logging.getLogger('model_service_client')
    logger.setLevel(logging.DEBUG)
    
    # Создаем директорию для логов
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Форматтер с расширенной информацией
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Файловый обработчик для API-запросов
    api_handler = logging.FileHandler(os.path.join(log_dir, 'mistral_api.log'))
    api_handler.setLevel(logging.DEBUG)
    api_handler.setFormatter(formatter)
    
    # Файловый обработчик для ошибок
    error_handler = logging.FileHandler(os.path.join(log_dir, 'mistral_api_errors.log'))
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Добавляем обработчики
    logger.addHandler(api_handler)
    logger.addHandler(error_handler)
    
    return logger

# Инициализация логгера
logger = setup_client_logging()

class ModelServiceClient:
    """
    Клиент для взаимодействия с сервисом моделей.
    Поддерживает асинхронную работу с различными моделями через унифицированный API.
    Реализует интерфейс, совместимый с MistralAdapter для использования в CodeImprovementAgent.
    """
    
    def __init__(self, 
                 config: Dict[str, Any] = None,
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
            config: Конфигурация с основными параметрами
            service_instance: Экземпляр сервиса моделей. Если None, будет создан.
            model_name: Название модели по умолчанию.
            max_retries: Максимальное количество повторных попыток.
            initial_backoff: Начальная задержка между повторными попытками (сек).
            max_backoff: Максимальная задержка между попытками (сек).
            backoff_factor: Множитель для экспоненциальной задержки.
            jitter: Случайный разброс для предотвращения "грозовых" обращений.
        """
        self.config = config or {}
        
        # Параметры модели Mistral
        self.model_name = self.config.get("MODEL_NAME", model_name)
        
        # URL для HTTP-соединения с Mistral API
        self.base_url = self.config.get("MISTRAL_API_URL", "http://139.59.241.176:8080")
        
        # Параметры повторных попыток
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        
        # Кэш для хранения результатов
        self._cache = {}
        self._max_cache_size = 100
        
        # Метрики запросов
        self._request_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "retry_count": 0
        }
        
        logger.info(
            f"ModelServiceClient initialized:\n"
            f"- Model: {self.model_name}\n"
            f"- URL: {self.base_url}\n"
            f"- Max retries: {self.max_retries}\n"
            f"- Backoff settings: initial={self.initial_backoff}s, max={self.max_backoff}s, factor={self.backoff_factor}"
        )
    
    def _log_request(self, method: str, url: str, payload: Dict[str, Any]) -> None:
        """Логирование деталей запроса"""
        request_id = random.randint(1000000, 9999999)
        log_data = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "url": url,
            "payload": {
                k: v if k != "messages" else f"[{len(v)} messages]"
                for k, v in payload.items()
            }
        }
        logger.debug(f"API Request {request_id}: {json.dumps(log_data, ensure_ascii=False)}")
        return request_id
    
    def _log_response(self, request_id: int, status_code: int, response_data: Dict[str, Any], duration: float) -> None:
        """Логирование деталей ответа"""
        log_data = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
            "response_keys": list(response_data.keys()) if isinstance(response_data, dict) else None
        }
        logger.debug(f"API Response {request_id}: {json.dumps(log_data, ensure_ascii=False)}")
    
    def _log_error(self, request_id: int, error: Exception, context: str) -> None:
        """Логирование ошибок"""
        log_data = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }
        logger.error(f"API Error {request_id}: {json.dumps(log_data, ensure_ascii=False)}", exc_info=True)
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, **params) -> str:
        """
        Генерирует текст на основе промпта.
        
        Args:
            prompt: Текстовый промпт для модели
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура для генерации (креативность)
            **params: Дополнительные параметры для модели
            
        Returns:
            str: Сгенерированный текст
        """
        logger.debug(f"Generating text with prompt: {prompt[:50]}...")
        
        async def _operation():
            # Формируем запрос к HTTP API Mistral
            url = f"{self.base_url}/generate"
            
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **params
            }
            
            # Выполняем запрос
            response = requests.post(url, json=payload)
            
            # Проверяем результат
            if response.status_code != 200:
                error_msg = f"Error calling Mistral API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            # Парсим ответ
            result = response.json()
            generated_text = result.get("text", "")
            
            return generated_text
            
        result = await self._execute_with_retry(_operation)
        return result
    
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
            cached_response = self._cache.get(cache_key)
            if cached_response:
                logger.info("Найден ответ в кэше")
                self._request_metrics["cache_hits"] += 1
                return cached_response
        
        try:
            # Подготавливаем параметры для запроса
            model_name = model or self.model_name
            
            async def _operation():
                # Формируем запрос к HTTP API Mistral
                # Используем эндпоинт /completion для llama.cpp сервера
                url = f"{self.base_url}/completion"
                
                # Преобразуем сообщения в формат промпта для llama.cpp
                prompt = ""
                for msg in messages:
                    role = msg["role"]
                    content = msg["content"]
                    if role == "user":
                        prompt += f"User: {content}\n"
                    elif role == "assistant":
                        prompt += f"Assistant: {content}\n"
                    elif role == "system":
                        prompt += f"System: {content}\n"
                
                # Добавляем префикс для ответа ассистента
                prompt += "Assistant: "
                
                payload = {
                    "prompt": prompt,
                    "model": model_name,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **params
                }
                
                # Логируем запрос
                request_id = self._log_request("POST", url, payload)
                
                start_time = time.time()
                
                try:
                    # Выполняем запрос
                    response = requests.post(url, json=payload)
                    duration = time.time() - start_time
                    
                    # Логируем ответ
                    self._log_response(request_id, response.status_code, response.json(), duration)
                    
                    # Проверяем результат
                    if response.status_code != 200:
                        error_msg = f"Ошибка вызова Mistral API: {response.status_code} - {response.text}"
                        self._log_error(request_id, Exception(error_msg), "HTTP Error")
                        raise Exception(error_msg)
                        
                    # Парсим ответ
                    result = response.json()
                    
                    # Извлекаем текст из ответа
                    if "content" in result:
                        # Формат llama.cpp
                        response_text = result["content"]
                    elif "choices" in result and len(result["choices"]) > 0:
                        # Формат OpenAI-совместимого API
                        response_text = result["choices"][0]["message"]["content"]
                    elif "response" in result:
                        # Альтернативный формат
                        response_text = result["response"]
                    elif "text" in result:
                        # Простой формат
                        response_text = result["text"]
                    else:
                        error_msg = f"Неизвестный формат ответа: {result}"
                        self._log_error(request_id, Exception(error_msg), "Parse Error")
                        response_text = "Не удалось получить ответ от модели."
                    
                    return response_text
                    
                except requests.exceptions.RequestException as e:
                    self._log_error(request_id, e, "Network Error")
                    raise
                except json.JSONDecodeError as e:
                    self._log_error(request_id, e, "JSON Parse Error")
                    raise
                except Exception as e:
                    self._log_error(request_id, e, "Unknown Error")
                    raise
            
            # Выполняем операцию с повторными попытками
            response_text = await self._execute_with_retry(_operation)
            
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
            model_name = model or self.model_name
            
            async def _operation():
                # Формируем запрос к HTTP API Mistral
                url = f"{self.base_url}/embeddings"
                
                payload = {
                    "input": text,
                    "model": model_name
                }
                
                # Выполняем запрос
                response = requests.post(url, json=payload)
                
                # Проверяем результат
                if response.status_code != 200:
                    error_msg = f"Ошибка вызова Mistral API: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
                # Парсим ответ
                result = response.json()
                
                # Извлекаем эмбеддинги
                if "data" in result and len(result["data"]) > 0:
                    # Формат OpenAI-совместимого API
                    return result["data"][0]["embedding"]
                elif "embeddings" in result:
                    # Альтернативный формат
                    return result["embeddings"]
                else:
                    logger.error(f"Неизвестный формат ответа эмбеддингов: {result}")
                    return []
            
            # Выполняем запрос с механизмом повторных попыток
            return await self._execute_with_retry(_operation)
            
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
            model_name = model or self.model_name
            
            async def _operation():
                # Формируем запрос к HTTP API Mistral
                url = f"{self.base_url}/model_info"
                
                payload = {
                    "model": model_name
                }
                
                # Логируем запрос
                request_id = self._log_request("GET", url, payload)
                
                start_time = time.time()
                
                try:
                    # Выполняем запрос
                    response = requests.get(url, params=payload)
                    duration = time.time() - start_time
                    
                    # Логируем ответ
                    self._log_response(request_id, response.status_code, response.json(), duration)
                    
                    # Проверяем результат
                    if response.status_code != 200:
                        error_msg = f"Ошибка вызова Mistral API: {response.status_code} - {response.text}"
                        self._log_error(request_id, Exception(error_msg), "HTTP Error")
                        raise Exception(error_msg)
                        
                    return response.json()
                    
                except requests.exceptions.RequestException as e:
                    self._log_error(request_id, e, "Network Error")
                    raise
                except json.JSONDecodeError as e:
                    self._log_error(request_id, e, "JSON Parse Error")
                    raise
                except Exception as e:
                    self._log_error(request_id, e, "Unknown Error")
                    raise
            
            # Выполняем запрос с механизмом повторных попыток
            return await self._execute_with_retry(_operation)
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о модели: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    async def _execute_with_retry(self, operation: Callable[[], Any]) -> Any:
        """
        Выполняет операцию с механизмом повторных попыток.
        
        Args:
            operation: Асинхронная функция для выполнения
            
        Returns:
            Результат операции
            
        Raises:
            Exception: Если все попытки завершились неудачно
        """
        self._request_metrics["total_requests"] += 1
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                result = await operation()
                duration = time.time() - start_time
                
                self._request_metrics["successful_requests"] += 1
                
                if attempt > 0:
                    self._request_metrics["retry_count"] += attempt
                    logger.info(f"Успешное выполнение после {attempt + 1} попыток за {duration:.2f}с")
                
                return result
                
            except Exception as e:
                self._request_metrics["failed_requests"] += 1
                
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Все попытки исчерпаны ({self.max_retries}). "
                        f"Последняя ошибка: {str(e)}", 
                        exc_info=True
                    )
                    raise
                
                # Вычисляем время ожидания
                backoff = min(
                    self.initial_backoff * (self.backoff_factor ** attempt),
                    self.max_backoff
                )
                
                # Добавляем случайный разброс
                jitter_amount = random.uniform(-self.jitter * backoff, self.jitter * backoff)
                wait_time = backoff + jitter_amount
                
                logger.warning(
                    f"Попытка {attempt + 1}/{self.max_retries} не удалась: {str(e)}. "
                    f"Повтор через {wait_time:.2f}с"
                )
                
                await asyncio.sleep(wait_time)
    
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
        model_name = model or self.model_name
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
        if len(self._cache) >= self._max_cache_size:
            # Получаем первый ключ (самый старый)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        # Добавляем новое значение
        self._cache[key] = value
        
    def close(self) -> None:
        """
        Освобождает ресурсы, используемые клиентом.
        """
        # Очищаем кэш
        self._cache.clear()
        logger.info("Ресурсы клиента сервиса моделей освобождены")
    
    # Методы для совместимости с интерфейсом MistralAdapter
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получает эмбеддинги для списка текстов.
        
        Args:
            texts: Список текстов для получения эмбеддингов
            
        Returns:
            List[List[float]]: Список векторов эмбеддингов
        """
        if not texts:
            return []
            
        # Для простоты реализации вызываем generate_embeddings для каждого текста
        result = []
        for text in texts:
            embedding = await self.generate_embeddings(text)
            result.append(embedding)
            
        return result
    
    async def get_chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Получает завершение чата на основе списка сообщений.
        
        Args:
            messages: Список сообщений чата в формате [{"role": "user", "content": "текст"}]
            temperature: Температура для генерации
            max_tokens: Максимальное количество токенов в ответе
            
        Returns:
            str: Сгенерированный ответ
        """
        # Прямое делегирование к существующему методу
        return await self.generate_chat_response(messages, temperature, max_tokens)
    
    async def __call__(self, prompt: str, **kwargs) -> str:
        """
        Позволяет вызывать экземпляр класса как функцию.
        
        Args:
            prompt: Текстовый промпт для модели
            **kwargs: Дополнительные параметры для модели
            
        Returns:
            str: Сгенерированный текст
        """
        return await self.generate_text(prompt, **kwargs) 