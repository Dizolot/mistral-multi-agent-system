"""
Модуль интеграции с Telegram для мульти-агентной системы.

Этот модуль предоставляет компоненты для интеграции Telegram-ботов с оркестратором.
"""

from multi_agent_system.integrations.telegram.telegram_bot_adapter import TelegramBotAdapter
from multi_agent_system.integrations.telegram.message_router import MessageRouter
from multi_agent_system.integrations.telegram.orchestrator_client import OrchestratorClient
from multi_agent_system.integrations.telegram.integration import TelegramIntegration

__all__ = [
    'TelegramBotAdapter',
    'MessageRouter',
    'OrchestratorClient',
    'TelegramIntegration'
] 