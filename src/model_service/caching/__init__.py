"""
Модуль кэширования.
Обеспечивает кэширование ответов моделей для оптимизации использования ресурсов.
"""

from .response_cache import ResponseCache

__all__ = [
    'ResponseCache',
] 