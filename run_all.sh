#!/bin/bash

# Скрипт для запуска всех компонентов системы

# Функция для проверки, запущен ли процесс
check_process() {
    local process_name=$1
    if pgrep -f "$process_name" > /dev/null; then
        echo "✅ $process_name уже запущен"
        return 0
    else
        echo "❌ $process_name не запущен"
        return 1
    fi
}

# Функция для запуска процесса в фоновом режиме
start_process() {
    local command=$1
    local log_file=$2
    local process_name=$3
    
    echo "🚀 Запуск $process_name..."
    if [ -n "$log_file" ]; then
        $command > "$log_file" 2>&1 &
    else
        $command &
    fi
    
    # Проверяем, запустился ли процесс
    sleep 2
    if check_process "$process_name"; then
        echo "✅ $process_name успешно запущен"
    else
        echo "❌ Не удалось запустить $process_name"
    fi
}

# Создаем директорию для логов, если она не существует
mkdir -p logs

# Проверяем, запущен ли API-сервер оркестратора
if ! check_process "run_api_server.py"; then
    # Запускаем API-сервер оркестратора
    start_process "python run_api_server.py" "logs/api_server.log" "run_api_server.py"
fi

# Проверяем, запущен ли Telegram-бот
if ! check_process "run_telegram_bot.py"; then
    # Запускаем Telegram-бот
    start_process "python run_telegram_bot.py" "logs/telegram_bot.log" "run_telegram_bot.py"
fi

echo ""
echo "📊 Статус компонентов:"
echo "-------------------"
check_process "run_api_server.py"
check_process "run_telegram_bot.py"
echo ""
echo "✨ Для остановки всех компонентов выполните: bash stop_all.sh"
echo "" 