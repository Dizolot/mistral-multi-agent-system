#!/bin/bash

# Скрипт для запуска Telegram-бота на сервере

# Переходим в директорию проекта
cd "$(dirname "$0")/.."

# Проверяем, запущен ли уже бот
if pgrep -f "python run_telegram_bot.py" > /dev/null; then
    echo "Бот уже запущен. Останавливаем..."
    pkill -f "python run_telegram_bot.py"
    sleep 2
fi

# Создаем директорию для логов, если она не существует
mkdir -p logs

# Запускаем бота в фоновом режиме
echo "Запускаем Telegram-бота..."
nohup python run_telegram_bot.py > logs/telegram_bot_stdout.log 2>&1 &

# Проверяем, запустился ли бот
sleep 2
if pgrep -f "python run_telegram_bot.py" > /dev/null; then
    echo "Бот успешно запущен!"
    echo "PID: $(pgrep -f "python run_telegram_bot.py")"
    echo "Логи доступны в директории logs/"
else
    echo "Ошибка при запуске бота. Проверьте логи в директории logs/"
    exit 1
fi 