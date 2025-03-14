#!/bin/bash
# Скрипт для остановки сервиса мониторинга Mistral API

# Определяем директории
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/monitoring_service.pid"

# Функция для остановки процесса мониторинга
stop_monitoring() {
    local pid=$1
    echo "Остановка сервиса мониторинга (PID: $pid)..."
    
    # Пробуем мягко остановить процесс
    if kill -15 "$pid" 2>/dev/null; then
        echo "Отправлен сигнал завершения процессу $pid"
        
        # Ждем завершения процесса
        local timeout=10
        local counter=0
        while kill -0 "$pid" 2>/dev/null && [ $counter -lt $timeout ]; do
            sleep 1
            counter=$((counter + 1))
        done
        
        # Если процесс все еще работает, принудительно завершаем
        if kill -0 "$pid" 2>/dev/null; then
            echo "Процесс не завершился мягко, принудительно останавливаем..."
            kill -9 "$pid" 2>/dev/null
        fi
        
        echo "Сервис мониторинга остановлен."
    else
        echo "Процесс $pid не найден или не может быть остановлен."
    fi
    
    # Удаляем файл с PID
    if [ -f "$PID_FILE" ]; then
        rm "$PID_FILE"
    fi
}

# Проверяем, существует ли файл с PID
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" >/dev/null; then
        stop_monitoring "$PID"
    else
        echo "Процесс с PID $PID не найден, но файл PID существует."
        echo "Удаляем устаревший файл PID..."
        rm "$PID_FILE"
    fi
else
    # Если файла с PID нет, ищем процесс по имени
    echo "Файл PID не найден, поиск процессов мониторинга..."
    PIDS=$(pgrep -f "python.*monitoring_service.py")
    
    if [ -n "$PIDS" ]; then
        for pid in $PIDS; do
            stop_monitoring "$pid"
        done
    else
        echo "Сервис мониторинга не запущен."
    fi
fi

# Финальная проверка
if pgrep -f "python.*monitoring_service.py" >/dev/null; then
    echo "ВНИМАНИЕ: Некоторые процессы мониторинга все еще запущены:"
    ps aux | grep "python.*monitoring_service.py" | grep -v grep
    exit 1
else
    echo "Все процессы мониторинга успешно остановлены."
    exit 0
fi 