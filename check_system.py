#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для проверки наличия всех необходимых компонентов системы.
"""

import os
import sys
import importlib
from pathlib import Path

# Настройка путей для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_file_exists(file_path):
    """Проверяет наличие файла и выводит информацию о нем."""
    path = Path(file_path)
    if path.exists():
        print(f"✅ Файл {file_path} существует ({path.stat().st_size} байт)")
        return True
    else:
        print(f"❌ Файл {file_path} не найден")
        return False

def check_module_imports(module_name):
    """Проверяет возможность импорта модуля."""
    try:
        module = importlib.import_module(module_name)
        print(f"✅ Модуль {module_name} успешно импортирован")
        return module
    except ImportError as e:
        print(f"❌ Ошибка импорта модуля {module_name}: {e}")
        return None

def main():
    """Основная функция проверки системы."""
    print("=== Проверка файловой структуры ===")
    
    # Проверка основных файлов
    check_file_exists("multi_agent_system/agents/base_agent.py")
    check_file_exists("multi_agent_system/agents/code_analyzer_agent.py")
    check_file_exists("multi_agent_system/agents/code_improver_agent.py")
    check_file_exists("multi_agent_system/agents/testing_agent.py")
    check_file_exists("multi_agent_system/agents/evaluation_agent.py")
    check_file_exists("multi_agent_system/agents/agent_configs.py")
    check_file_exists("multi_agent_system/agents/__init__.py")
    
    check_file_exists("multi_agent_system/orchestrator/agent_orchestrator.py")
    check_file_exists("multi_agent_system/memory/conversation_memory.py")
    check_file_exists("multi_agent_system/logger.py")
    check_file_exists("multi_agent_system/async_utils.py")
    
    check_file_exists("src/model_service/service/model_service.py")
    check_file_exists("src/model_service/service/session_manager.py")
    check_file_exists("src/model_service/service/request_queue.py")
    
    print("\n=== Проверка импорта модулей ===")
    
    # Проверка импорта основных модулей
    base_agent = check_module_imports("multi_agent_system.agents.base_agent")
    if base_agent:
        print(f"  - Классы в base_agent: {', '.join([name for name in dir(base_agent) if not name.startswith('_') and name[0].isupper()])}")
    
    agent_orchestrator = check_module_imports("multi_agent_system.orchestrator.agent_orchestrator")
    if agent_orchestrator:
        print(f"  - Классы в agent_orchestrator: {', '.join([name for name in dir(agent_orchestrator) if not name.startswith('_') and name[0].isupper()])}")
    
    model_service = check_module_imports("src.model_service.service.model_service")
    if model_service:
        print(f"  - Классы в model_service: {', '.join([name for name in dir(model_service) if not name.startswith('_') and name[0].isupper()])}")
    
    print("\n=== Проверка зависимостей ===")
    
    # Проверка наличия необходимых пакетов
    try:
        import pytest
        print(f"✅ pytest установлен (версия {pytest.__version__})")
    except ImportError:
        print("❌ pytest не установлен")
    
    try:
        import mistralai
        print(f"✅ mistralai установлен")
    except ImportError:
        print("❌ mistralai не установлен")
    
    print("\n=== Проверка завершена ===")

if __name__ == "__main__":
    main() 