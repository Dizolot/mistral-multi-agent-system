"""
Адаптер для работы с API Mistral.
"""

import json
import logging
import httpx
import asyncio
import time
import random
from typing import List, Dict, Any, Optional, Tuple, Union, Callable

from .model_adapter import ModelAdapter

# Настройка логирования
logger = logging.getLogger(__name__)

# Константы для механизма повторных попыток
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 1.0  # начальная задержка в секундах
DEFAULT_MAX_BACKOFF = 30.0  # максимальная задержка в секундах
DEFAULT_BACKOFF_FACTOR = 2.0  # множитель для экспоненциальной задержки
DEFAULT_JITTER = 0.1  # разброс для предотвращения "грозовых" обращений

# Словарь доступных моделей Mistral и их параметров
MISTRAL_MODELS = {
    "TheBloke/Mistral-7B-Instruct-v0.3-GPTQ": {
        "max_tokens": 8000,
        "description": "Mistral 7B Instruct v0.3 GPTQ",
        "recommended_temperature": 0.7,
        "recommended_top_p": 0.9,
    }
}

# Типы ошибок в Mistral API
class MistralApiError(Exception):
    """Базовый класс ошибок Mistral API."""
    pass

class MistralConnectionError(MistralApiError):
    """Ошибка соединения с Mistral API."""
    pass

class MistralTimeoutError(MistralApiError):
    """Ошибка таймаута Mistral API."""
    pass

class MistralRateLimitError(MistralApiError):
    """Ошибка превышения лимита запросов к Mistral API."""
    pass

class MistralServerError(MistralApiError):
    """Ошибка на стороне сервера Mistral API."""
    pass

class MistralAuthenticationError(MistralApiError):
    """Ошибка аутентификации в Mistral API."""
    pass

class MistralValidationError(MistralApiError):
    """Ошибка валидации в Mistral API."""
    pass

class MistralAdapter(ModelAdapter):
    """
    Адаптер для работы с моделями Mistral через HTTP API.
    Обеспечивает унифицированный интерфейс для работы с моделями Mistral.
    """

    def __init__(
        self,
        base_url: str = "http://139.59.241.176:8080",
        model_name: str = "TheBloke/Mistral-7B-Instruct-v0.3-GPTQ",
        timeout: int = 60,
        api_key: str = "",
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_codes: List[int] = None,
        initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        jitter: float = DEFAULT_JITTER,
    ):
        """
        Инициализирует адаптер для работы с Mistral API.

        Args:
            base_url: Базовый URL API (по умолчанию: http://139.59.241.176:8080)
            model_name: Название модели (по умолчанию: TheBloke/Mistral-7B-Instruct-v0.3-GPTQ)
            timeout: Таймаут запросов в секундах (по умолчанию: 60)
            api_key: API ключ (если требуется)
            max_retries: Максимальное количество повторных попыток (по умолчанию: 3)
            retry_codes: Список HTTP кодов, при которых выполнять повторные попытки
            initial_backoff: Начальная задержка в секундах (по умолчанию: 1.0)
            max_backoff: Максимальная задержка в секундах (по умолчанию: 30.0)
            backoff_factor: Множитель для экспоненциальной задержки (по умолчанию: 2.0)
            jitter: Разброс для предотвращения "грозовых" обращений (по умолчанию: 0.1)
        """
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_codes = retry_codes or [408, 429, 500, 502, 503, 504]
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        
        self.headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        # Получаем информацию о модели из предопределенного словаря или используем значения по умолчанию
        model_info = MISTRAL_MODELS.get(model_name, {
            "max_tokens": 8000,
            "description": "Стандартная модель Mistral",
            "recommended_temperature": 0.7,
            "recommended_top_p": 0.9,
        })

        # Информация о модели
        self._model_info = {
            "name": model_name,
            "provider": "Mistral",
            "max_tokens": model_info["max_tokens"],
            "description": model_info["description"],
            "recommended_params": {
                "temperature": model_info["recommended_temperature"],
                "top_p": model_info["recommended_top_p"],
            },
            "capabilities": ["chat", "completion", "embeddings"],
        }

        # Состояние адаптера
        self._health_status = {
            "is_available": True,
            "last_success": time.time(),
            "last_error": None,
            "error_count": 0,
            "success_count": 0,
        }

        logger.info(f"Инициализирован адаптер для модели {model_name} с API {base_url}")

    @classmethod
    def available_models(cls) -> List[Dict[str, Any]]:
        """
        Возвращает список доступных моделей Mistral с их параметрами.
        
        Returns:
            Список словарей с информацией о моделях
        """
        return [
            {
                "name": name,
                "max_tokens": info["max_tokens"],
                "description": info["description"],
                "recommended_params": {
                    "temperature": info["recommended_temperature"],
                    "top_p": info["recommended_top_p"],
                }
            }
            for name, info in MISTRAL_MODELS.items()
        ]

    async def generate(self, prompt: str, **params) -> Dict[str, Any]:
        """
        Генерирует текст на основе промпта.

        Args:
            prompt: Текстовый промпт для генерации
            **params: Дополнительные параметры (temperature, max_tokens и т.д.)

        Returns:
            Dict с результатом генерации
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, **params)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        stream: bool = False,
        **params,
    ) -> Dict[str, Any]:
        """
        Обрабатывает запрос в формате чата.

        Args:
            messages: Список сообщений
            temperature: Параметр температуры (0.0-1.0)
            max_tokens: Максимальное число токенов
            top_p: Параметр top-p
            presence_penalty: Штраф за повторение тем (0.0-2.0)
            frequency_penalty: Штраф за повторение токенов (0.0-2.0)
            stream: Использовать потоковый режим ответа
            **params: Дополнительные параметры

        Returns:
            Dict с результатом генерации
        """
        endpoint = f"{self.base_url}/v1/chat/completions"
        
        # Формируем запрос в формате OpenAI API
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature if temperature is not None else self._model_info["recommended_params"].get("temperature", 0.7),
            "max_tokens": max_tokens if max_tokens is not None else 1000,
            "top_p": top_p if top_p is not None else self._model_info["recommended_params"].get("top_p", 0.9),
            "stream": stream
        }
        
        # Добавляем дополнительные параметры, если они указаны
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        
        # Добавляем любые дополнительные параметры
        for key, value in params.items():
            if key not in payload:
                payload[key] = value
        
        try:
            response = await self._execute_request_with_retry(endpoint, payload)
            
            # Если включен потоковый режим, возвращаем генератор
            if stream:
                return {
                    "stream": self._stream_response(response),
                    "model_info": self.get_model_info(),
                }
            
            # Иначе преобразуем ответ в унифицированный формат
            result = {
                "text": response["choices"][0]["message"]["content"],
                "usage": response.get("usage", {"prompt_tokens": 0, "completion_tokens": 0}),
                "model_info": self.get_model_info(),
                "id": response.get("id", ""),
                "finish_reason": response["choices"][0].get("finish_reason", "stop"),
            }
            
            # Обновляем статус здоровья
            self._update_health_status(success=True)
            
            return result
        except MistralApiError as e:
            logger.error(f"Ошибка Mistral API при выполнении запроса: {str(e)}")
            self._update_health_status(success=False, error=str(e))
            return {
                "error": str(e),
                "error_type": e.__class__.__name__,
                "model_info": self.get_model_info(),
            }
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при выполнении запроса к Mistral API: {str(e)}")
            self._update_health_status(success=False, error=str(e))
            return {
                "error": str(e),
                "error_type": "UnexpectedError",
                "model_info": self.get_model_info(),
            }

    async def embeddings(self, text: str) -> Dict[str, Any]:
        """
        Генерирует векторные представления для текста.

        Args:
            text: Текст для векторизации

        Returns:
            Dict с результатом
        """
        endpoint = f"{self.base_url}/v1/embeddings"
        
        payload = {
            "model": f"{self.model_name}-embeddings",  # Обычно для эмбеддингов используется специальная модель
            "input": text
        }
        
        try:
            response = await self._execute_request_with_retry(endpoint, payload)
            
            result = {
                "embeddings": response["data"][0]["embedding"],
                "usage": response.get("usage", {"prompt_tokens": 0}),
                "model_info": self.get_model_info(),
            }
            
            # Обновляем статус здоровья
            self._update_health_status(success=True)
            
            return result
        except MistralApiError as e:
            logger.error(f"Ошибка Mistral API при получении эмбеддингов: {str(e)}")
            self._update_health_status(success=False, error=str(e))
            return {
                "error": str(e),
                "error_type": e.__class__.__name__,
                "model_info": self.get_model_info(),
            }
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении эмбеддингов от Mistral API: {str(e)}")
            self._update_health_status(success=False, error=str(e))
            return {
                "error": str(e),
                "error_type": "UnexpectedError",
                "model_info": self.get_model_info(),
            }

    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели.

        Returns:
            Dict с информацией о модели
        """
        return self._model_info
        
    def get_health_status(self) -> Dict[str, Any]:
        """
        Возвращает текущий статус здоровья адаптера.
        
        Returns:
            Dict с информацией о состоянии адаптера
        """
        return self._health_status

    async def _execute_request_with_retry(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к API с механизмом повторных попыток.

        Args:
            endpoint: URL эндпоинта
            payload: Данные запроса

        Returns:
            Dict с ответом от API

        Raises:
            MistralApiError: При ошибке запроса или обработки ответа
        """
        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                return await self._execute_request(endpoint, payload)
            except MistralRateLimitError as e:
                # Всегда повторяем запрос при превышении лимита
                last_exception = e
                logger.warning(f"Превышен лимит запросов (попытка {retries+1}/{self.max_retries+1}): {str(e)}")
            except MistralServerError as e:
                # Повторяем запрос при ошибке сервера
                last_exception = e
                logger.warning(f"Ошибка сервера Mistral (попытка {retries+1}/{self.max_retries+1}): {str(e)}")
            except MistralTimeoutError as e:
                # Повторяем запрос при таймауте
                last_exception = e
                logger.warning(f"Таймаут запроса (попытка {retries+1}/{self.max_retries+1}): {str(e)}")
            except MistralConnectionError as e:
                # Повторяем запрос при ошибке соединения
                last_exception = e
                logger.warning(f"Ошибка соединения (попытка {retries+1}/{self.max_retries+1}): {str(e)}")
            except (MistralAuthenticationError, MistralValidationError) as e:
                # Не повторяем запрос при ошибках аутентификации и валидации
                logger.error(f"Ошибка аутентификации или валидации: {str(e)}")
                raise
            except Exception as e:
                # Для прочих ошибок делаем одну повторную попытку
                last_exception = e
                logger.warning(f"Непредвиденная ошибка (попытка {retries+1}/{self.max_retries+1}): {str(e)}")
                
            # Увеличиваем счетчик попыток
            retries += 1
            
            # Если достигнут лимит повторных попыток, выходим
            if retries > self.max_retries:
                break
                
            # Вычисляем время задержки с экспоненциальным ростом
            backoff = min(
                self.max_backoff,
                self.initial_backoff * (self.backoff_factor ** (retries - 1))
            )
            
            # Добавляем случайный разброс (jitter)
            jitter_amount = backoff * self.jitter
            backoff = backoff + random.uniform(-jitter_amount, jitter_amount)
            
            logger.info(f"Повторная попытка через {backoff:.2f} секунд...")
            await asyncio.sleep(backoff)
        
        # Если все попытки исчерпаны, выбрасываем последнее исключение
        if last_exception:
            logger.error(f"Все попытки исчерпаны. Последняя ошибка: {str(last_exception)}")
            raise last_exception
        
        # На всякий случай, хотя этот код не должен выполняться
        raise MistralApiError("Все попытки запроса исчерпаны")

    async def _execute_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к API.

        Args:
            endpoint: URL эндпоинта
            payload: Данные запроса

        Returns:
            Dict с ответом от API

        Raises:
            MistralApiError: При ошибке запроса или обработки ответа
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        raise MistralApiError(f"Ошибка декодирования JSON-ответа от {endpoint}")
                elif response.status_code == 429:
                    raise MistralRateLimitError(f"Превышен лимит запросов: {response.text}")
                elif response.status_code >= 500:
                    raise MistralServerError(f"Ошибка на сервере: {response.status_code}, {response.text}")
                elif response.status_code == 401:
                    raise MistralAuthenticationError(f"Ошибка аутентификации: {response.text}")
                elif response.status_code == 400:
                    raise MistralValidationError(f"Ошибка валидации: {response.text}")
                else:
                    raise MistralApiError(f"Ошибка API: {response.status_code}, {response.text}")
        except httpx.TimeoutException:
            raise MistralTimeoutError(f"Превышено время ожидания ({self.timeout}с) при запросе к {endpoint}")
        except httpx.RequestError as e:
            raise MistralConnectionError(f"Ошибка соединения с {endpoint}: {str(e)}")
        except (MistralApiError, MistralConnectionError, MistralTimeoutError, 
                MistralRateLimitError, MistralServerError, MistralAuthenticationError, 
                MistralValidationError):
            # Пробрасываем специализированные исключения
            raise
        except Exception as e:
            raise MistralApiError(f"Непредвиденная ошибка при запросе к {endpoint}: {str(e)}")

    async def _stream_response(self, response_stream):
        """
        Обрабатывает потоковый ответ от API.
        
        Args:
            response_stream: Поток ответа от API
            
        Yields:
            Фрагменты ответа модели
        """
        buffer = ""
        try:
            async for chunk in response_stream:
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    if "delta" in chunk["choices"][0] and "content" in chunk["choices"][0]["delta"]:
                        content = chunk["choices"][0]["delta"]["content"]
                        buffer += content
                        yield {
                            "text": content,
                            "buffer": buffer,
                            "finished": False,
                            "model_info": self.get_model_info(),
                        }
            
            # Финальный чанк
            yield {
                "text": "",
                "buffer": buffer,
                "finished": True,
                "model_info": self.get_model_info(),
            }
        except Exception as e:
            logger.error(f"Ошибка при обработке потока: {str(e)}")
            yield {
                "error": str(e),
                "buffer": buffer,
                "finished": True,
                "model_info": self.get_model_info(),
            }

    def _update_health_status(self, success: bool, error: Optional[str] = None) -> None:
        """
        Обновляет информацию о состоянии адаптера.
        
        Args:
            success: Успешно ли выполнился запрос
            error: Текст ошибки (если запрос не успешен)
        """
        current_time = time.time()
        
        if success:
            self._health_status["is_available"] = True
            self._health_status["last_success"] = current_time
            self._health_status["success_count"] += 1
            # Сбрасываем счетчик ошибок при успешном запросе
            self._health_status["error_count"] = 0
        else:
            self._health_status["last_error"] = error
            self._health_status["error_count"] += 1
            
            # Если накопилось достаточно ошибок, помечаем как недоступный
            if self._health_status["error_count"] >= 3:
                self._health_status["is_available"] = False 