#!/bin/bash

# Скрипт для остановки всех компонентов системы

echo "🛑 Остановка компонентов системы..."

# Функция для остановки процесса по имени
stop_process() {
    local process_name=$1
    local pid=$(pgrep -f "$process_name")
    
    if [ -n "$pid" ]; then
        echo "🛑 Останавливаем $process_name (PID: $pid)..."
        kill $pid
        sleep 1
        
        # Проверяем, остановился ли процесс
        if pgrep -f "$process_name" > /dev/null; then
            echo "⚠️ Процесс $process_name всё ещё запущен, пробуем принудительно остановить..."
            kill -9 $pid
            sleep 1
            
            if pgrep -f "$process_name" > /dev/null; then
                echo "❌ Не удалось остановить $process_name"
            else
                echo "✅ Процесс $process_name остановлен"
            fi
        else
            echo "✅ Процесс $process_name остановлен"
        fi
    else
        echo "ℹ️ Процесс $process_name не запущен"
    fi
}

# Останавливаем все компоненты
stop_process "run_telegram_bot.py"
stop_process "run_api_server.py"

echo ""
echo "📊 Проверка статуса компонентов:"
echo "----------------------------"

# Функция для проверки статуса процесса
check_process() {
    local process_name=$1
    if pgrep -f "$process_name" > /dev/null; then
        echo "⚠️ $process_name всё ещё запущен"
    else
        echo "✅ $process_name остановлен"
    fi
}

# Проверяем статус всех компонентов
check_process "run_telegram_bot.py"
check_process "run_api_server.py"

echo ""
echo "✨ Для запуска всех компонентов выполните: bash run_all.sh"
echo "" 