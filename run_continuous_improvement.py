#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для запуска непрерывного цикла улучшения кода.

Этот скрипт инициализирует и запускает цикл, который:
1. Анализирует код с помощью CodeAnalyzerAgent
2. Улучшает код с помощью CodeImproverAgent
3. Тестирует улучшенный код с помощью TestingAgent
4. Оценивает качество улучшений с помощью EvaluationAgent
5. Применяет успешные изменения
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from typing import List, Optional

# Настройка путей для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("continuous_improvement")

# Импорт компонентов системы
from multi_agent_system.orchestrator.agent_orchestrator import (
    AgentOrchestrator,
    AgentTask,
    TaskStatus,
    TaskPriority,
    AgentType,
    AgentStatus
)
from multi_agent_system.agents.code_analyzer_agent import CodeAnalyzerAgent
from multi_agent_system.agents.code_improver_agent import CodeImproverAgent
from multi_agent_system.agents.testing_agent import TestingAgent
from multi_agent_system.agents.evaluation_agent import EvaluationAgent
from src.model_service.service.model_service import ModelService
from src.model_service.service.session_manager import SessionManager
from src.model_service.service.request_queue import RequestQueue
from src.core.memory_system.memory_manager import MemoryManager as ConversationMemoryManager

async def setup_orchestrator() -> AgentOrchestrator:
    """
    Настраивает оркестратор агентов и регистрирует необходимые агенты.
    
    Returns:
        Настроенный оркестратор агентов
    """
    logger.info("Настройка базовых сервисов...")
    
    # Инициализация базовых сервисов
    memory_manager = ConversationMemoryManager()
    
    # Создание сервиса моделей
    model_service = ModelService(
        default_model="mistral",
        session_ttl=3600,
        max_sessions=1000,
        max_workers=5,
        max_queue_size=100
    )
    
    # Создание оркестратора агентов
    orchestrator = AgentOrchestrator(model_service=model_service, memory_manager=memory_manager)
    
    # Регистрация агентов
    code_analyzer = CodeAnalyzerAgent(
        agent_id="code_analyzer_1",
        model_service=model_service,
        memory_manager=memory_manager,
        config={
            "max_files_per_analysis": 10,
            "severity_threshold": 3
        }
    )
    await orchestrator.register_agent(code_analyzer)
    
    code_improver = CodeImproverAgent(
        agent_id="code_improver_1",
        model_service=model_service,
        memory_manager=memory_manager,
        config={
            "improvement_strategy": "maintainability",
            "max_attempts": 3
        }
    )
    await orchestrator.register_agent(code_improver)
    
    testing_agent = TestingAgent(
        agent_id="testing_agent_1",
        model_service=model_service,
        memory_manager=memory_manager,
        config={
            "test_timeout": 60,
            "max_retries": 3
        }
    )
    await orchestrator.register_agent(testing_agent)
    
    evaluation_agent = EvaluationAgent(
        agent_id="evaluation_agent_1",
        model_service=model_service,
        memory_manager=memory_manager,
        config={
            "quality_threshold": 0.7,
            "max_evaluation_time": 120
        }
    )
    await orchestrator.register_agent(evaluation_agent)
    
    logger.info(f"Зарегистрировано {len(orchestrator.agents)} агентов")
    return orchestrator

async def main():
    """Основная функция запуска цикла улучшения кода"""
    parser = argparse.ArgumentParser(description="Запуск непрерывного цикла улучшения кода")
    parser.add_argument("--target-dir", type=str, default=".", help="Директория с кодом для улучшения")
    parser.add_argument("--interval", type=int, default=3600, help="Интервал между циклами в секундах (по умолчанию 1 час)")
    parser.add_argument("--max-cycles", type=int, default=None, help="Максимальное количество циклов (по умолчанию бесконечно)")
    parser.add_argument("--extensions", type=str, default=".py", help="Расширения файлов для анализа (через запятую)")
    parser.add_argument("--exclude", type=str, default="venv,__pycache__,.git,logs", help="Исключенные директории (через запятую)")
    
    args = parser.parse_args()
    
    # Преобразуем параметры
    target_dir = args.target_dir
    interval = args.interval
    max_cycles = args.max_cycles
    extensions = [ext.strip() for ext in args.extensions.split(",")]
    excluded_dirs = [dir.strip() for dir in args.exclude.split(",")]
    
    logger.info(f"Запуск непрерывного цикла улучшения кода")
    logger.info(f"Целевая директория: {target_dir}")
    logger.info(f"Интервал между циклами: {interval} сек")
    logger.info(f"Максимальное количество циклов: {max_cycles if max_cycles else 'бесконечно'}")
    logger.info(f"Расширения файлов: {extensions}")
    logger.info(f"Исключенные директории: {excluded_dirs}")
    
    # Настройка и запуск оркестратора
    orchestrator = await setup_orchestrator()
    await orchestrator.start()
    
    try:
        # Запуск непрерывного цикла улучшения
        await orchestrator.run_continuous_improvement_cycle(
            target_directory=target_dir,
            cycle_interval=interval,
            max_cycles=max_cycles,
            file_extensions=extensions,
            excluded_dirs=excluded_dirs
        )
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем работу")
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
    finally:
        # Останавливаем оркестратор
        await orchestrator.stop()
        logger.info("Работа завершена")

if __name__ == "__main__":
    try:
        # Запускаем асинхронную функцию main
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}") 