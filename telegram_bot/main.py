"""
Основной файл для запуска Telegram-бота.
"""

import os
import logging
from telegram_bot import main

if __name__ == "__main__":
    # Создаем директорию для логов, если её нет
    os.makedirs("logs", exist_ok=True)
    
    # Запускаем бота
    main() 