#!/usr/bin/env python3
"""
Скрипт для запуска Telegram-бота с интеграцией маршрутизатора LangChain.
Обеспечивает возможность запуска бота в фоновом режиме и управление его жизненным циклом.
"""

import os
import sys
import argparse
import signal
import subprocess
import time
import psutil
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/telegram_bot_with_langchain.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Создаем директорию для логов, если она не существует
os.makedirs("logs", exist_ok=True)

def check_if_process_running(script_name):
    """
    Проверяет, запущен ли уже процесс с указанным именем скрипта.
    
    Args:
        script_name: Имя скрипта для поиска
        
    Returns:
        (bool, Optional[int]): Пара (запущен ли процесс, ID процесса)
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Проверяем команду процесса
            if proc.info['cmdline'] and script_name in ' '.join(proc.info['cmdline']):
                # Если это не текущий процесс
                if proc.pid != os.getpid():
                    return True, proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False, None

def kill_process(pid):
    """
    Завершает процесс с указанным PID.
    
    Args:
        pid: ID процесса для завершения
        
    Returns:
        bool: Успешно ли завершен процесс
    """
    try:
        process = psutil.Process(pid)
        process.terminate()
        # Ждем завершения процесса
        process.wait(timeout=5)
        if process.is_running():
            # Если процесс не завершился, убиваем его принудительно
            process.kill()
        logger.info(f"Процесс с PID {pid} успешно завершен")
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        logger.error(f"Ошибка при завершении процесса с PID {pid}: {str(e)}")
        return False

def start_bot():
    """
    Запускает Telegram-бот с интеграцией маршрутизатора LangChain.
    """
    # Проверяем, запущен ли уже бот
    running, pid = check_if_process_running("telegram_bot/mistral_telegram_bot.py")
    if running:
        logger.info(f"Telegram-бот уже запущен (PID: {pid}). Завершаем старый процесс...")
        kill_process(pid)
    
    # Загружаем переменные окружения из .env файла
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv не установлен, переменные окружения не будут загружены из .env файла")
    
    # Получаем токен Telegram
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    if not telegram_token:
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения")
        sys.exit(1)
    
    # Получаем URL API Mistral
    mistral_api_url = os.getenv("MISTRAL_API_URL", "http://localhost:8080/completion")
    
    # Запускаем бота
    try:
        logger.info("Запускаем Telegram-бот с интеграцией маршрутизатора LangChain...")
        
        # Путь к файлу бота
        bot_script = os.path.join("telegram_bot", "mistral_telegram_bot.py")
        
        # Запускаем бота в фоновом режиме
        process = subprocess.Popen(
            [sys.executable, bot_script],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        
        logger.info(f"Telegram-бот запущен (PID: {process.pid})")
        return process.pid
    
    except Exception as e:
        logger.error(f"Ошибка при запуске Telegram-бота: {str(e)}")
        sys.exit(1)

def stop_bot():
    """
    Останавливает Telegram-бот.
    """
    running, pid = check_if_process_running("telegram_bot/mistral_telegram_bot.py")
    if running:
        logger.info(f"Останавливаем Telegram-бот (PID: {pid})...")
        kill_process(pid)
    else:
        logger.info("Telegram-бот не запущен")

def restart_bot():
    """
    Перезапускает Telegram-бот.
    """
    stop_bot()
    time.sleep(2)  # Ждем, чтобы процесс успел завершиться
    start_bot()

def check_status():
    """
    Проверяет статус Telegram-бота.
    """
    running, pid = check_if_process_running("telegram_bot/mistral_telegram_bot.py")
    if running:
        logger.info(f"Telegram-бот запущен (PID: {pid})")
    else:
        logger.info("Telegram-бот не запущен")

def main():
    """
    Основная функция скрипта.
    """
    parser = argparse.ArgumentParser(description="Запускает Telegram-бот с интеграцией маршрутизатора LangChain")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--start", action="store_true", help="Запускает бот")
    group.add_argument("--stop", action="store_true", help="Останавливает бот")
    group.add_argument("--restart", action="store_true", help="Перезапускает бот")
    group.add_argument("--status", action="store_true", help="Проверяет статус бота")
    
    args = parser.parse_args()
    
    if args.start:
        start_bot()
    elif args.stop:
        stop_bot()
    elif args.restart:
        restart_bot()
    elif args.status:
        check_status()
    else:
        # По умолчанию запускаем бота
        start_bot()

if __name__ == "__main__":
    main() 