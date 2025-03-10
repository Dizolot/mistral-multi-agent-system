#!/bin/bash

# Путь к директории проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "Настройка окружения для Mistral Multi-Agent System Orchestrator..."

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Ошибка при создании виртуального окружения. Убедитесь, что у вас установлен Python 3."
        exit 1
    fi
else
    echo "Виртуальное окружение уже существует."
fi

# Активация виртуального окружения
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Ошибка при активации виртуального окружения."
    exit 1
fi

# Установка зависимостей
echo "Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Ошибка при установке зависимостей."
    exit 1
fi

# Создание директорий
echo "Создание необходимых директорий..."
mkdir -p logs

echo "Настройка завершена успешно!"
echo "Для запуска тестового окружения выполните: ./run_test_environment.sh" 