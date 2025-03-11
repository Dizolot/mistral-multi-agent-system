"""
Пакет разработчика агентов для автоматической оптимизации и улучшения агентов.

Этот пакет предоставляет инструменты и классы для:
- Оптимизации агентов на основе аналитических данных
- Тестирования агентов и их улучшений
- Управления версиями агентов
- Автоматического создания новых специализированных агентов
"""

# Импорты будут добавляться по мере создания модулей
from multi_agent_system.agent_developer.agent_optimizer import AgentOptimizer
from multi_agent_system.agent_developer.agent_tester import AgentTester
from multi_agent_system.agent_developer.version_manager import VersionManager

__all__ = [
    'agent_optimizer', 'AgentOptimizer',
    'agent_tester', 'AgentTester',
    'version_manager', 'VersionManager'
] 