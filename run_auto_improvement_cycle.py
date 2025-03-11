#!/usr/bin/env python3
"""
Скрипт для запуска автоматического цикла улучшения агентов.

Этот скрипт запускает полный цикл автоматического улучшения агентов, который:
1. Собирает данные из истории диалогов с пользователями
2. Анализирует эффективность агентов
3. Генерирует улучшения для агентов
4. Тестирует улучшения
5. Внедряет успешные улучшения

Скрипт может быть запущен как вручную, так и по расписанию через cron.
"""

import os
import sys
import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию проекта в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Импортируем необходимые модули
from multi_agent_system.memory.conversation_memory import ConversationMemoryManager
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector
from multi_agent_system.agent_analytics.performance_analyzer import PerformanceAnalyzer
from multi_agent_system.agent_analytics.metrics_evaluator import MetricsEvaluator
from multi_agent_system.agent_developer.agent_optimizer import AgentOptimizer
from multi_agent_system.agent_developer.agent_tester import AgentTester
from multi_agent_system.agent_developer.version_manager import VersionManager
from multi_agent_system.memory.memory_analytics_integration import MemoryAnalyticsIntegration
from multi_agent_system.agent_developer.testing_memory_integration import TestingMemoryIntegration, create_auto_improvement_cycle
from multi_agent_system.logger import get_logger

# Настройка логирования
logger = get_logger(__name__)

# Создаем директорию для результатов, если она не существует
os.makedirs("agent_developer/improvement_results", exist_ok=True)

def run_improvement_cycle(
    process_all_users: bool = False,
    min_interactions: int = 10,
    deploy_improvements: bool = False,
    save_results: bool = True
):
    """
    Запускает цикл автоматического улучшения агентов.
    
    Args:
        process_all_users: Обрабатывать историю диалогов всех пользователей
        min_interactions: Минимальное количество взаимодействий для анализа
        deploy_improvements: Внедрять улучшения, если они успешны
        save_results: Сохранять результаты в файл
        
    Returns:
        Dict: Результаты выполнения цикла улучшения
    """
    logger.info("Запуск цикла автоматического улучшения агентов...")
    
    # Инициализируем все необходимые компоненты
    memory_manager = ConversationMemoryManager()
    data_collector = AgentDataCollector()
    performance_analyzer = PerformanceAnalyzer(data_collector=data_collector)
    metrics_evaluator = MetricsEvaluator()
    agent_optimizer = AgentOptimizer(
        data_collector=data_collector,
        performance_analyzer=performance_analyzer,
        metrics_evaluator=metrics_evaluator
    )
    agent_tester = AgentTester(
        data_collector=data_collector,
        performance_analyzer=performance_analyzer,
        metrics_evaluator=metrics_evaluator
    )
    version_manager = VersionManager(agent_tester=agent_tester)
    
    # Интеграция памяти и аналитики
    memory_analytics = MemoryAnalyticsIntegration(
        memory_manager=memory_manager,
        data_collector=data_collector
    )
    
    # Если нужно обработать всех пользователей, делаем это
    if process_all_users:
        logger.info("Обработка историй диалогов всех пользователей...")
        users_processed = memory_analytics.process_all_users()
        logger.info(f"Обработано {sum(users_processed.values())} взаимодействий для {len(users_processed)} пользователей")
    
    # Запускаем цикл автоматического улучшения
    cycle_results = create_auto_improvement_cycle(
        memory_manager=memory_manager,
        agent_tester=agent_tester,
        agent_optimizer=agent_optimizer,
        version_manager=version_manager,
        data_collector=data_collector
    )
    
    # Выводим результаты
    logger.info(f"Цикл улучшения завершен. Обработано агентов: {cycle_results['agents_processed']}")
    logger.info(f"Улучшено агентов: {cycle_results['agents_improved']}")
    logger.info(f"Внедрено улучшений: {cycle_results['agents_deployed']}")
    
    # Сохраняем результаты в файл, если нужно
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"agent_developer/improvement_results/cycle_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(cycle_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты сохранены в файл: {results_file}")
    
    return cycle_results

def main():
    """
    Основная функция скрипта.
    """
    parser = argparse.ArgumentParser(description="Запускает цикл автоматического улучшения агентов")
    parser.add_argument("--process-all-users", action="store_true", help="Обрабатывать историю диалогов всех пользователей")
    parser.add_argument("--min-interactions", type=int, default=10, help="Минимальное количество взаимодействий для анализа")
    parser.add_argument("--deploy-improvements", action="store_true", help="Внедрять улучшения, если они успешны")
    parser.add_argument("--no-save-results", action="store_true", help="Не сохранять результаты в файл")
    
    args = parser.parse_args()
    
    try:
        run_improvement_cycle(
            process_all_users=args.process_all_users,
            min_interactions=args.min_interactions,
            deploy_improvements=args.deploy_improvements,
            save_results=not args.no_save_results
        )
    except Exception as e:
        logger.error(f"Ошибка при выполнении цикла улучшения: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 