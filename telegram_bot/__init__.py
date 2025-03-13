"""
Инициализация пакета telegram_bot
"""

from telegram_bot.telegram_bot import create_application
from telegram_bot.model_service_client import ModelServiceClient

__all__ = ['create_application', 'ModelServiceClient'] 