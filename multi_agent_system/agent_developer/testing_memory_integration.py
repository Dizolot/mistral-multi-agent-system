"""
Модуль для интеграции системы тестирования агентов с историей диалогов.

Этот модуль предоставляет инструменты для создания тестовых случаев на основе
реальных диалогов с пользователями, а также для оценки улучшений агентов
на основе исторических данных.
"""

import os
import json
import logging
import random
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

from multi_agent_system.memory.conversation_memory import ConversationMemoryManager
from multi_agent_system.agent_developer.agent_tester import AgentTester
from multi_agent_system.agent_developer.agent_optimizer import AgentOptimizer
from multi_agent_system.agent_developer.version_manager import VersionManager
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector
from multi_agent_system.agent_analytics.performance_analyzer import PerformanceAnalyzer
from multi_agent_system.agent_analytics.metrics_evaluator import MetricsEvaluator
from multi_agent_system.logger import get_logger

# Настройка логирования
logger = get_logger(__name__)

class TestingMemoryIntegration:
    """
    Класс для интеграции системы тестирования агентов с историей диалогов.
    
    Предоставляет методы для создания тестовых случаев на основе реальных диалогов
    и оценки улучшений агентов на исторических данных.
    """
    
    def __init__(
        self,
        memory_manager: ConversationMemoryManager,
        agent_tester: AgentTester,
        agent_optimizer: Optional[AgentOptimizer] = None,
        version_manager: Optional[VersionManager] = None,
        data_collector: Optional[AgentDataCollector] = None,
        performance_analyzer: Optional[PerformanceAnalyzer] = None,
        metrics_evaluator: Optional[MetricsEvaluator] = None
    ):
        """
        Инициализирует интеграцию между тестированием агентов и историей диалогов.
        
        Args:
            memory_manager: Менеджер памяти для доступа к истории диалогов
            agent_tester: Тестировщик агентов для проверки улучшений
            agent_optimizer: Оптимизатор агентов (опционально)
            version_manager: Менеджер версий агентов (опционально)
            data_collector: Коллектор данных для записи в аналитику (опционально)
            performance_analyzer: Анализатор производительности (опционально)
            metrics_evaluator: Оценщик метрик (опционально)
        """
        self.memory_manager = memory_manager
        self.agent_tester = agent_tester
        self.agent_optimizer = agent_optimizer or AgentOptimizer()
        self.version_manager = version_manager or VersionManager()
        self.data_collector = data_collector or AgentDataCollector()
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer()
        self.metrics_evaluator = metrics_evaluator or MetricsEvaluator()
        
        logger.info("Интеграция тестирования и памяти инициализирована")
    
    def create_test_dataset_from_memory(
        self,
        agent_name: str,
        sample_size: int = 20,
        min_message_length: int = 50,
        max_users: Optional[int] = None,
        filter_by_quality: bool = True
    ) -> str:
        """
        Создает тестовый набор данных на основе истории диалогов пользователей.
        
        Args:
            agent_name: Имя агента, для которого создается тестовый набор
            sample_size: Размер выборки (количество тестовых случаев)
            min_message_length: Минимальная длина сообщения для включения в тестовый набор
            max_users: Максимальное количество пользователей для анализа
            filter_by_quality: Фильтровать сообщения по качеству ответа
            
        Returns:
            Идентификатор созданного тестового набора данных
        """
        # Получаем список всех пользователей
        users = self.memory_manager.get_all_users()
        
        # Если указано максимальное количество пользователей, ограничиваем список
        if max_users and len(users) > max_users:
            users = random.sample(users, max_users)
        
        # Собираем все диалоги
        test_cases = []
        for user_id in users:
            # Получаем историю диалога
            chat_history = self.memory_manager.get_chat_history(user_id)
            
            # Группируем сообщения в пары "запрос-ответ"
            current_request = None
            
            for message in chat_history:
                # Пропускаем системные сообщения
                if isinstance(message, SystemMessage):
                    continue
                
                # Обрабатываем сообщение пользователя (запрос)
                if isinstance(message, HumanMessage):
                    current_request = message
                
                # Обрабатываем сообщение агента (ответ)
                elif isinstance(message, AIMessage) and current_request is not None:
                    # Проверяем метаданные сообщения
                    message_agent_name = "default_agent"
                    if hasattr(message, "additional_kwargs") and "agent_name" in message.additional_kwargs:
                        message_agent_name = message.additional_kwargs["agent_name"]
                    
                    # Проверяем, соответствует ли сообщение нужному агенту
                    if message_agent_name == agent_name:
                        # Проверяем длину сообщения
                        if len(current_request.content) >= min_message_length:
                            # Добавляем тестовый случай
                            test_case = {
                                "question": current_request.content,
                                "reference_answer": message.content,
                                "metadata": {
                                    "user_id": user_id,
                                    "timestamp": datetime.now().isoformat(),
                                    "source": "conversation_memory"
                                }
                            }
                            test_cases.append(test_case)
                    
                    # Сбрасываем текущий запрос
                    current_request = None
        
        # Если необходимо фильтровать по качеству, оцениваем каждый тестовый случай
        if filter_by_quality and test_cases:
            # Используем эвристики для оценки качества
            scored_cases = []
            for case in test_cases:
                question = case["question"]
                answer = case["reference_answer"]
                
                # Простая эвристика: длина ответа относительно вопроса
                ratio = len(answer) / max(len(question), 1)
                
                # Наличие ключевых слов из вопроса в ответе
                question_keywords = set([word.lower() for word in question.split() if len(word) > 4])
                answer_keywords = set([word.lower() for word in answer.split() if len(word) > 4])
                keyword_overlap = len(question_keywords.intersection(answer_keywords)) / max(len(question_keywords), 1)
                
                # Общая оценка
                score = (ratio * 0.5) + (keyword_overlap * 0.5)
                scored_cases.append((case, score))
            
            # Сортируем по оценке (от высшей к низшей)
            scored_cases.sort(key=lambda x: x[1], reverse=True)
            
            # Выбираем лучшие случаи
            best_cases = [case for case, _ in scored_cases[:sample_size]]
            test_cases = best_cases
        
        # Если у нас больше тестовых случаев, чем требуется, выбираем случайную выборку
        if len(test_cases) > sample_size:
            test_cases = random.sample(test_cases, sample_size)
        
        # Создаем тестовый набор данных
        dataset_id = self.agent_tester.create_test_dataset(
            agent_name=agent_name,
            test_cases=test_cases
        )
        
        logger.info(f"Создан тестовый набор данных {dataset_id} с {len(test_cases)} тестовыми случаями")
        return dataset_id
    
    def improve_agent_from_memory(
        self,
        agent_name: str,
        agent_system_prompt: str,
        agent_description: str,
        min_sample_size: int = 10,
        test_improvement: bool = True,
        deploy_if_better: bool = False
    ) -> Dict[str, Any]:
        """
        Улучшает агента на основе истории диалогов и тестирует улучшения.
        
        Args:
            agent_name: Имя агента
            agent_system_prompt: Текущий системный промпт агента
            agent_description: Описание агента
            min_sample_size: Минимальный размер выборки для создания тестового набора
            test_improvement: Тестировать ли улучшения
            deploy_if_better: Внедрять ли улучшения, если они лучше
            
        Returns:
            Результаты улучшения и тестирования
        """
        results = {
            "agent_name": agent_name,
            "timestamp": datetime.now().isoformat(),
            "improvement_generated": False,
            "test_performed": False,
            "deployed": False,
            "test_results": None,
            "improvement": None
        }
        
        # Шаг 1: Создаем тестовый набор данных из истории диалогов
        dataset_id = self.create_test_dataset_from_memory(
            agent_name=agent_name,
            sample_size=min_sample_size
        )
        
        if not dataset_id:
            logger.warning(f"Не удалось создать тестовый набор данных для агента {agent_name}")
            return results
        
        # Шаг 2: Собираем данные для анализа
        performance_data = self.performance_analyzer.analyze_agent_performance(agent_name)
        
        # Шаг 3: Улучшаем агента
        optimization_result = self.agent_optimizer.optimize_agent(
            agent_name=agent_name,
            agent_description=agent_description,
            agent_system_prompt=agent_system_prompt,
            min_interactions=min_sample_size
        )
        
        if not optimization_result or "improved_system_prompt" not in optimization_result:
            logger.warning(f"Не удалось улучшить агента {agent_name}")
            return results
        
        results["improvement_generated"] = True
        results["improvement"] = optimization_result
        
        # Шаг 4: Тестируем улучшения
        if test_improvement:
            # Получаем системный промпт улучшенного агента
            improved_system_prompt = optimization_result["improved_system_prompt"]
            
            # Создаем версию улучшенного агента
            improved_version_id = self.version_manager.save_agent_version(
                agent={
                    "name": agent_name,
                    "description": agent_description,
                    "system_prompt": improved_system_prompt,
                    "version_notes": "Автоматически улучшенная версия на основе истории диалогов"
                },
                version_name=f"{agent_name}_improved_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Получаем текущую производственную версию
            original_version_id = self.version_manager.get_production_version(agent_name)
            if not original_version_id:
                # Если нет производственной версии, создаем её
                original_version_id = self.version_manager.save_agent_version(
                    agent={
                        "name": agent_name,
                        "description": agent_description,
                        "system_prompt": agent_system_prompt,
                        "version_notes": "Базовая версия перед автоматическим улучшением"
                    },
                    version_name=f"{agent_name}_original_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    is_production=True
                )
            
            # Тестируем улучшения
            test_results = self.version_manager.evaluate_improvement(
                agent_name=agent_name,
                original_version_id=original_version_id,
                improved_version_id=improved_version_id,
                test_dataset_id=dataset_id
            )
            
            results["test_performed"] = True
            results["test_results"] = test_results
            
            # Шаг 5: Внедряем улучшения, если они лучше
            if deploy_if_better and test_results.get("is_improvement", False):
                deployed = self.version_manager.deploy_improvement(
                    agent_name=agent_name,
                    version_id=improved_version_id
                )
                results["deployed"] = deployed
        
        return results


def create_auto_improvement_cycle(
    memory_manager: ConversationMemoryManager,
    agent_tester: AgentTester,
    agent_optimizer: AgentOptimizer,
    version_manager: VersionManager,
    data_collector: AgentDataCollector
) -> Dict[str, Any]:
    """
    Создает полный цикл автоматического улучшения агентов.
    
    Args:
        memory_manager: Менеджер памяти
        agent_tester: Тестировщик агентов
        agent_optimizer: Оптимизатор агентов
        version_manager: Менеджер версий
        data_collector: Коллектор данных
        
    Returns:
        Результаты цикла улучшения
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "agents_processed": 0,
        "agents_improved": 0,
        "agents_deployed": 0,
        "agent_results": {}
    }
    
    # Интеграция памяти и тестирования
    testing_integration = TestingMemoryIntegration(
        memory_manager=memory_manager,
        agent_tester=agent_tester,
        agent_optimizer=agent_optimizer,
        version_manager=version_manager,
        data_collector=data_collector
    )
    
    # Получаем список всех агентов
    agents = version_manager.get_all_agents()
    
    # Для каждого агента запускаем процесс улучшения
    for agent_name in agents:
        # Получаем текущую версию агента
        agent_version = version_manager.load_agent_version(agent_name)
        
        if not agent_version:
            logger.warning(f"Не удалось загрузить версию агента {agent_name}")
            continue
        
        # Получаем системный промпт и описание агента
        agent_system_prompt = agent_version.get("system_prompt", "")
        agent_description = agent_version.get("description", "")
        
        if not agent_system_prompt:
            logger.warning(f"Системный промпт агента {agent_name} не найден")
            continue
        
        # Улучшаем агента
        improvement_result = testing_integration.improve_agent_from_memory(
            agent_name=agent_name,
            agent_system_prompt=agent_system_prompt,
            agent_description=agent_description,
            test_improvement=True,
            deploy_if_better=True
        )
        
        # Обновляем результаты
        results["agents_processed"] += 1
        if improvement_result["improvement_generated"]:
            results["agents_improved"] += 1
        if improvement_result["deployed"]:
            results["agents_deployed"] += 1
        
        results["agent_results"][agent_name] = improvement_result
    
    logger.info(f"Цикл автоматического улучшения завершен. Улучшено {results['agents_improved']} из {results['agents_processed']} агентов")
    return results 