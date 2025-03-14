#!/bin/bash

# Скрипт для запуска службы непрерывного улучшения кода в фоновом режиме с автоматическим перезапуском

# Перейти в корневую директорию проекта
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# Создать директории для логов
mkdir -p logs
LOG_DIR="${PROJECT_ROOT}/logs"

# Настройка переменных окружения
export MISTRAL_API_URL="http://139.59.241.176:8080"
export LOG_LEVEL="INFO"
export PYTHONPATH="${PROJECT_ROOT}"

# Настройка параметров для служб непрерывного улучшения
INTERVAL=3600  # Интервал между циклами улучшения в секундах (по умолчанию: 1 час)
TARGET_DIR="${PROJECT_ROOT}/multi_agent_system/agents"  # Директория с целевым кодом для улучшения
EXTENSIONS=".py"  # Расширения файлов для анализа
EXCLUDE="__pycache__,venv,logs,.git"  # Исключенные директории
MAX_RESTART_ATTEMPTS=5  # Максимальное количество попыток перезапуска за день
RESTART_COOLDOWN=300  # Задержка между попытками перезапуска (в секундах)

# Функция для сохранения PID и статуса службы
save_service_status() {
    echo "$1" > "${LOG_DIR}/continuous_improvement.pid"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $2" >> "${LOG_DIR}/service_status.log"
}

# Функция для отправки уведомлений (если настроен Telegram)
send_notification() {
    if [ -n "${TELEGRAM_BOT_TOKEN}" ] && [ -n "${TELEGRAM_CHAT_ID}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="$1" \
            -d parse_mode="Markdown" \
            > /dev/null
    fi
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "${LOG_DIR}/notifications.log"
}

# Функция для запуска процесса непрерывного улучшения
start_improvement_process() {
    save_service_status "starting" "Запуск службы непрерывного улучшения кода..."
    
    python run_continuous_improvement.py \
        --target-dir "${TARGET_DIR}" \
        --interval "${INTERVAL}" \
        --extensions "${EXTENSIONS}" \
        --exclude "${EXCLUDE}" \
        > "${LOG_DIR}/continuous_improvement.log" 2>&1 &
    
    PID=$!
    save_service_status "${PID}" "Служба запущена с PID: ${PID}"
    send_notification "✅ *Служба непрерывного улучшения запущена*\nPID: ${PID}\nЦелевая директория: ${TARGET_DIR}"
    
    echo "Служба непрерывного улучшения запущена с PID: ${PID}"
    echo "Логи доступны в: ${LOG_DIR}/continuous_improvement.log"
}

# Функция для проверки статуса процесса
check_process() {
    if [ -f "${LOG_DIR}/continuous_improvement.pid" ]; then
        PID=$(cat "${LOG_DIR}/continuous_improvement.pid")
        if [ "${PID}" = "starting" ]; then
            echo "Служба в процессе запуска"
            return 1
        elif ps -p "${PID}" > /dev/null; then
            echo "Служба работает с PID: ${PID}"
            return 0
        else
            echo "Служба не работает (PID ${PID} не существует)"
            return 1
        fi
    else
        echo "PID файл не найден"
        return 1
    fi
}

# Функция для автоматического перезапуска
restart_service() {
    # Проверяем количество перезапусков за день
    TODAY=$(date '+%Y-%m-%d')
    RESTART_COUNT_FILE="${LOG_DIR}/restart_count_${TODAY}.txt"
    
    # Создаем файл счетчика, если он не существует
    if [ ! -f "${RESTART_COUNT_FILE}" ]; then
        echo "0" > "${RESTART_COUNT_FILE}"
    fi
    
    RESTART_COUNT=$(cat "${RESTART_COUNT_FILE}")
    
    # Проверяем, не превышен ли лимит перезапусков
    if [ "${RESTART_COUNT}" -ge "${MAX_RESTART_ATTEMPTS}" ]; then
        send_notification "⚠️ *Превышен лимит перезапусков*\nДостигнуто максимальное количество перезапусков за день (${MAX_RESTART_ATTEMPTS}). Требуется ручное вмешательство."
        save_service_status "error" "Превышен лимит перезапусков (${MAX_RESTART_ATTEMPTS})"
        return 1
    fi
    
    # Увеличиваем счетчик перезапусков
    RESTART_COUNT=$((RESTART_COUNT + 1))
    echo "${RESTART_COUNT}" > "${RESTART_COUNT_FILE}"
    
    # Останавливаем процесс, если он все еще выполняется
    if [ -f "${LOG_DIR}/continuous_improvement.pid" ]; then
        PID=$(cat "${LOG_DIR}/continuous_improvement.pid")
        if [ "${PID}" != "starting" ] && [ "${PID}" != "error" ]; then
            kill -9 "${PID}" 2>/dev/null || true
        fi
    fi
    
    send_notification "🔄 *Перезапуск службы непрерывного улучшения*\nПопытка перезапуска ${RESTART_COUNT}/${MAX_RESTART_ATTEMPTS}"
    sleep 5  # Даем время для корректного завершения процесса
    
    # Запускаем службу снова
    start_improvement_process
    
    echo "Служба перезапущена. Новая попытка: ${RESTART_COUNT}/${MAX_RESTART_ATTEMPTS}"
    return 0
}

# Функция для мониторинга и автоматического перезапуска
monitor_and_restart() {
    while true; do
        if ! check_process > /dev/null; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Обнаружена остановка службы, выполняется перезапуск..." >> "${LOG_DIR}/service_status.log"
            restart_service
            sleep "${RESTART_COOLDOWN}"  # Задержка между попытками перезапуска
        fi
        sleep 60  # Интервал проверки статуса (в секундах)
    done
}

# Запускаем службу непрерывного улучшения
start_improvement_process

# Запускаем мониторинг в фоновом режиме
monitor_and_restart > "${LOG_DIR}/monitor.log" 2>&1 &
MONITOR_PID=$!
echo "${MONITOR_PID}" > "${LOG_DIR}/monitor.pid"

echo "Служба мониторинга запущена с PID: ${MONITOR_PID}"
echo "Всё готово! Система непрерывного улучшения запущена и находится под мониторингом." 