#!/bin/bash

# Остановка сервиса мониторинга Mistral API

# Перейти в корневую директорию проекта
cd "$(dirname "$0")/.."

# Проверить, существует ли файл с PID
if [ ! -f logs/monitoring.pid ]; then
    echo "Файл с PID не найден. Возможно, сервис мониторинга не запущен."
    exit 1
fi

# Получить PID сервиса мониторинга
PID=$(cat logs/monitoring.pid)

# Проверить, существует ли процесс с указанным PID
if ! kill -0 $PID 2>/dev/null; then
    echo "Процесс с PID $PID не найден. Возможно, сервис мониторинга уже остановлен."
    rm -f logs/monitoring.pid
    exit 1
fi

# Остановить процесс
echo "Останавливаем сервис мониторинга с PID $PID..."
kill $PID

# Подождать завершения процесса
for i in {1..10}; do
    if ! kill -0 $PID 2>/dev/null; then
        echo "Сервис мониторинга успешно остановлен."
        rm -f logs/monitoring.pid
        exit 0
    fi
    echo "Ожидание завершения процесса... ($i/10)"
    sleep 1
done

# Если процесс не завершился, принудительно завершить
echo "Процесс не завершился. Принудительное завершение..."
kill -9 $PID
rm -f logs/monitoring.pid
echo "Сервис мониторинга принудительно остановлен." 