#!/bin/bash

# Скрипт для остановки Telegram-бота на сервере

# Проверяем, запущен ли бот
if pgrep -f "python run_telegram_bot.py" > /dev/null; then
    echo "Останавливаем Telegram-бота..."
    pkill -f "python run_telegram_bot.py"
    
    # Проверяем, остановился ли бот
    sleep 2
    if pgrep -f "python run_telegram_bot.py" > /dev/null; then
        echo "Бот не остановился. Принудительно завершаем процесс..."
        pkill -9 -f "python run_telegram_bot.py"
        sleep 1
    fi
    
    if pgrep -f "python run_telegram_bot.py" > /dev/null; then
        echo "Не удалось остановить бота!"
        exit 1
    else
        echo "Бот успешно остановлен!"
    fi
else
    echo "Бот не запущен."
fi 