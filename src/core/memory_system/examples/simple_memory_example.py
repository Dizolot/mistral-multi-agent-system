#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простой пример использования системы памяти.

Демонстрирует основные возможности системы памяти, включая:
1. Создание менеджера памяти
2. Добавление сообщений пользователя и ассистента
3. Получение истории чата и контекста
4. Сохранение и загрузка состояния памяти
"""

import os
import logging
import json
from typing import Dict, List, Any

from src.core.memory_system import (
    MemoryManager,
    create_simple_summarizer,
    create_keyword_summarizer
)
from src.core.memory_system.embedding_provider import LocalMistralEmbeddingProvider


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция примера."""
    # Создаем директорию для хранения данных памяти
    os.makedirs("data/memory_example", exist_ok=True)
    
    # Создаем провайдер эмбеддингов
    embedding_provider = LocalMistralEmbeddingProvider(
        server_url="http://139.59.241.176:8000"
    )
    
    # Создаем менеджер памяти с простым суммаризатором
    memory_manager = MemoryManager(
        storage_dir="data/memory_example",
        default_buffer_size=10,
        default_summarize_threshold=5,
        summarizer=create_simple_summarizer(),
        embedding_provider=embedding_provider
    )
    
    # Добавляем сообщения пользователя и ассистента
    user_id = "user123"
    
    memory_manager.add_system_message(
        user_id,
        "Начало диалога. Пользователь интересуется мульти-агентными системами."
    )
    
    memory_manager.add_user_message(
        user_id,
        "Привет! Я хочу узнать больше о мульти-агентных системах."
    )
    
    memory_manager.add_assistant_message(
        user_id,
        "Здравствуйте! Мульти-агентные системы - это системы, состоящие из нескольких автономных агентов, которые взаимодействуют друг с другом для решения задач.",
        agent_id="general_agent"
    )
    
    memory_manager.add_user_message(
        user_id,
        "Какие преимущества у таких систем?"
    )
    
    memory_manager.add_assistant_message(
        user_id,
        "Преимущества мульти-агентных систем включают:\n1. Распределение сложных задач между специализированными агентами\n2. Повышение надежности за счет отсутствия единой точки отказа\n3. Масштабируемость и гибкость\n4. Возможность параллельной обработки задач",
        agent_id="expert_agent"
    )
    
    memory_manager.add_user_message(
        user_id,
        "А какие есть примеры таких систем?"
    )
    
    memory_manager.add_assistant_message(
        user_id,
        "Примеры мульти-агентных систем:\n1. Системы управления умным домом, где разные агенты отвечают за разные аспекты (освещение, температура, безопасность)\n2. Торговые системы, где агенты представляют разных участников рынка\n3. Поисковые системы, где разные агенты отвечают за разные аспекты поиска\n4. Системы поддержки принятия решений, где агенты анализируют разные аспекты проблемы",
        agent_id="expert_agent"
    )
    
    # Получаем историю чата
    chat_history = memory_manager.get_chat_history(user_id)
    print("\nИстория чата:")
    for message in chat_history:
        print(f"{message.role}: {message.content[:50]}...")
    
    # Получаем форматированную историю чата
    formatted_history = memory_manager.get_formatted_history(user_id, include_system_messages=False)
    print("\nФорматированная история чата:")
    print(json.dumps(formatted_history, ensure_ascii=False, indent=2))
    
    # Получаем контекст диалога
    context = memory_manager.get_context(user_id)
    print("\nКонтекст диалога:")
    print(f"Резюме: {context['summary']}")
    print(f"Количество последних сообщений: {len(context['chat_history'])}")
    
    # Сохраняем состояние памяти
    memory_manager.save_all()
    print("\nСостояние памяти сохранено")
    
    # Создаем новый менеджер памяти с другим суммаризатором
    new_memory_manager = MemoryManager(
        storage_dir="data/memory_example_new",
        summarizer=create_keyword_summarizer(),
        embedding_provider=embedding_provider
    )
    
    # Получаем историю чата из нового менеджера
    new_chat_history = new_memory_manager.get_chat_history(user_id)
    print("\nИстория чата из нового менеджера:")
    print(f"Количество сообщений: {len(new_chat_history)}")
    
    # Добавляем новые сообщения
    new_memory_manager.add_user_message(
        user_id,
        "Как можно реализовать такую систему на Python?"
    )
    
    new_memory_manager.add_assistant_message(
        user_id,
        "Для реализации мульти-агентной системы на Python можно использовать различные библиотеки и фреймворки, такие как:\n1. SPADE (Smart Python Agent Development Environment)\n2. MESA - агентно-ориентированный фреймворк моделирования\n3. Ray - для распределенных вычислений\n4. LangChain - для создания агентов на основе языковых моделей\n\nОсновные шаги реализации:\n1. Определение интерфейсов агентов\n2. Реализация конкретных агентов\n3. Создание системы коммуникации между агентами\n4. Реализация координации и управления агентами",
        agent_id="developer_agent"
    )
    
    # Получаем обновленный контекст
    updated_context = new_memory_manager.get_context(user_id)
    print("\nОбновленный контекст диалога:")
    print(f"Резюме: {updated_context['summary']}")
    
    # Сохраняем обновленное состояние
    new_memory_manager.save_all()
    print("\nОбновленное состояние памяти сохранено")


if __name__ == "__main__":
    main() 