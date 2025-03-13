"""
Модуль для кэширования ответов моделей.
Реализует механизм кэширования запросов и ответов для оптимизации использования ресурсов.
"""

import time
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

# Настройка логирования
logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Класс для кэширования ответов языковых моделей.
    Позволяет сохранять результаты запросов и получать их при повторном запросе,
    что экономит время и ресурсы.
    """

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Инициализирует кэш с указанными параметрами.

        Args:
            max_size: Максимальный размер кэша (количество элементов)
            ttl: Время жизни элементов в кэше (в секундах)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[Dict[str, Any], float]] = {}  # {key: (response, timestamp)}
        self.hits = 0
        self.misses = 0
        
        logger.info(f"Инициализирован кэш размером {max_size} элементов с TTL {ttl} секунд")

    def get(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Получает закэшированный ответ, если он существует и не устарел.

        Args:
            messages: Список сообщений запроса
            model: Название модели
            params: Параметры запроса

        Returns:
            Закэшированный ответ или None, если кэш отсутствует или устарел
        """
        cache_key = self._generate_cache_key(messages, model, params)
        
        if cache_key in self.cache:
            cached_response, timestamp = self.cache[cache_key]
            
            # Проверяем, не устарел ли кэш
            if time.time() - timestamp <= self.ttl:
                self.hits += 1
                logger.debug(f"Кэш-хит для запроса к модели {model}. Хитрейт: {self.hit_rate():.2f}")
                return cached_response
            else:
                # Удаляем устаревший кэш
                del self.cache[cache_key]
                logger.debug(f"Удален устаревший кэш для запроса к модели {model}")
        
        self.misses += 1
        logger.debug(f"Кэш-мисс для запроса к модели {model}. Хитрейт: {self.hit_rate():.2f}")
        return None

    def set(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        params: Dict[str, Any], 
        response: Dict[str, Any]
    ) -> None:
        """
        Сохраняет ответ в кэш.

        Args:
            messages: Список сообщений запроса
            model: Название модели
            params: Параметры запроса
            response: Ответ модели для кэширования
        """
        cache_key = self._generate_cache_key(messages, model, params)
        
        # Если кэш переполнен, удаляем самый старый элемент
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
            del self.cache[oldest_key]
            logger.debug(f"Кэш переполнен, удален самый старый элемент")
        
        self.cache[cache_key] = (response, time.time())
        logger.debug(f"Добавлен новый элемент в кэш для модели {model}")

    def clear(self) -> None:
        """Очищает кэш"""
        self.cache.clear()
        logger.info("Кэш полностью очищен")

    def hit_rate(self) -> float:
        """
        Вычисляет соотношение попаданий в кэш.

        Returns:
            Процент попаданий в кэш (от 0.0 до 1.0)
        """
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику использования кэша.

        Returns:
            Словарь со статистикой:
            - hits: количество попаданий
            - misses: количество промахов
            - hit_rate: соотношение попаданий
            - size: текущий размер кэша
            - max_size: максимальный размер кэша
        """
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate(),
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl
        }

    def _generate_cache_key(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        params: Dict[str, Any]
    ) -> str:
        """
        Генерирует уникальный ключ для кэширования.

        Args:
            messages: Список сообщений запроса
            model: Название модели
            params: Параметры запроса

        Returns:
            Строковый хеш-ключ для кэширования
        """
        # Отфильтровываем параметры, влияющие на генерацию
        relevant_params = {
            k: v for k, v in params.items() 
            if k in ["temperature", "max_tokens", "top_p", "presence_penalty", "frequency_penalty"]
        }
        
        # Создаем словарь для хеширования
        cache_dict = {
            "messages": messages,
            "model": model,
            "params": relevant_params
        }
        
        # Преобразуем в строку и хешируем
        cache_str = json.dumps(cache_dict, sort_keys=True)
        return hashlib.md5(cache_str.encode("utf-8")).hexdigest() 