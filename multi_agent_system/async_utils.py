"""
Утилиты для работы с асинхронным кодом.

Этот модуль содержит утилиты для работы с асинхронным кодом,
в частности, для решения проблем с вложенными циклами событий asyncio.
"""

import nest_asyncio
import asyncio
import logging
from typing import Any, Callable, Coroutine

# Настраиваем логгер
logger = logging.getLogger("async_utils")

# Применяем патч для поддержки вложенных циклов событий
nest_asyncio.apply()
logger.info("nest_asyncio применен для поддержки вложенных циклов событий")

def get_or_create_event_loop():
    """
    Получает текущий цикл событий или создает новый, если текущий не найден.
    
    Returns:
        asyncio.AbstractEventLoop: Цикл событий
    """
    try:
        loop = asyncio.get_event_loop()
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

def sync_to_async(async_func: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs) -> Any:
    """
    Выполняет асинхронную функцию синхронно.
    
    Args:
        async_func: Асинхронная функция
        *args: Позиционные аргументы для асинхронной функции
        **kwargs: Именованные аргументы для асинхронной функции
        
    Returns:
        Any: Результат выполнения асинхронной функции
    """
    loop = get_or_create_event_loop()
    return loop.run_until_complete(async_func(*args, **kwargs))

def run_async_safely(async_func: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs) -> Any:
    """
    Безопасно выполняет асинхронную функцию, обрабатывая ошибки с циклом событий.
    
    Args:
        async_func: Асинхронная функция для выполнения
        *args: Позиционные аргументы для функции
        **kwargs: Именованные аргументы для функции
        
    Returns:
        Any: Результат выполнения асинхронной функции
    """
    try:
        # Пробуем использовать существующий цикл событий
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(async_func(*args, **kwargs))
    except RuntimeError:
        # Если цикл не найден или не запущен, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close() 