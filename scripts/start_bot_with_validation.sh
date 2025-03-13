#!/bin/bash

# Скрипт для запуска бота с предварительной валидацией конфигурации

# Определяем директорию проекта
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_DIR"

echo "🔍 Запуск валидации конфигурации системы..."
python -m src.utils.config_validator

# Проверяем код возврата валидатора
if [ $? -ne 0 ]; then
    echo "❌ Валидация конфигурации не пройдена. Исправьте проблемы перед запуском бота."
    echo "📖 Подробности смотрите в логе: logs/config_validator.log"
    exit 1
fi

echo "✅ Валидация конфигурации пройдена успешно."
echo "🚀 Запуск Telegram-бота..."

# Останавливаем предыдущие экземпляры бота
pkill -f "python run_telegram_bot.py" || true
sleep 2

# Запускаем бота в фоновом режиме
python run_telegram_bot.py > logs/telegram_bot.log 2>&1 &

echo "🤖 Telegram-бот запущен! Логи записываются в logs/telegram_bot.log"
echo "📊 Для мониторинга используйте: tail -f logs/telegram_bot.log" 