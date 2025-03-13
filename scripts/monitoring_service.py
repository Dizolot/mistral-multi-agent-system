#!/usr/bin/env python3

import os
import time
import requests
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/monitoring/logs/monitoring.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Конфигурация
MISTRAL_API_URL = os.getenv('MISTRAL_API_URL', 'http://139.59.241.176:8000')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # интервал проверки в секундах
HEALTH_CHECK_ENDPOINT = '/health'

def check_api_health():
    """Проверка здоровья Mistral API"""
    try:
        response = requests.get(f"{MISTRAL_API_URL}{HEALTH_CHECK_ENDPOINT}")
        if response.status_code == 200:
            logger.info("Mistral API работает нормально")
            return True
        else:
            logger.error(f"Mistral API вернул код {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при проверке Mistral API: {e}")
        return False

def main():
    """Основной цикл мониторинга"""
    logger.info("Запуск сервиса мониторинга Mistral API")
    logger.info(f"Проверка API по адресу: {MISTRAL_API_URL}")
    logger.info(f"Интервал проверки: {CHECK_INTERVAL} секунд")

    while True:
        check_api_health()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main() 