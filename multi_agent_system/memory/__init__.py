"""
Пакет для хранения и управления памятью разговоров в мульти-агентной системе.

Этот пакет предоставляет инструменты для:
- Хранения истории диалогов с пользователями
- Суммаризации длинных разговоров
- Предоставления контекста для агентов при обработке запросов
"""

from multi_agent_system.memory.conversation_memory import ConversationMemoryManager

__all__ = [
    'ConversationMemoryManager'
] 