#!/usr/bin/env python3

import os
import time
import requests
import logging
import subprocess
import json
from datetime import datetime, timedelta

# Настройка логирования
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
log_dir = os.getenv('LOG_DIR', os.path.join(project_root, 'logs'))
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{log_dir}/monitoring.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('api_monitor')

# Конфигурация
MISTRAL_API_URL = os.getenv('MISTRAL_API_URL', 'http://139.59.241.176:8080')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # интервал проверки в секундах
HEALTH_CHECK_ENDPOINT = '/v1/models'  # Проверка через реальный API эндпоинт
RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '3'))  # количество попыток перед рестартом
RESTART_SCRIPT = os.getenv('RESTART_SCRIPT', os.path.join(script_dir, 'restart_mistral_api.sh'))
RESTART_COOLDOWN = int(os.getenv('RESTART_COOLDOWN', '300'))  # время в секундах между рестартами
MAX_RESTARTS_PER_DAY = int(os.getenv('MAX_RESTARTS_PER_DAY', '5'))  # максимальное количество рестартов в день

# Telegram конфигурация для уведомлений
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
NOTIFICATION_ENABLED = TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# Состояние мониторинга
monitoring_state = {
    'last_restart_time': None,
    'restart_count': 0,
    'restart_dates': [],
    'last_status': True,
    'consecutive_failures': 0,
    'total_checks': 0,
    'uptime_checks': 0
}

def send_telegram_notification(message):
    """Отправка уведомления через Telegram бота"""
    if not NOTIFICATION_ENABLED:
        logger.info("Уведомления отключены: не настроены токен или chat_id")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            logger.info("Уведомление в Telegram отправлено успешно")
        else:
            logger.error(f"Ошибка при отправке уведомления в Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Исключение при отправке уведомления в Telegram: {e}")

def check_api_health():
    """Проверка здоровья Mistral API"""
    try:
        start_time = time.time()
        response = requests.get(f"{MISTRAL_API_URL}{HEALTH_CHECK_ENDPOINT}", timeout=10)
        response_time = time.time() - start_time
        
        monitoring_state['total_checks'] += 1
        
        if response.status_code == 200:
            models_info = response.json()
            model_count = len(models_info.get('data', []))
            logger.info(f"Mistral API работает нормально, доступно {model_count} моделей, "
                       f"время ответа: {response_time:.2f} сек")
            
            monitoring_state['consecutive_failures'] = 0
            monitoring_state['uptime_checks'] += 1
            
            # Если API восстановился после сбоя, отправляем уведомление
            if not monitoring_state['last_status']:
                uptime_percentage = (monitoring_state['uptime_checks'] / monitoring_state['total_checks']) * 100
                message = (f"✅ *Mistral API восстановлен*\n"
                          f"API снова доступен на {MISTRAL_API_URL}\n"
                          f"Доступно моделей: {model_count}\n"
                          f"Время ответа: {response_time:.2f} сек\n"
                          f"Аптайм: {uptime_percentage:.1f}%")
                send_telegram_notification(message)
            
            monitoring_state['last_status'] = True
            return True
        else:
            logger.error(f"Mistral API вернул код {response.status_code}, тело ответа: {response.text}")
            monitoring_state['consecutive_failures'] += 1
            monitoring_state['last_status'] = False
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при проверке Mistral API: {e}")
        monitoring_state['consecutive_failures'] += 1
        monitoring_state['last_status'] = False
        return False

def restart_mistral_api():
    """Перезапуск сервиса Mistral API"""
    now = datetime.now()
    
    # Проверка времени охлаждения между рестартами
    if (monitoring_state['last_restart_time'] and 
        (now - monitoring_state['last_restart_time']).total_seconds() < RESTART_COOLDOWN):
        logger.warning("Рестарт не выполнен: не прошло достаточно времени с последнего рестарта")
        return False
    
    # Проверка максимального количества рестартов в день
    today = now.strftime('%Y-%m-%d')
    restarts_today = sum(1 for date in monitoring_state['restart_dates'] if date.startswith(today))
    
    if restarts_today >= MAX_RESTARTS_PER_DAY:
        logger.error(f"Превышено максимальное количество рестартов на сегодня ({MAX_RESTARTS_PER_DAY})")
        message = (f"⚠️ *Превышение лимита рестартов*\n"
                  f"Достигнут лимит {MAX_RESTARTS_PER_DAY} рестартов в день для Mistral API.\n"
                  f"Требуется ручное вмешательство!")
        send_telegram_notification(message)
        return False
    
    try:
        # Отправляем уведомление о рестарте
        message = (f"🔄 *Перезапуск Mistral API*\n"
                  f"Причина: API недоступен {monitoring_state['consecutive_failures']} проверок подряд\n"
                  f"Сервер: {MISTRAL_API_URL}")
        send_telegram_notification(message)
        
        logger.info(f"Выполняется перезапуск Mistral API с помощью скрипта {RESTART_SCRIPT}")
        
        # Выполнение скрипта перезапуска
        result = subprocess.run(
            ['bash', RESTART_SCRIPT], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Рестарт успешно выполнен: {result.stdout}")
            monitoring_state['last_restart_time'] = now
            monitoring_state['restart_count'] += 1
            monitoring_state['restart_dates'].append(now.strftime('%Y-%m-%d %H:%M:%S'))
            return True
        else:
            logger.error(f"Ошибка при рестарте: {result.stderr}")
            message = (f"❌ *Ошибка перезапуска Mistral API*\n"
                      f"Скрипт перезапуска вернул ошибку:\n"
                      f"```\n{result.stderr}\n```")
            send_telegram_notification(message)
            return False
    except Exception as e:
        logger.error(f"Исключение при рестарте Mistral API: {e}")
        message = (f"❌ *Исключение при перезапуске Mistral API*\n"
                  f"Ошибка: {str(e)}")
        send_telegram_notification(message)
        return False

def save_state():
    """Сохранение состояния мониторинга в файл"""
    state_to_save = monitoring_state.copy()
    # Преобразуем datetime в строки для сериализации
    if state_to_save['last_restart_time']:
        state_to_save['last_restart_time'] = state_to_save['last_restart_time'].strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with open(f'{log_dir}/monitoring_state.json', 'w') as f:
            json.dump(state_to_save, f, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении состояния: {e}")

def load_state():
    """Загрузка состояния мониторинга из файла"""
    try:
        if os.path.exists(f'{log_dir}/monitoring_state.json'):
            with open(f'{log_dir}/monitoring_state.json', 'r') as f:
                loaded_state = json.load(f)
                
            # Преобразуем строковые даты обратно в datetime
            if loaded_state.get('last_restart_time'):
                loaded_state['last_restart_time'] = datetime.strptime(
                    loaded_state['last_restart_time'], '%Y-%m-%d %H:%M:%S'
                )
            
            # Обновляем глобальное состояние
            monitoring_state.update(loaded_state)
            logger.info(f"Загружено состояние мониторинга: перезапусков - {monitoring_state['restart_count']}")
    except Exception as e:
        logger.error(f"Ошибка при загрузке состояния: {e}")

def generate_report():
    """Генерация отчета о работе мониторинга"""
    uptime_percentage = 0
    if monitoring_state['total_checks'] > 0:
        uptime_percentage = (monitoring_state['uptime_checks'] / monitoring_state['total_checks']) * 100
    
    report = (
        f"\n===== Отчет о работе мониторинга Mistral API =====\n"
        f"Время отчета: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"API URL: {MISTRAL_API_URL}\n"
        f"Всего проверок: {monitoring_state['total_checks']}\n"
        f"Успешных проверок: {monitoring_state['uptime_checks']}\n"
        f"Аптайм: {uptime_percentage:.1f}%\n"
        f"Всего перезапусков: {monitoring_state['restart_count']}\n"
        f"Последний перезапуск: {monitoring_state['last_restart_time'] or 'нет'}\n"
        f"========================================\n"
    )
    logger.info(report)
    
    # Отправляем ежедневный отчет в Telegram
    now = datetime.now()
    if now.hour == 9 and now.minute < 5:  # Отправляем отчет примерно в 9:00 утра
        send_telegram_notification(f"📊 *Ежедневный отчет Mistral API*\n```\n{report}\n```")

def main():
    """Основной цикл мониторинга"""
    logger.info("Запуск сервиса мониторинга Mistral API")
    logger.info(f"Проверка API по адресу: {MISTRAL_API_URL}")
    logger.info(f"Интервал проверки: {CHECK_INTERVAL} секунд")
    
    # Создаем шаблон скрипта перезапуска, если его нет
    if not os.path.exists(RESTART_SCRIPT):
        restart_dir = os.path.dirname(RESTART_SCRIPT)
        # Директория уже должна существовать, так как это директория скриптов
        
        with open(RESTART_SCRIPT, 'w') as f:
            f.write("""#!/bin/bash
# Скрипт для перезапуска Mistral API

# Настройки
SERVER_HOST="139.59.241.176"
SERVER_PORT="8080"
SERVER_USER="root"
SSH_KEY="${HOME}/.ssh/id_rsa"
RESTART_COMMAND="sudo systemctl restart mistral-api || ( pkill -f 'llama-server' && cd /opt/mistral && ./run_mistral_server.sh )"
CHECK_COMMAND="curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/v1/models"

echo "Проверка локальной доступности Mistral API..."
status_code=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_HOST}:${SERVER_PORT}/v1/models)

if [ "$status_code" = "200" ]; then
  echo "API доступен (код ответа: $status_code). Перезапуск не требуется."
  exit 0
else
  echo "API недоступен или вернул ошибку (код ответа: $status_code)."
  echo "Необходим перезапуск, но в тестовом режиме только имитируем его."
  echo "В реальном сценарии здесь выполнялось бы подключение по SSH и перезапуск сервиса."
  exit 0  # Для тестов всегда возвращаем успех
fi
""")
        os.chmod(RESTART_SCRIPT, 0o755)
        logger.info(f"Создан шаблон скрипта перезапуска: {RESTART_SCRIPT}")
        logger.warning("Этот скрипт - только шаблон. Для реального использования необходимо настроить корректные данные SSH и команды.")
    
    # Загружаем предыдущее состояние
    load_state()
    
    # Отправляем уведомление о запуске мониторинга
    message = (
        f"🚀 *Сервис мониторинга Mistral API запущен*\n"
        f"URL API: `{MISTRAL_API_URL}`\n"
        f"Интервал проверки: {CHECK_INTERVAL} секунд\n"
        f"Макс. рестартов в день: {MAX_RESTARTS_PER_DAY}"
    )
    logger.info(message.replace('*', '').replace('`', ''))
    send_telegram_notification(message)

    last_report_time = datetime.now()
    
    while True:
        try:
            logger.info(f"Проверка доступности API по адресу {MISTRAL_API_URL}")
            status = check_api_health()
            
            # Если API недоступен несколько раз подряд, пробуем перезапустить
            if not status and monitoring_state['consecutive_failures'] >= RETRY_ATTEMPTS:
                restart_mistral_api()
                monitoring_state['consecutive_failures'] = 0  # Сбрасываем счетчик после попытки рестарта
            
            # Сохраняем состояние
            save_state()
            
            # Генерируем отчет каждый час
            now = datetime.now()
            if (now - last_report_time).total_seconds() >= 3600:  # 1 час
                generate_report()
                last_report_time = now
            
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения, останавливаем мониторинг")
            break
        except Exception as e:
            logger.error(f"Неожиданная ошибка в основном цикле: {e}")
            time.sleep(CHECK_INTERVAL)  # Ждем перед повторной попыткой

    logger.info("Сервис мониторинга остановлен")

if __name__ == "__main__":
    main() 