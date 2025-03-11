"""
Базовый класс для специализированных агентов в мульти-агентной системе.

Этот модуль предоставляет базовую реализацию класса агента, который может быть
расширен для создания специализированных агентов разного типа.
"""

import logging
from typing import Dict, List, Any, Optional, Callable

from langchain_core.language_models import BaseLLM
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from multi_agent_system.agent_analytics.data_collector import AgentDataCollector

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseAgent:
    """
    Базовый класс для специализированных агентов.
    
    Атрибуты:
        name (str): Уникальное имя агента
        display_name (str): Отображаемое имя агента для пользователей
        description (str): Описание возможностей и специализации агента
        system_prompt (str): Системный промпт, определяющий поведение агента
        llm (BaseLLM): Языковая модель для генерации ответов
        data_collector (AgentDataCollector): Сборщик данных для аналитики
    """
    
    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        system_prompt: str,
        llm: Optional[BaseLLM] = None,
        data_collector: Optional[AgentDataCollector] = None,
        use_cases: Optional[List[str]] = None,
        example_questions: Optional[List[str]] = None,
        routing_keywords: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Инициализирует агента с заданными параметрами.
        
        Args:
            name: Уникальное имя агента
            display_name: Отображаемое имя агента
            description: Описание возможностей агента
            system_prompt: Системный промпт агента
            llm: Языковая модель (по умолчанию локальный Mistral)
            data_collector: Сборщик данных для аналитики
            use_cases: Список вариантов использования агента
            example_questions: Примеры вопросов, на которые агент может ответить
            routing_keywords: Ключевые слова для маршрутизации запросов к этому агенту
            **kwargs: Дополнительные параметры
        """
        self.name = name
        self.display_name = display_name
        self.description = description
        self.system_prompt = system_prompt
        
        # Устанавливаем языковую модель (по умолчанию локальный Mistral)
        self.llm = llm or ChatMistralAI(
            model="mistral-medium",
            mistral_api_url="http://localhost:8080/completion"
        )
        
        # Устанавливаем сборщик данных для аналитики
        self.data_collector = data_collector or AgentDataCollector()
        
        # Дополнительные атрибуты для маршрутизации
        self.use_cases = use_cases or []
        self.example_questions = example_questions or []
        self.routing_keywords = routing_keywords or []
        
        # Создаем базовую цепочку для обработки запросов
        self._create_base_chain()
        
        logger.info(f"Инициализирован агент: {self.name} ({self.display_name})")
    
    def _create_base_chain(self):
        """Создает базовую цепочку для обработки запросов."""
        self.prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="{input}")
        ])
        
        self.chain = self.prompt_template | self.llm | StrOutputParser()
    
    @classmethod
    def from_config(cls, config: Dict[str, Any], **kwargs) -> 'BaseAgent':
        """
        Создает агента из конфигурации.
        
        Args:
            config: Словарь с конфигурацией агента
            **kwargs: Дополнительные параметры, которые переопределяют значения из конфигурации
            
        Returns:
            Созданный агент
        """
        # Объединяем конфигурацию с дополнительными параметрами
        agent_params = {**config, **kwargs}
        return cls(**agent_params)
    
    def process(
        self, 
        query: str, 
        chat_history: Optional[List[Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает запрос пользователя и возвращает ответ.
        
        Args:
            query: Запрос пользователя
            chat_history: История чата (если доступна)
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии
            
        Returns:
            Словарь с ответом и метаданными
        """
        start_time = logging.info(f"Агент {self.name} начал обработку запроса: {query[:50]}...")
        
        try:
            # Подготовка контекста с историей чата, если она доступна
            context = self._prepare_context(query, chat_history)
            
            # Выполнение запроса через цепочку
            response = self.chain.invoke({"input": context})
            
            # Сохранение взаимодействия для аналитики
            if user_id and self.data_collector:
                self.data_collector.store_interaction({
                    "user_id": user_id,
                    "agent_name": self.name,
                    "query": query,
                    "response": response,
                    "session_id": session_id,
                    "success": True
                })
            
            result = {
                "agent_name": self.name,
                "display_name": self.display_name,
                "response": response,
                "success": True,
                "error": None
            }
            
            logger.info(f"Агент {self.name} успешно обработал запрос")
            return result
            
        except Exception as e:
            error_message = f"Ошибка при обработке запроса агентом {self.name}: {str(e)}"
            logger.error(error_message)
            
            # Сохранение неудачного взаимодействия для аналитики
            if user_id and self.data_collector:
                self.data_collector.store_interaction({
                    "user_id": user_id,
                    "agent_name": self.name,
                    "query": query,
                    "response": None,
                    "session_id": session_id,
                    "success": False,
                    "error": str(e)
                })
            
            return {
                "agent_name": self.name,
                "display_name": self.display_name,
                "response": f"Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или обратитесь к другому агенту.",
                "success": False,
                "error": str(e)
            }
    
    def _prepare_context(self, query: str, chat_history: Optional[List[Any]] = None) -> str:
        """
        Подготавливает контекст для запроса, включая историю чата, если она доступна.
        
        Args:
            query: Текущий запрос пользователя
            chat_history: История чата
            
        Returns:
            Контекст для запроса
        """
        if not chat_history:
            return query
        
        # Формируем контекст с историей чата
        context = "История чата:\n"
        for message in chat_history[-5:]:  # Берем последние 5 сообщений для ограничения контекста
            if isinstance(message, dict):
                role = message.get("role", "unknown")
                content = message.get("content", "")
                context += f"{role.capitalize()}: {content}\n"
            else:
                context += f"{message}\n"
        
        context += f"\nТекущий запрос: {query}\n"
        context += "\nОтвечай только на текущий запрос, учитывая контекст из истории чата."
        
        return context
    
    def get_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию агента.
        
        Returns:
            Словарь с конфигурацией агента
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "use_cases": self.use_cases,
            "example_questions": self.example_questions,
            "routing_keywords": self.routing_keywords
        }


class AgentFactory:
    """
    Фабрика для создания агентов из конфигураций.
    """
    
    @staticmethod
    def create_agent(
        config: Dict[str, Any], 
        llm: Optional[BaseLLM] = None,
        data_collector: Optional[AgentDataCollector] = None
    ) -> BaseAgent:
        """
        Создает агента из конфигурации.
        
        Args:
            config: Конфигурация агента
            llm: Языковая модель (необязательно)
            data_collector: Сборщик данных (необязательно)
            
        Returns:
            Созданный агент
        """
        return BaseAgent.from_config(config, llm=llm, data_collector=data_collector)
    
    @staticmethod
    def create_all_agents(
        configs: List[Dict[str, Any]],
        llm: Optional[BaseLLM] = None,
        data_collector: Optional[AgentDataCollector] = None
    ) -> Dict[str, BaseAgent]:
        """
        Создает всех агентов из списка конфигураций.
        
        Args:
            configs: Список конфигураций агентов
            llm: Языковая модель (необязательно)
            data_collector: Сборщик данных (необязательно)
            
        Returns:
            Словарь с созданными агентами, где ключ - имя агента
        """
        agents = {}
        for config in configs:
            agent = AgentFactory.create_agent(config, llm, data_collector)
            agents[agent.name] = agent
        
        return agents
