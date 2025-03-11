"""
Модуль для автоматической оптимизации и улучшения агентов.
Генерирует улучшенные версии агентов на основе анализа их эффективности.
"""
import os
import json
import logging
import datetime
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union

# Импорты LangChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseLLM

# Локальные импорты
from multi_agent_system.logger import get_logger
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector
from multi_agent_system.agent_analytics.performance_analyzer import PerformanceAnalyzer
from multi_agent_system.agent_analytics.metrics_evaluator import MetricsEvaluator

# Настройка логгера
logger = get_logger(__name__)

class AgentOptimizer:
    """
    Класс для автоматической оптимизации и улучшения агентов.
    Анализирует данные о производительности агентов и генерирует улучшенные версии.
    """
    
    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        data_collector: Optional[AgentDataCollector] = None,
        performance_analyzer: Optional[PerformanceAnalyzer] = None,
        metrics_evaluator: Optional[MetricsEvaluator] = None,
        optimization_dir: str = "agent_developer/optimizations"
    ):
        """
        Инициализация оптимизатора агентов.
        
        Args:
            llm: Модель языка для генерации улучшений
            data_collector: Экземпляр коллектора данных
            performance_analyzer: Экземпляр анализатора производительности
            metrics_evaluator: Экземпляр оценщика метрик
            optimization_dir: Директория для сохранения оптимизаций
        """
        self.llm = llm
        self.data_collector = data_collector or AgentDataCollector()
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer()
        self.metrics_evaluator = metrics_evaluator or MetricsEvaluator()
        self.optimization_dir = optimization_dir
        
        # Создаем директорию для сохранения оптимизаций, если её нет
        os.makedirs(self.optimization_dir, exist_ok=True)
        
        # Создаем промпты для генерации улучшений
        self._create_optimization_prompts()
        
        logger.info("AgentOptimizer инициализирован")
    
    def _create_optimization_prompts(self):
        """Создает промпты для генерации улучшений агентов"""
        
        # Промпт для анализа проблем и предложения улучшений
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """Ты - эксперт по оптимизации агентов искусственного интеллекта.
            Твоя задача - проанализировать данные о производительности агента и предложить
            конкретные улучшения, которые помогут повысить качество его ответов.
            Анализируй проблемные паттерны, типичные ошибки и сценарии, где агент работает неэффективно.
            
            Формат анализа:
            1. Выявленные проблемы и их причины
            2. Конкретные рекомендации по улучшению агента
            3. Предлагаемые изменения в промптах и настройках агента
            
            Будь конкретным и детальным в своих рекомендациях."""),
            ("human", """Проанализируй данные о производительности агента:
            
            Имя агента: {agent_name}
            Описание агента: {agent_description}
            Текущий системный промпт агента: {agent_system_prompt}
            
            Аналитические данные о производительности:
            {performance_data}
            
            Проблемные паттерны:
            {problematic_patterns}
            
            Метрики качества:
            {quality_metrics}""")
        ])
        
        # Промпт для генерации улучшенной версии системного промпта агента
        self.prompt_optimization_prompt = ChatPromptTemplate.from_messages([
            ("system", """Ты - эксперт по созданию эффективных промптов для агентов искусственного интеллекта.
            Твоя задача - разработать улучшенную версию системного промпта для агента,
            устраняющую выявленные проблемы и повышающую качество его работы.
            
            Учитывай:
            1. Выявленные проблемные паттерны и типичные ошибки
            2. Рекомендации по улучшению из предыдущего анализа
            3. Особенности специализации агента
            
            Сохраняй основную специализацию и ключевые аспекты поведения агента.
            Улучшенный промпт должен быть понятным, хорошо структурированным и
            содержать конкретные инструкции для повышения качества ответов агента."""),
            ("human", """Разработай улучшенную версию системного промпта для агента.
            
            Имя агента: {agent_name}
            Описание агента: {agent_description}
            Текущий системный промпт агента: {agent_system_prompt}
            
            Анализ проблем и рекомендации по улучшению:
            {improvement_recommendations}
            
            Создай улучшенную версию системного промпта, которая устранит выявленные проблемы:""")
        ])
    
    def optimize_agent(
        self,
        agent_name: str,
        agent_description: str,
        agent_system_prompt: str,
        min_interactions: int = 50
    ) -> Dict[str, Any]:
        """
        Оптимизирует агента на основе анализа его производительности.
        
        Args:
            agent_name: Имя агента
            agent_description: Описание агента
            agent_system_prompt: Текущий системный промпт агента
            min_interactions: Минимальное количество взаимодействий для анализа
            
        Returns:
            Dict[str, Any]: Результат оптимизации с улучшенным промптом
        """
        logger.info(f"Начало оптимизации агента {agent_name}")
        
        # Получаем данные о производительности агента
        performance_data = self.performance_analyzer.analyze_agent_performance(
            agent_name=agent_name,
            min_interactions=min_interactions
        )
        
        # Если недостаточно данных или анализ не удался
        if performance_data.get("status") != "success":
            logger.warning(f"Невозможно оптимизировать агента {agent_name}: {performance_data.get('message', 'Неизвестная ошибка')}")
            return {
                "agent_name": agent_name,
                "status": "failed",
                "message": performance_data.get("message", "Недостаточно данных для оптимизации"),
                "optimized_prompt": None
            }
        
        # Получаем проблемные паттерны
        problematic_patterns = performance_data.get("problematic_patterns", [])
        
        # Получаем метрики качества
        quality_metrics = {
            "success_rate": performance_data["metrics"]["success_rate"],
            "avg_processing_time": performance_data["metrics"]["avg_processing_time"],
            "failed_interactions": performance_data["metrics"]["failed_interactions"]
        }
        
        try:
            # Если нет LLM, не можем генерировать улучшения
            if self.llm is None:
                logger.warning(f"Невозможно оптимизировать агента {agent_name}: LLM не предоставлена")
                return {
                    "agent_name": agent_name,
                    "status": "failed",
                    "message": "LLM не предоставлена для генерации улучшений",
                    "optimized_prompt": None
                }
            
            # Генерируем анализ проблем и рекомендации по улучшению
            analysis_input = {
                "agent_name": agent_name,
                "agent_description": agent_description,
                "agent_system_prompt": agent_system_prompt,
                "performance_data": json.dumps(performance_data, indent=2),
                "problematic_patterns": json.dumps(problematic_patterns, indent=2),
                "quality_metrics": json.dumps(quality_metrics, indent=2)
            }
            
            analysis_chain = self.analysis_prompt | self.llm
            analysis_result = analysis_chain.invoke(analysis_input)
            
            # Получаем текст рекомендаций по улучшению
            improvement_recommendations = analysis_result.content
            
            # Генерируем улучшенный системный промпт
            prompt_optimization_input = {
                "agent_name": agent_name,
                "agent_description": agent_description,
                "agent_system_prompt": agent_system_prompt,
                "improvement_recommendations": improvement_recommendations
            }
            
            prompt_optimization_chain = self.prompt_optimization_prompt | self.llm
            optimization_result = prompt_optimization_chain.invoke(prompt_optimization_input)
            
            # Получаем улучшенный системный промпт
            optimized_prompt = optimization_result.content
            
            # Создаем результат оптимизации
            optimization_result = {
                "agent_name": agent_name,
                "status": "success",
                "timestamp": datetime.datetime.now().isoformat(),
                "original_prompt": agent_system_prompt,
                "optimized_prompt": optimized_prompt,
                "improvement_recommendations": improvement_recommendations,
                "performance_data": performance_data
            }
            
            # Сохраняем результат оптимизации
            self._save_optimization_result(optimization_result)
            
            logger.info(f"Оптимизация агента {agent_name} успешно завершена")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Ошибка при оптимизации агента {agent_name}: {str(e)}")
            return {
                "agent_name": agent_name,
                "status": "failed",
                "message": f"Ошибка при оптимизации: {str(e)}",
                "optimized_prompt": None
            }
    
    def _save_optimization_result(self, result: Dict[str, Any]) -> None:
        """
        Сохраняет результат оптимизации в файл.
        
        Args:
            result: Результат оптимизации
        """
        try:
            # Формируем имя файла на основе имени агента и даты оптимизации
            agent_name = result["agent_name"]
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            version_id = uuid.uuid4().hex[:8]
            file_path = os.path.join(self.optimization_dir, f"optimization_{agent_name}_{date_str}_{version_id}.json")
            
            # Сохраняем результат в файл
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Результат оптимизации сохранен в файл: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата оптимизации: {str(e)}")
    
    def get_latest_optimization(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Получает последнюю оптимизацию для указанного агента.
        
        Args:
            agent_name: Имя агента
            
        Returns:
            Optional[Dict[str, Any]]: Последняя оптимизация или None, если оптимизаций нет
        """
        try:
            # Получаем список файлов оптимизаций для агента
            optimization_files = [
                f for f in os.listdir(self.optimization_dir)
                if f.startswith(f"optimization_{agent_name}_") and f.endswith(".json")
            ]
            
            if not optimization_files:
                logger.warning(f"Оптимизации для агента {agent_name} не найдены")
                return None
            
            # Сортируем файлы по дате создания (от новых к старым)
            optimization_files.sort(reverse=True)
            
            # Загружаем последнюю оптимизацию
            latest_file = os.path.join(self.optimization_dir, optimization_files[0])
            with open(latest_file, "r", encoding="utf-8") as f:
                latest_optimization = json.load(f)
            
            logger.info(f"Загружена последняя оптимизация для агента {agent_name} из файла {latest_file}")
            
            return latest_optimization
            
        except Exception as e:
            logger.error(f"Ошибка при получении последней оптимизации для агента {agent_name}: {str(e)}")
            return None

# Создаем экземпляр оптимизатора агентов для использования в других модулях
agent_optimizer = AgentOptimizer() 