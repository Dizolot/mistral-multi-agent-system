#!/bin/bash

# Скрипт для запуска тестов модуля ImprovementTracker

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Запускаю тесты модуля ImprovementTracker...${NC}"

# Переходим в корневую директорию проекта
cd "$(dirname "$0")/.." || exit 1

# Создаем директорию для результатов тестов, если её нет
mkdir -p results

# Запускаем тесты
python -m tests.test_improvement_tracker

# Проверяем результат выполнения
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Тесты успешно пройдены!${NC}"
    exit 0
else
    echo -e "${RED}Тесты завершились с ошибкой.${NC}"
    exit 1
fi 