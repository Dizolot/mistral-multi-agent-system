#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт мониторинга сервера Mistral API

Этот скрипт:
1. Периодически проверяет доступность API Mistral
2. Отправляет уведомления при недоступности через Telegram
3. Автоматически перезапускает сервис при необходимости
4. Ведет детальный лог всех проблем и действий
"""

import os
import sys
import time
import json
import logging
import requests
import subprocess
from datetime import datetime
from pathlib import Path

# Настройка логирования
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'api_monitoring.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('api_monitor')

# Конфигурация
CONFIG = {
    'api_url': 'http://139.59.241.176:8080',
    'health_endpoint': '/health',  # Если есть такой эндпоинт
    'test_endpoint': '/v1/chat/completions',  # Для тестового запроса
    'check_interval': 60,  # Проверка каждую минуту
    'max_restart_attempts': 3,  # Максимальное количество попыток перезапуска
    'restart_command': 'ssh root@139.59.241.176 "systemctl restart llama-server.service"',  # Команда для перезапуска сервиса
    'telegram_bot_token': '7835434491:AAEFMJLLKuSJzPkwKsDtcJ7q5BjzgsqNiQw',  # Токен бота для уведомлений
    'telegram_chat_id': '123456789',  # ID чата для уведомлений (нужно заменить на реальный)
    'alert_threshold': 3,  # Количество ошибок подряд для отправки уведомления
}

# Счетчик неудачных проверок подряд
consecutive_failures = 0
restart_attempts = 0

def check_api_health():
    """Проверка доступности API"""
    global consecutive_failures
    
    logger.info(f"Проверка доступности API по адресу {CONFIG['api_url']}")
    
    # Проверка через health endpoint, если он существует
    if CONFIG['health_endpoint']:
        try:
            health_url = f"{CONFIG['api_url']}{CONFIG['health_endpoint']}"
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"API доступен через health endpoint. Статус: {response.status_code}")
                consecutive_failures = 0
                return True
            else:
                logger.warning(f"API недоступен через health endpoint. Статус: {response.status_code}")
        except Exception as e:
            logger.warning(f"Ошибка при проверке через health endpoint: {e}")
    
    # Проверка через тестовый запрос
    try:
        test_url = f"{CONFIG['api_url']}{CONFIG['test_endpoint']}"
        # Проверяем только доступность эндпоинта, без отправки данных
        response = requests.options(test_url, timeout=10)
        if response.status_code < 500:  # Любой ответ, кроме 5xx
            logger.info(f"API доступен через test endpoint. Статус: {response.status_code}")
            consecutive_failures = 0
            return True
        else:
            logger.warning(f"API недоступен через test endpoint. Статус: {response.status_code}")
            consecutive_failures += 1
    except Exception as e:
        logger.warning(f"Ошибка при проверке через test endpoint: {e}")
        consecutive_failures += 1
    
    logger.error(f"API недоступен. Количество неудачных проверок подряд: {consecutive_failures}")
    return False

def restart_service():
    """Перезапуск сервиса"""
    global restart_attempts
    
    if restart_attempts >= CONFIG['max_restart_attempts']:
        logger.error(f"Достигнуто максимальное количество попыток перезапуска ({CONFIG['max_restart_attempts']})")
        send_telegram_notification(
            f"⚠️ КРИТИЧЕСКАЯ ОШИБКА: Сервер Mistral API недоступен после {CONFIG['max_restart_attempts']} попыток перезапуска. "
            f"Требуется ручное вмешательство!"
        )
        return False
    
    logger.info(f"Попытка перезапуска сервиса (попытка {restart_attempts + 1}/{CONFIG['max_restart_attempts']})")
    
    try:
        # Выполнение команды перезапуска
        result = subprocess.run(
            CONFIG['restart_command'], 
            shell=True, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Сервис успешно перезапущен. Вывод: {result.stdout}")
            restart_attempts += 1
            # Даем сервису время на запуск
            time.sleep(10)
            return True
        else:
            logger.error(f"Ошибка при перезапуске сервиса. Код: {result.returncode}, Ошибка: {result.stderr}")
            restart_attempts += 1
            return False
    except Exception as e:
        logger.error(f"Исключение при перезапуске сервиса: {e}")
        restart_attempts += 1
        return False

def send_telegram_notification(message):
    """Отправка уведомления в Telegram"""
    
    url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/sendMessage"
    
    payload = {
        'chat_id': CONFIG['telegram_chat_id'],
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Уведомление в Telegram отправлено успешно")
        else:
            logger.error(f"Ошибка при отправке уведомления в Telegram. Статус: {response.status_code}, Ответ: {response.text}")
    except Exception as e:
        logger.error(f"Исключение при отправке уведомления в Telegram: {e}")

def run_monitoring():
    """Основной цикл мониторинга"""
    global consecutive_failures, restart_attempts
    
    logger.info("Запуск мониторинга API")
    
    while True:
        api_available = check_api_health()
        
        if not api_available:
            if consecutive_failures >= CONFIG['alert_threshold']:
                # Отправляем уведомление и пытаемся перезапустить сервис
                send_telegram_notification(
                    f"🔴 ВНИМАНИЕ: Сервер Mistral API недоступен! "
                    f"Количество неудачных проверок подряд: {consecutive_failures}. "
                    f"Пытаюсь перезапустить сервис..."
                )
                
                restart_success = restart_service()
                
                if restart_success:
                    # Проверяем снова после перезапуска
                    time.sleep(10)  # Даем сервису время на запуск
                    if check_api_health():
                        send_telegram_notification(
                            f"🟢 Сервер Mistral API снова доступен после перезапуска!"
                        )
                        consecutive_failures = 0
                        restart_attempts = 0
        else:
            # Если после серии сбоев API снова доступен
            if consecutive_failures > 0:
                logger.info(f"API снова доступен после {consecutive_failures} неудачных проверок")
                consecutive_failures = 0
                
                if restart_attempts > 0:
                    send_telegram_notification(
                        f"🟢 Сервер Mistral API снова доступен после {restart_attempts} попыток перезапуска!"
                    )
                    restart_attempts = 0
        
        time.sleep(CONFIG['check_interval'])

if __name__ == "__main__":
    try:
        run_monitoring()
    except KeyboardInterrupt:
        logger.info("Мониторинг остановлен пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка в скрипте мониторинга: {e}")
        send_telegram_notification(
            f"⚠️ КРИТИЧЕСКАЯ ОШИБКА в скрипте мониторинга API: {e}"
        ) 