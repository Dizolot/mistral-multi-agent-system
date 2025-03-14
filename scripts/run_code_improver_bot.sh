#!/bin/bash

# Скрипт для запуска Telegram-бота с функциональностью улучшения кода в фоновом режиме

# Перейти в корневую директорию проекта
cd "$(dirname "$0")/.."

# Проверить и создать директорию для логов
mkdir -p logs

# Проверить наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "Виртуальное окружение не найдено. Создаю виртуальное окружение..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Остановить существующий процесс бота, если он запущен
echo "Проверяю наличие запущенного бота..."
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
    
    echo "Бот остановлен."
fi

# Запуск бота в фоновом режиме с выводом логов в файл
echo "Запускаю бота улучшения кода в фоновом режиме..."
nohup python run_telegram_bot.py > logs/telegram_bot.log 2>&1 &

# Получение PID запущенного процесса
bot_pid=$!
echo "Бот запущен с PID: $bot_pid"

# Запись PID в файл для возможности остановки в будущем
echo $bot_pid > logs/telegram_bot.pid

echo "Бот успешно запущен. Логи записываются в logs/telegram_bot.log"
echo "Для просмотра логов выполните: tail -f logs/telegram_bot.log"
echo "Для остановки бота выполните: scripts/stop_code_improver_bot.sh" 