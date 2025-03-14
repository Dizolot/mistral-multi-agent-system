#!/bin/bash

# Скрипт для остановки службы непрерывного улучшения кода

# Перейти в корневую директорию проекта
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)
LOG_DIR="${PROJECT_ROOT}/logs"

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

# Остановка мониторинга
if [ -f "${LOG_DIR}/monitor.pid" ]; then
    MONITOR_PID=$(cat "${LOG_DIR}/monitor.pid")
    if ps -p ${MONITOR_PID} > /dev/null; then
        echo "Остановка мониторинга (PID: ${MONITOR_PID})..."
        kill -9 ${MONITOR_PID} 2>/dev/null
        echo "Мониторинг остановлен."
    else
        echo "Процесс мониторинга не найден (PID: ${MONITOR_PID})."
    fi
    rm "${LOG_DIR}/monitor.pid" 2>/dev/null
else
    echo "Файл PID мониторинга не найден."
fi

# Остановка службы непрерывного улучшения
if [ -f "${LOG_DIR}/continuous_improvement.pid" ]; then
    PID=$(cat "${LOG_DIR}/continuous_improvement.pid")
    if [ "${PID}" = "starting" ] || [ "${PID}" = "error" ]; then
        echo "Служба в особом состоянии: ${PID}. Очистка PID файла."
        rm "${LOG_DIR}/continuous_improvement.pid"
    elif ps -p ${PID} > /dev/null; then
        echo "Остановка службы непрерывного улучшения (PID: ${PID})..."
        kill -9 ${PID} 2>/dev/null
        sleep 2
        
        # Проверка, что процесс действительно остановлен
        if ! ps -p ${PID} > /dev/null; then
            echo "Служба успешно остановлена."
            send_notification "🛑 *Служба непрерывного улучшения остановлена*\nСлужба успешно остановлена администратором."
        else
            echo "Не удалось остановить службу! Процесс все еще выполняется."
            send_notification "⚠️ *Ошибка остановки службы*\nНе удалось остановить службу непрерывного улучшения (PID: ${PID})."
        fi
    else
        echo "Процесс службы непрерывного улучшения не найден (PID: ${PID})."
    fi
    rm "${LOG_DIR}/continuous_improvement.pid" 2>/dev/null
else
    echo "Файл PID службы непрерывного улучшения не найден."
fi

echo "Операция завершена." 