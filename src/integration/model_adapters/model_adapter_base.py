#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль содержит базовый абстрактный класс для адаптеров языковых моделей.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union


class ModelAdapterBase(ABC):
    """
    Абстрактный базовый класс для адаптеров языковых моделей.
    
    Определяет общий интерфейс, который должны реализовать все конкретные адаптеры,
    работающие с различными провайдерами моделей (Mistral, OpenAI, Anthropic и др.).
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        **kwargs
    ):
        """
        Инициализация базового адаптера модели.
        
        Args:
            model_name: Название используемой модели
            api_key: API ключ для доступа к сервису моделей
            api_base: Базовый URL API (можно переопределить для использования self-hosted решений)
            **kwargs: Дополнительные параметры конфигурации
        """
        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
        self.config = kwargs
        self.logger = logging.getLogger(f"model_adapter.{self.__class__.__name__}")
        self.logger.info(f"Инициализирован адаптер модели {model_name}")
    
    @abstractmethod
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
        Генерация текста с использованием модели.
        
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
        pass
    
    @abstractmethod
    def generate_with_json(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        json_schema: Dict[str, Any] = None,
        temperature: float = 0.2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Генерация ответа в формате JSON с использованием модели.
        
        Args:
            prompt: Основной запрос (промпт) для модели
            system_message: Системное сообщение, определяющее поведение модели
            json_schema: Схема ожидаемого JSON ответа
            temperature: Температура генерации (для JSON обычно используется низкая)
            **kwargs: Дополнительные параметры для генерации
            
        Returns:
            Dict[str, Any]: Сгенерированный моделью ответ в формате JSON
        """
        pass
    
    @abstractmethod
    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Получение векторных эмбеддингов для текста или списка текстов.
        
        Args:
            text: Текст или список текстов для векторизации
            
        Returns:
            Union[List[float], List[List[float]]]: Векторные представления текстов
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Получение информации о модели и адаптере.
        
        Returns:
            Dict[str, Any]: Информация о модели и адаптере
        """
        return {
            "model_name": self.model_name,
            "adapter_type": self.__class__.__name__,
            "api_base": self.api_base
        }
    
    def __str__(self) -> str:
        """
        Строковое представление адаптера модели.
        
        Returns:
            str: Информация об адаптере модели
        """
        return f"{self.__class__.__name__}(model={self.model_name})" 