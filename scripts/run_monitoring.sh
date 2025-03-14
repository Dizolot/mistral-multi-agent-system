#!/bin/bash

# Запуск сервиса мониторинга Mistral API в фоновом режиме

# Перейти в корневую директорию проекта
cd "$(dirname "$0")/.."

# Создать директорию для логов, если она не существует
mkdir -p logs

# Настройка переменных окружения
export LOG_DIR="$(pwd)/logs"
export MISTRAL_API_URL="http://139.59.241.176:8080"
export CHECK_INTERVAL="60"
export RETRY_ATTEMPTS="3"
export RESTART_COOLDOWN="300" 
export MAX_RESTARTS_PER_DAY="5"

# Опционально: настройка уведомлений Telegram
# export TELEGRAM_BOT_TOKEN="ваш_токен"
# export TELEGRAM_CHAT_ID="ваш_чат_id"

# Запуск скрипта мониторинга
python scripts/monitoring_service.py > logs/monitoring_stdout.log 2>&1 &

# Сохранение PID для возможности остановки сервиса
echo $! > logs/monitoring.pid

echo "Сервис мониторинга запущен с PID: $(cat logs/monitoring.pid)"
echo "Логи доступны в директории: $(pwd)/logs" 