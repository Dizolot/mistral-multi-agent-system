#!/bin/bash

# Скрипт для остановки Telegram-бота с функциональностью улучшения кода

# Перейти в корневую директорию проекта
cd "$(dirname "$0")/.."

# Проверить наличие файла с PID
if [ -f "logs/telegram_bot.pid" ]; then
    bot_pid=$(cat logs/telegram_bot.pid)
    
    # Проверить, существует ли процесс с таким PID
    if ps -p $bot_pid > /dev/null; then
        echo "Останавливаю бота с PID: $bot_pid..."
        kill $bot_pid
        sleep 2
        
        # Проверяем, остановился ли процесс
        if ps -p $bot_pid > /dev/null; then
            echo "Процесс не остановился. Принудительно завершаю..."
            kill -9 $bot_pid
        fi
        
        echo "Бот успешно остановлен."
    else
        echo "Процесс с PID $bot_pid не найден. Возможно, бот уже остановлен."
    fi
    
    # Удаляем файл с PID
    rm logs/telegram_bot.pid
else
    # Если файл с PID не найден, ищем процесс по имени
    bot_pid=$(pgrep -f "python.*run_telegram_bot.py")
    
    if [ ! -z "$bot_pid" ]; then
        echo "Найден запущенный процесс бота (PID: $bot_pid). Останавливаю его..."
        kill $bot_pid
        sleep 2
        
        # Проверяем, остановился ли процесс
        if ps -p $bot_pid > /dev/null; then
            echo "Процесс не остановился. Принудительно завершаю..."
            kill -9 $bot_pid
        fi
        
        echo "Бот успешно остановлен."
    else
        echo "Запущенный бот не найден."
    fi
fi

echo "Операция завершена." 