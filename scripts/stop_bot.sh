#!/bin/bash

# Скрипт для остановки Telegram-бота

# Проверка наличия файла с PID
if [ ! -f "bot.pid" ]; then
    echo "Файл bot.pid не найден. Бот, возможно, не запущен."
    exit 1
fi

# Получение PID процесса
PID=$(cat bot.pid)

# Проверка, запущен ли процесс
if ! ps -p $PID > /dev/null; then
    echo "Процесс с PID $PID не найден. Бот, возможно, уже остановлен."
    rm bot.pid
    exit 0
fi

# Остановка процесса
echo "Остановка бота с PID: $PID..."
kill $PID

# Проверка успешности остановки
sleep 2
if ! ps -p $PID > /dev/null; then
    echo "Бот успешно остановлен."
    rm bot.pid
else
    echo "Не удалось остановить бот. Попробуйте принудительно: kill -9 $PID"
fi 