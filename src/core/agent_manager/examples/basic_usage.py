#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Базовый пример использования менеджера агентов.

Этот скрипт демонстрирует основные возможности менеджера агентов:
1. Создание экземпляра менеджера
2. Регистрация агентов
3. Обработка запросов с автоматическим выбором режима
"""

import logging
import sys
from typing import Dict, Any

sys.path.append("../../../..")  # Добавляем корневую директорию проекта в путь импорта

from src.core.agent_manager.agent_manager import AgentManager
from src.core.agent_manager.general_agent import GeneralAgent


def setup_logging():
    """Настройка логирования для примера."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()]
    )


def process_query_and_print_result(agent_manager: AgentManager, query: str) -> None:
    """
    Обработка запроса и вывод результата.
    
    Args:
        agent_manager: Менеджер агентов
        query: Запрос для обработки
    """
    print(f"\n>>> Запрос: {query}")
    
    # Обрабатываем запрос
    result = agent_manager.process_query(query)
    
    # Выводим результат
    if result.get("success", False):
        print(f"Режим работы: {result.get('operation_mode')}")
        print(f"Уровень сложности: {result.get('complexity_level')}")
        print(f"Используемый агент: {result.get('agent_id')}")
        print(f"Ответ: {result.get('result', {}).get('response')}")
    else:
        print(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")
    
    print("-" * 50)


def main():
    """Основная функция примера."""
    # Настраиваем логирование
    setup_logging()
    
    # Создаем менеджер агентов
    agent_manager = AgentManager()
    
    # Создаем и регистрируем агентов
    general_agent = GeneralAgent()
    agent_manager.register_agent(general_agent)
    
    # Обрабатываем различные типы запросов
    
    # Простой запрос (низкая сложность)
    process_query_and_print_result(
        agent_manager, 
        "Привет, как дела?"
    )
    
    # Запрос средней сложности
    process_query_and_print_result(
        agent_manager, 
        "Расскажи мне о концепции машинного обучения и его основных методах."
    )
    
    # Сложный запрос (высокая сложность)
    process_query_and_print_result(
        agent_manager, 
        "Сравни различные архитектуры нейронных сетей для обработки естественного "
        "языка, объясни их преимущества и недостатки, и приведи примеры практического "
        "применения каждой из них в современных системах."
    )


if __name__ == "__main__":
    main() 