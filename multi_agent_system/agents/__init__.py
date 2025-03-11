"""
Пакет для работы с различными специализированными агентами в мульти-агентной системе.

Этот пакет предоставляет инструменты для:
- Создания и настройки специализированных агентов
- Загрузки конфигураций агентов
- Работы с агентами через интерфейс LangChain
"""

from multi_agent_system.agents.agent_configs import (
    get_agent_config,
    get_all_agent_configs,
    get_agent_names,
    ALL_AGENT_CONFIGS,
    GENERAL_AGENT_CONFIG,
    PROGRAMMING_AGENT_CONFIG,
    SCIENCE_MATH_AGENT_CONFIG
)

from multi_agent_system.agents.base_agent import (
    BaseAgent,
    AgentFactory
)

__all__ = [
    'get_agent_config',
    'get_all_agent_configs',
    'get_agent_names',
    'ALL_AGENT_CONFIGS',
    'GENERAL_AGENT_CONFIG',
    'PROGRAMMING_AGENT_CONFIG',
    'SCIENCE_MATH_AGENT_CONFIG',
    'BaseAgent',
    'AgentFactory'
]
