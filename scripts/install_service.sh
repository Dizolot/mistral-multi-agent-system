#!/bin/bash

# Скрипт для установки systemd-сервиса для Telegram-бота

# Проверка прав суперпользователя
if [ "$EUID" -ne 0 ]; then
    echo "Этот скрипт должен быть запущен с правами суперпользователя (root)."
    echo "Попробуйте: sudo $0"
    exit 1
fi

# Путь к текущей директории
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/mistral-telegram-bot.service"

# Проверка наличия файла сервиса
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Файл сервиса не найден: $SERVICE_FILE"
    exit 1
fi

# Копирование файла сервиса в systemd
echo "Копирование файла сервиса в /etc/systemd/system/..."
cp "$SERVICE_FILE" /etc/systemd/system/

# Перезагрузка конфигурации systemd
echo "Перезагрузка конфигурации systemd..."
systemctl daemon-reload

# Включение сервиса для автозапуска
echo "Включение сервиса для автозапуска..."
systemctl enable mistral-telegram-bot.service

# Запуск сервиса
echo "Запуск сервиса..."
systemctl start mistral-telegram-bot.service

# Проверка статуса
echo "Проверка статуса сервиса..."
systemctl status mistral-telegram-bot.service

echo "Установка сервиса завершена."
echo "Для управления сервисом используйте команды:"
echo "  systemctl start mistral-telegram-bot.service   # Запуск"
echo "  systemctl stop mistral-telegram-bot.service    # Остановка"
echo "  systemctl restart mistral-telegram-bot.service # Перезапуск"
echo "  systemctl status mistral-telegram-bot.service  # Проверка статуса"
echo "  journalctl -u mistral-telegram-bot.service     # Просмотр логов" 