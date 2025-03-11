"""
Пакет для анализа эффективности агентов и сбора данных о взаимодействии с ними.

Этот пакет включает модули для:
- Сбора данных о взаимодействии пользователей с агентами
- Анализа эффективности агентов на основе собранных данных
- Оценки качества ответов агентов по различным метрикам
- Генерации рекомендаций по улучшению агентов
"""

from multi_agent_system.agent_analytics.data_collector import data_collector, AgentDataCollector
from multi_agent_system.agent_analytics.performance_analyzer import performance_analyzer, PerformanceAnalyzer
from multi_agent_system.agent_analytics.metrics_evaluator import metrics_evaluator, MetricsEvaluator

__all__ = [
    'data_collector',
    'performance_analyzer',
    'metrics_evaluator',
    'AgentDataCollector',
    'PerformanceAnalyzer',
    'MetricsEvaluator'
] 