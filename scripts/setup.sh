#!/bin/bash

# Скрипт для установки и запуска Telegram-бота для Mistral

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 не найден. Установите Python 3.8 или выше."
    exit 1
fi

# Создание виртуального окружения
echo "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Проверка наличия файла .env
if [ ! -f .env ]; then
    echo "Файл .env не найден. Создаем из примера..."
    cp .env.example .env
    echo "Пожалуйста, отредактируйте файл .env и укажите необходимые параметры."
    echo "В частности, добавьте токен Telegram бота (TELEGRAM_TOKEN)."
    exit 1
fi

# Создание директории для логов
mkdir -p logs

# Запуск бота
echo "Запуск бота..."
python main.py 