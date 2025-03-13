#!/usr/bin/env python
"""
Скрипт для запуска API-сервера оркестратора
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Создаем директорию для логов, если она не существует
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(logs_dir, "orchestrator_api.log"))
    ]
)

logger = logging.getLogger(__name__)

# Устанавливаем порт API-сервера из переменных окружения или используем значение по умолчанию
api_server_port = int(os.environ.get("API_SERVER_PORT", "8002"))
api_server_host = os.environ.get("API_SERVER_HOST", "0.0.0.0")

# Импортируем и запускаем сервер
try:
    from multi_agent_system.api_server import run_server
    
    if __name__ == "__main__":
        logger.info(f"Запуск API-сервера оркестратора на {api_server_host}:{api_server_port}...")
        run_server(host=api_server_host, port=api_server_port)
except ImportError as e:
    logger.error(f"Ошибка импорта модуля: {e}")
    logger.error("Убедитесь, что все необходимые модули установлены и структура проекта корректна.")
    sys.exit(1)
except Exception as e:
    logger.exception(f"Ошибка при запуске API-сервера: {e}")
    sys.exit(1) 