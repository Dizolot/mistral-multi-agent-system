"""
Модуль управления агентами в мульти-агентной системе.

Обеспечивает регистрацию, получение и маршрутизацию между агентами.
"""

import os
from typing import Dict, Any, List, Optional, Callable
import re

from multi_agent_system.logger import get_logger

# Настройка логирования
logger = get_logger("agent_manager")

class Agent:
    """
    Класс агента, представляющий отдельную роль или специализацию модели.
    """
    
    def __init__(self, 
                agent_id: str, 
                name: str, 
                description: str, 
                system_prompt: str,
                keywords: List[str] = None):
        """
        Инициализация агента.
        
        Args:
            agent_id: Уникальный идентификатор агента
            name: Человекочитаемое имя агента
            description: Описание возможностей и специализации агента
            system_prompt: Системный промпт для модели, определяющий роль агента
            keywords: Список ключевых слов для маршрутизации запросов к этому агенту
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.keywords = keywords or []
        
        logger.info(f"Инициализирован агент: {name} (ID: {agent_id})")
    
    def check_relevance(self, text: str) -> float:
        """
        Проверяет релевантность запроса для данного агента.
        
        Args:
            text: Текст запроса пользователя
            
        Returns:
            float: Оценка релевантности от 0.0 до 1.0
        """
        if not self.keywords:
            return 0.0
            
        text_lower = text.lower()
        
        # Простая проверка по ключевым словам
        matches = sum(1 for keyword in self.keywords if keyword.lower() in text_lower)
        
        if matches > 0:
            # Нормализуем оценку (чем больше совпадений, тем выше оценка)
            return min(matches / len(self.keywords) * 2, 1.0)
        
        return 0.0

class AgentManager:
    """
    Менеджер агентов, управляющий регистрацией и выбором агентов для обработки запросов.
    """
    
    def __init__(self):
        """
        Инициализация менеджера агентов.
        """
        self.agents: Dict[str, Agent] = {}
        self.default_agent_id = None
        
        logger.info("Инициализирован менеджер агентов")
    
    def register_agent(self, agent: Agent, is_default: bool = False) -> None:
        """
        Регистрирует агента в системе.
        
        Args:
            agent: Экземпляр агента для регистрации
            is_default: Указывает, должен ли этот агент быть используемым по умолчанию
        """
        self.agents[agent.agent_id] = agent
        
        if is_default or self.default_agent_id is None:
            self.default_agent_id = agent.agent_id
            logger.info(f"Установлен агент по умолчанию: {agent.name} (ID: {agent.agent_id})")
            
        logger.info(f"Зарегистрирован агент: {agent.name} (ID: {agent.agent_id})")
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Возвращает агента по его ID.
        
        Args:
            agent_id: ID агента
            
        Returns:
            Agent: Экземпляр агента или None, если агент не найден
        """
        return self.agents.get(agent_id)
    
    def get_default_agent(self) -> Agent:
        """
        Возвращает агента по умолчанию.
        
        Returns:
            Agent: Агент по умолчанию
        """
        if self.default_agent_id is None:
            raise ValueError("Агент по умолчанию не установлен")
            
        return self.agents[self.default_agent_id]
    
    def route_to_agent(self, text: str) -> str:
        """
        Определяет, какой агент должен обработать запрос.
        
        Args:
            text: Текст запроса пользователя
            
        Returns:
            str: ID наиболее подходящего агента
        """
        if not self.agents:
            raise ValueError("Нет зарегистрированных агентов")
            
        # Если есть только один агент, используем его
        if len(self.agents) == 1:
            return next(iter(self.agents.keys()))
            
        # Вычисляем релевантность для каждого агента
        relevance_scores = {}
        for agent_id, agent in self.agents.items():
            relevance_scores[agent_id] = agent.check_relevance(text)
            
        # Находим агента с максимальной релевантностью
        max_relevance = max(relevance_scores.values())
        
        # Если нет явного лидера, используем агента по умолчанию
        if max_relevance < 0.3:  # Порог релевантности
            return self.default_agent_id
            
        # Выбираем агента с максимальной релевантностью
        for agent_id, relevance in relevance_scores.items():
            if relevance == max_relevance:
                logger.info(f"Маршрутизация запроса к агенту {agent_id} с релевантностью {relevance}")
                return agent_id
                
        # Если что-то пошло не так, используем агента по умолчанию
        return self.default_agent_id

# Создаем глобальный экземпляр менеджера агентов
agent_manager = AgentManager()

# Регистрируем стандартных агентов
def initialize_default_agents():
    """
    Инициализирует и регистрирует стандартный набор агентов.
    """
    # Агент по умолчанию
    default_agent = Agent(
        agent_id="default",
        name="Основной ассистент",
        description="Универсальный ассистент для общих вопросов",
        system_prompt="Вы — полезный ассистент. Отвечайте кратко, информативно и дружелюбно.",
        keywords=["помощь", "вопрос", "расскажи", "объясни", "что такое"]
    )
    
    # Python-агент
    python_agent = Agent(
        agent_id="python",
        name="Python-ассистент",
        description="Специалист по языку программирования Python",
        system_prompt="Вы — эксперт по Python. Помогайте с кодом, объясняйте концепции и предлагайте оптимальные решения.",
        keywords=["python", "питон", "код", "программирование", "скрипт", "функция", 
                 "класс", "метод", "библиотека", "import", "переменная"]
    )
    
    # Математический агент
    math_agent = Agent(
        agent_id="math",
        name="Математический ассистент",
        description="Специалист по математике и решению задач",
        system_prompt="Вы — эксперт по математике. Помогайте с решением задач, объясняйте концепции и проводите вычисления.",
        keywords=["математика", "формула", "вычислить", "решить", "уравнение", "функция", 
                 "интеграл", "производная", "геометрия", "алгебра", "число"]
    )
    
    # Регистрируем агентов
    agent_manager.register_agent(default_agent, is_default=True)
    agent_manager.register_agent(python_agent)
    agent_manager.register_agent(math_agent)
    
    logger.info("Стандартные агенты инициализированы и зарегистрированы")

# Инициализируем стандартных агентов при импорте модуля
initialize_default_agents() 