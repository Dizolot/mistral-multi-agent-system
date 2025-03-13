#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адаптер для работы с моделями Mistral AI через их официальный API.
"""

import json
import os
from typing import Dict, List, Any, Optional, Union

import mistralai.client
import mistralai.models.chat_completion
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage, ChatCompletionResponse

from src.integration.model_adapters.model_adapter_base import ModelAdapterBase


class MistralAdapter(ModelAdapterBase):
    """
    Адаптер для работы с моделями Mistral AI.
    
    Обеспечивает взаимодействие с моделями Mistral через официальный API,
    абстрагируя особенности API и форматирования данных.
    """
    
    DEFAULT_MODELS = {
        "default": "mistral-large-latest",
        "embedding": "mistral-embed"
    }
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        **kwargs
    ):
        """
        Инициализация адаптера для Mistral.
        
        Args:
            model_name: Название используемой модели Mistral
            api_key: API ключ для доступа к Mistral API
            api_base: Базовый URL API (можно переопределить)
            **kwargs: Дополнительные параметры конфигурации
        """
        # Определяем модель по умолчанию, если не указана
        if model_name is None:
            model_name = self.DEFAULT_MODELS["default"]
        
        # Получаем API ключ из переменных окружения, если не указан
        if api_key is None:
            api_key = os.environ.get("MISTRAL_API_KEY")
            if api_key is None:
                raise ValueError("API ключ Mistral не найден. Укажите его в параметрах или переменной окружения MISTRAL_API_KEY")
        
        super().__init__(model_name, api_key, api_base, **kwargs)
        
        # Инициализируем клиент Mistral
        self.client = MistralClient(api_key=self.api_key, endpoint=self.api_base)
        self.logger.info(f"Адаптер Mistral инициализирован с моделью {model_name}")
        
        # Модель для эмбеддингов
        self.embedding_model = kwargs.get("embedding_model", self.DEFAULT_MODELS["embedding"])
    
    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Генерация текста с использованием модели Mistral.
        
        Args:
            prompt: Основной запрос (промпт) для модели
            system_message: Системное сообщение, определяющее поведение модели
            temperature: Температура генерации (влияет на креативность/детерминированность)
            max_tokens: Максимальное количество токенов в генерируемом ответе
            stop_sequences: Последовательности, при достижении которых генерация останавливается
            **kwargs: Дополнительные параметры для генерации
            
        Returns:
            str: Сгенерированный моделью текст
        """
        try:
            # Формируем сообщения для чата
            messages = []
            
            # Добавляем системное сообщение, если оно указано
            if system_message:
                messages.append(ChatMessage(role="system", content=system_message))
            
            # Добавляем сообщение пользователя
            messages.append(ChatMessage(role="user", content=prompt))
            
            # Подготавливаем параметры для запроса
            request_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }
            
            # Добавляем опциональные параметры
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            
            if stop_sequences:
                request_params["stop"] = stop_sequences
            
            # Добавляем дополнительные параметры из kwargs
            for key, value in kwargs.items():
                if key not in request_params:
                    request_params[key] = value
            
            # Отправляем запрос к API
            self.logger.debug(f"Отправка запроса к Mistral API: {request_params}")
            chat_response = self.client.chat(**request_params)
            
            # Извлекаем и возвращаем сгенерированный текст
            response_text = chat_response.choices[0].message.content
            self.logger.debug(f"Получен ответ от Mistral API: {response_text[:100]}...")
            
            return response_text
        
        except Exception as e:
            self.logger.error(f"Ошибка при генерации текста через Mistral API: {str(e)}")
            raise
    
    def generate_with_json(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        json_schema: Dict[str, Any] = None,
        temperature: float = 0.2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Генерация ответа в формате JSON с использованием модели Mistral.
        
        Args:
            prompt: Основной запрос (промпт) для модели
            system_message: Системное сообщение, определяющее поведение модели
            json_schema: Схема ожидаемого JSON ответа
            temperature: Температура генерации (для JSON обычно используется низкая)
            **kwargs: Дополнительные параметры для генерации
            
        Returns:
            Dict[str, Any]: Сгенерированный моделью ответ в формате JSON
        """
        try:
            # Формируем промпт для получения JSON
            if json_schema:
                json_schema_str = json.dumps(json_schema, ensure_ascii=False, indent=2)
                
                if system_message:
                    enhanced_system_message = (
                        f"{system_message}\n\n"
                        f"Ты должен вернуть ответ в формате JSON, соответствующий следующей схеме:\n"
                        f"```json\n{json_schema_str}\n```\n"
                        f"Важно! Возвращай только JSON без дополнительного текста."
                    )
                else:
                    enhanced_system_message = (
                        f"Ты должен вернуть ответ в формате JSON, соответствующий следующей схеме:\n"
                        f"```json\n{json_schema_str}\n```\n"
                        f"Важно! Возвращай только JSON без дополнительного текста."
                    )
                
                enhanced_prompt = f"{prompt}\n\nОтвет должен быть в формате JSON."
                
                # Генерируем ответ с уменьшенной температурой для более детерминированного результата
                response_text = self.generate(
                    prompt=enhanced_prompt,
                    system_message=enhanced_system_message,
                    temperature=temperature,
                    **kwargs
                )
            else:
                # Если схема не указана, просто запрашиваем JSON
                if system_message:
                    enhanced_system_message = f"{system_message}\n\nВерни ответ в формате JSON. Только JSON, без дополнительного текста."
                else:
                    enhanced_system_message = "Верни ответ в формате JSON. Только JSON, без дополнительного текста."
                
                response_text = self.generate(
                    prompt=prompt,
                    system_message=enhanced_system_message,
                    temperature=temperature,
                    **kwargs
                )
            
            # Извлекаем JSON из ответа
            # Сначала попробуем напрямую парсить весь ответ
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Если не получилось, попробуем найти JSON в тексте с помощью регулярных выражений
                import re
                
                # Ищем текст между ```json и ```
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # Ищем что-то похожее на JSON объект
                json_match = re.search(r'(\{[\s\S]*\})', response_text)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # Если все попытки не удались, логируем ошибку и возвращаем текст в специальном формате
                self.logger.error(f"Не удалось извлечь JSON из ответа модели: {response_text}")
                return {"error": "Failed to parse JSON", "raw_response": response_text}
        
        except Exception as e:
            self.logger.error(f"Ошибка при генерации JSON через Mistral API: {str(e)}")
            raise
    
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Получение векторных эмбеддингов для текста или списка текстов с использованием модели Mistral.
        
        Args:
            text: Текст или список текстов для векторизации
            
        Returns:
            Union[List[float], List[List[float]]]: Векторные представления текстов
        """
        try:
            # Преобразуем одиночный текст в список для единообразной обработки
            if isinstance(text, str):
                texts = [text]
                single_input = True
            else:
                texts = text
                single_input = False
            
            # Получаем эмбеддинги
            embedding_response = self.client.embeddings(
                model=self.embedding_model,
                input=texts
            )
            
            # Извлекаем векторы из ответа
            embeddings = [data.embedding for data in embedding_response.data]
            
            # Возвращаем одиночный вектор или список векторов в зависимости от входных данных
            if single_input:
                return embeddings[0]
            else:
                return embeddings
        
        except Exception as e:
            self.logger.error(f"Ошибка при получении эмбеддингов через Mistral API: {str(e)}")
            raise 