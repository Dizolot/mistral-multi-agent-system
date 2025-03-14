#!/bin/bash
# Скрипт для запуска сервиса мониторинга Mistral API в фоновом режиме

# Определяем директории и переменные окружения
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
MONITORING_LOG="$LOG_DIR/monitoring_service.log"
VIRTUAL_ENV="$PROJECT_ROOT/venv"

# Создаем директорию для логов, если она не существует
mkdir -p "$LOG_DIR"

# Функция для проверки, запущен ли уже мониторинг
is_monitoring_running() {
    pgrep -f "python.*monitoring_service.py" >/dev/null
    return $?
}

# Функция для запуска мониторинга
start_monitoring() {
    echo "Запуск сервиса мониторинга Mistral API..."
    
    # Если виртуальное окружение существует, активируем его
    if [ -d "$VIRTUAL_ENV" ]; then
        source "$VIRTUAL_ENV/bin/activate"
        echo "Активировано виртуальное окружение: $VIRTUAL_ENV"
    else
        echo "Виртуальное окружение не найдено, используем системный Python"
    fi
    
    # Определяем переменные окружения для мониторинга
    export MISTRAL_API_URL=${MISTRAL_API_URL:-"http://139.59.241.176:8080"}
    export CHECK_INTERVAL=${CHECK_INTERVAL:-60}
    export RETRY_ATTEMPTS=${RETRY_ATTEMPTS:-3}
    export RESTART_SCRIPT=${RESTART_SCRIPT:-"$SCRIPT_DIR/restart_mistral_api.sh"}
    export RESTART_COOLDOWN=${RESTART_COOLDOWN:-300}
    export MAX_RESTARTS_PER_DAY=${MAX_RESTARTS_PER_DAY:-5}
    export LOG_DIR=${LOG_DIR}
    
    # Если указаны переменные для Telegram, используем их
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        echo "Настроены уведомления через Telegram"
    else
        echo "Уведомления через Telegram не настроены (опционально)"
    fi
    
    # Запускаем мониторинг в фоновом режиме
    echo "Директория запуска: $(pwd)"
    echo "Скрипт: $SCRIPT_DIR/monitoring_service.py"
    echo "Логи: $MONITORING_LOG"
    
    nohup python "$SCRIPT_DIR/monitoring_service.py" > "$MONITORING_LOG" 2>&1 &
    
    # Сохраняем PID процесса
    MONITORING_PID=$!
    echo "$MONITORING_PID" > "$LOG_DIR/monitoring_service.pid"
    
    echo "Сервис мониторинга запущен с PID: $MONITORING_PID"
}

# Проверяем, запущен ли уже мониторинг
if is_monitoring_running; then
    echo "Сервис мониторинга уже запущен:"
    ps aux | grep "python.*monitoring_service.py" | grep -v grep
    exit 0
else
    # Запускаем мониторинг
    start_monitoring
fi

# Проверяем, что мониторинг успешно запустился
sleep 2
if is_monitoring_running; then
    echo "Сервис мониторинга успешно запущен!"
    echo "Для просмотра логов выполните: tail -f $MONITORING_LOG"
    echo "Для остановки сервиса выполните: $SCRIPT_DIR/stop_monitoring_service.sh"
else
    echo "Ошибка: сервис мониторинга не запустился!"
    echo "Проверьте логи: $MONITORING_LOG"
    tail -n 20 "$MONITORING_LOG"
    exit 1
fi

exit 0 