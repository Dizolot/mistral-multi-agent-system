"""
Базовый класс адаптера для языковых моделей.
Предоставляет унифицированный интерфейс для работы с различными моделями.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ModelAdapter(ABC):
    """
    Абстрактный базовый класс для адаптеров различных языковых моделей.
    Определяет общий интерфейс для работы с моделями независимо от их поставщика.
    """

    @abstractmethod
    async def generate(self, prompt: str, **params) -> Dict[str, Any]:
        """
        Генерирует текст на основе промпта.

        Args:
            prompt: Текстовый промпт для генерации
            **params: Дополнительные параметры генерации (temperature, max_tokens и т.д.)

        Returns:
            Dict с результатом генерации, содержащий ключи:
            - text: сгенерированный текст
            - usage: статистика использования (токены и т.д.)
            - model_info: информация о модели
        """
        pass

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **params) -> Dict[str, Any]:
        """
        Обрабатывает запрос в формате чата (серия сообщений).

        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "Привет"}, ...]
            **params: Дополнительные параметры генерации (temperature, max_tokens и т.д.)

        Returns:
            Dict с результатом генерации, содержащий ключи:
            - text: сгенерированный текст
            - usage: статистика использования (токены и т.д.)
            - model_info: информация о модели
        """
        pass

    @abstractmethod
    async def embeddings(self, text: str) -> Dict[str, Any]:
        """
        Генерирует векторные представления (эмбеддинги) для текста.

        Args:
            text: Текст для векторизации

        Returns:
            Dict с результатом, содержащий ключи:
            - embeddings: векторное представление текста
            - usage: статистика использования (токены и т.д.)
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели.

        Returns:
            Dict с информацией о модели:
            - name: название модели
            - provider: поставщик модели
            - max_tokens: максимальное количество токенов
            - capabilities: список возможностей (chat, completion, embeddings, etc.)
        """
        pass 