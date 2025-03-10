#!/usr/bin/env python
"""
Скрипт для запуска мок-сервера Mistral API
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Создаем директорию для логов, если она не существует
os.makedirs(os.path.join(project_root, "logs"), exist_ok=True)

# Импортируем и запускаем сервер
from multi_agent_system.mistral_api_mock import run_server

if __name__ == "__main__":
    print("Запуск мок-сервера Mistral API...")
    run_server() 