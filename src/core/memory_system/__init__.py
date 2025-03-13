#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Система памяти - компонент ядра системы, отвечающий за хранение и управление
контекстом диалогов, историей взаимодействий и дополнительной информацией.

Обеспечивает персистентное хранение данных для обеспечения контекстного
понимания запросов и долгосрочной памяти при взаимодействии с пользователями.
"""

# Экспортируем базовые классы и интерфейсы
from src.core.memory_system.memory_base import (
    Message,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    MemoryBase
)

# Экспортируем реализации памяти
from src.core.memory_system.buffer_memory import BufferMemory
from src.core.memory_system.summary_memory import SummaryMemory

# Экспортируем менеджер памяти
from src.core.memory_system.memory_manager import MemoryManager

# Экспортируем суммаризаторы
from src.core.memory_system.summarizers import (
    create_default_summarizer,
    create_simple_summarizer,
    create_keyword_summarizer
)

__all__ = [
    # Базовые классы
    'Message',
    'UserMessage',
    'AssistantMessage',
    'SystemMessage',
    'MemoryBase',
    
    # Реализации памяти
    'BufferMemory',
    'SummaryMemory',
    
    # Менеджер памяти
    'MemoryManager',
    
    # Суммаризаторы
    'create_default_summarizer',
    'create_simple_summarizer',
    'create_keyword_summarizer'
]
