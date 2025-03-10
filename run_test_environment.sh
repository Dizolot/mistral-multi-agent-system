#!/bin/bash

# Путь к директории проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Создаем директорию для логов, если она не существует
mkdir -p logs

# Проверяем, установлены ли зависимости
if ! command -v uvicorn &> /dev/null; then
    echo "Устанавливаем необходимые зависимости..."
    pip install fastapi uvicorn loguru pydantic psutil
fi

# Функция для остановки всех сервисов
stop_all_services() {
    echo "Останавливаем все сервисы..."
    
    # Находим PID процессов и останавливаем их
    for service in "api_server" "mistral_api_mock"; do
        pid=$(ps -ef | grep python | grep $service | grep -v grep | awk '{print $2}')
        if [ ! -z "$pid" ]; then
            echo "Останавливаем $service (PID: $pid)..."
            kill $pid
        fi
    done
    
    echo "Все сервисы остановлены."
    exit 0
}

# Обработка сигналов для корректного завершения
trap stop_all_services SIGINT SIGTERM

# Проверяем, запущены ли уже сервисы
echo "Проверяем, запущены ли сервисы..."
for service in "api_server" "mistral_api_mock"; do
    pid=$(ps -ef | grep python | grep $service | grep -v grep | awk '{print $2}')
    if [ ! -z "$pid" ]; then
        echo "$service уже запущен (PID: $pid), останавливаем..."
        kill $pid
        sleep 2
    fi
done

# Запускаем API-сервер оркестратора в фоновом режиме
echo "Запуск API-сервера оркестратора..."
python3 "$PROJECT_DIR/run_api_server.py" > logs/orchestrator_api.log 2>&1 &
API_SERVER_PID=$!
echo "API-сервер оркестратора запущен с PID: $API_SERVER_PID"

# Ждем немного, чтобы сервер успел запуститься
sleep 2

# Проверяем, что API-сервер запустился успешно
if ! ps -p $API_SERVER_PID > /dev/null; then
    echo "Ошибка при запуске API-сервера оркестратора. Проверьте логи в logs/orchestrator_api.log"
    exit 1
fi

# Запускаем мок-сервер Mistral API в фоновом режиме
echo "Запуск мок-сервера Mistral API..."
python3 "$PROJECT_DIR/run_mistral_mock.py" > logs/mistral_api_mock.log 2>&1 &
MISTRAL_MOCK_PID=$!
echo "Мок-сервер Mistral API запущен с PID: $MISTRAL_MOCK_PID"

# Ждем немного, чтобы сервер успел запуститься
sleep 2

# Проверяем, что мок-сервер запустился успешно
if ! ps -p $MISTRAL_MOCK_PID > /dev/null; then
    echo "Ошибка при запуске мок-сервера Mistral API. Проверьте логи в logs/mistral_api_mock.log"
    stop_all_services
    exit 1
fi

# Проверяем доступность сервисов
echo "Проверяем доступность API-сервера оркестратора..."
if curl -s --head "http://localhost:8000/health" | grep "200 OK" > /dev/null; then
    echo "✅ API-сервер оркестратора доступен по адресу http://localhost:8000"
else
    echo "❌ API-сервер оркестратора недоступен. Проверьте логи в logs/orchestrator_api.log"
    stop_all_services
    exit 1
fi

echo "Проверяем доступность мок-сервера Mistral API..."
if curl -s --head "http://localhost:8001/health" | grep "200 OK" > /dev/null; then
    echo "✅ Мок-сервер Mistral API доступен по адресу http://localhost:8001"
else
    echo "❌ Мок-сервер Mistral API недоступен. Проверьте логи в logs/mistral_api_mock.log"
    stop_all_services
    exit 1
fi

echo "Все сервисы успешно запущены и доступны."
echo ""
echo "Теперь вы можете запустить бота с интеграцией оркестратора:"
echo "cd /Users/dimitrizolot/Desktop/Co-Founder/mistral_multiagent_bot && ./run_bot.sh"
echo ""
echo "Для остановки всех сервисов нажмите Ctrl+C"

# Ждем, пока пользователь не нажмет Ctrl+C
while true; do
    sleep 1
done 