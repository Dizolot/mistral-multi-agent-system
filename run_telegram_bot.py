#!/usr/bin/env python
"""
Скрипт для запуска Telegram-бота с интеграцией Mistral
"""

import os
import sys
import logging
import psutil
import time
from pathlib import Path
from telegram.ext import Application
from telegram_bot.config import config
from telegram_bot.model_service_client import ModelServiceClient

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Создаем директорию для логов, если она не существует
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "telegram_bot.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_and_kill_duplicate_bots():
    """
    Проверяет и завершает другие экземпляры бота
    """
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'python' in proc.info['cmdline'][0] and 'run_telegram_bot.py' in ' '.join(proc.info['cmdline']):
                if proc.info['pid'] != current_pid:
                    logger.warning(f"Найден дубликат процесса бота с PID {proc.info['pid']}, завершаем его")
                    psutil.Process(proc.info['pid']).terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Даем время на завершение процессов
    logger.info("Ожидаем завершения других экземпляров бота...")
    time.sleep(2)

def main():
    """
    Основная функция для запуска бота
    """
    try:
        # Проверяем и останавливаем другие экземпляры бота
        check_and_kill_duplicate_bots()
        
        # Выводим информацию о запуске
        logger.info("Запуск Telegram-бота с интеграцией Mistral")
        
        # Создаем и запускаем приложение
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Инициализируем клиент сервиса моделей
        client = ModelServiceClient(model_name="mistral")
        application.bot_data["client"] = client
        
        # Добавляем обработчики
        from telegram_bot.telegram_bot import (
            start, help_command, reset, message_handler
        )
        from telegram.ext import CommandHandler, MessageHandler, filters
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("reset", reset))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        # Запускаем бота
        logger.info("Запускаем бота в режиме polling...")
        application.run_polling(drop_pending_updates=True)
        
        logger.info("Бот запущен и готов к работе")
    except Exception as e:
        logger.exception(f"Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения, останавливаем бота...")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1) 