#!/usr/bin/env python
"""
Скрипт для запуска Telegram-бота с интеграцией Mistral
"""

import os
import sys
import logging
import psutil
import time
import asyncio
from pathlib import Path

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
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(logs_dir, "telegram_bot.log"))
    ]
)

logger = logging.getLogger(__name__)

# Функция для проверки и остановки уже запущенных экземпляров бота
def check_and_kill_duplicate_bots():
    """
    Проверяет наличие других запущенных экземпляров бота 
    и завершает их перед запуском.
    """
    try:
        current_pid = os.getpid()
        current_process = psutil.Process(current_pid)
        bot_processes_found = False
        
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            if process.info['pid'] != current_pid and process.info['name'] == current_process.name():
                cmdline = ' '.join(process.info['cmdline']) if process.info['cmdline'] else ''
                if any(x in cmdline for x in ['run_telegram_bot.py', 'telegram_bot.py']):
                    # Проверяем, не является ли процесс родительским для текущего
                    if process.info['pid'] != os.getppid():
                        logger.warning(f"Найден дубликат процесса бота с PID {process.info['pid']}, завершаем его")
                        try:
                            process.terminate()
                            bot_processes_found = True
                        except psutil.NoSuchProcess:
                            logger.warning(f"Процесс {process.info['pid']} уже завершен")
        
        # Если нашли другие процессы, ждем их завершения
        if bot_processes_found:
            logger.info("Ожидаем завершения других экземпляров бота...")
            time.sleep(2)  # Даем время на корректное завершение
            
        return bot_processes_found
    except Exception as e:
        logger.warning(f"Ошибка при проверке дубликатов бота: {e}")
        return False

if __name__ == "__main__":
    try:
        # Проверяем и останавливаем другие экземпляры бота
        check_and_kill_duplicate_bots()
        
        # Импортируем модуль создания приложения
        from telegram_bot import create_application
        from telegram_bot.config import config
        
        # Выводим информацию о запуске
        logger.info("Запуск Telegram-бота с интеграцией Mistral")
        
        # Создаем и запускаем приложение
        application = asyncio.run(create_application(config))
        application.run_polling()
        
        logger.info("Бот запущен и готов к работе")
    except Exception as e:
        logger.exception(f"Ошибка при запуске бота: {e}")
        sys.exit(1) 