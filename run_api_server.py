#!/usr/bin/env python
"""
Скрипт для запуска API-сервера оркестратора
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Создаем директорию для логов, если она не существует
os.makedirs(os.path.join(project_root, "logs"), exist_ok=True)

# Устанавливаем порт API-сервера
os.environ["API_SERVER_PORT"] = "8002"

# Импортируем и запускаем сервер
from multi_agent_system.api_server import run_server

if __name__ == "__main__":
    print("Запуск API-сервера оркестратора...")
    run_server() 