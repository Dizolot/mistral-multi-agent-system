"""
Агент общего назначения для мульти-агентной системы.
Этот агент обрабатывает широкий спектр запросов и является 
базовым агентом для общих вопросов.
"""
import logging
from typing import Dict, List, Any, Optional

# Импорты из LangChain
from langchain_core.language_models import BaseLLM

# Локальные импорты
from multi_agent_system.agents.base_agent import LangChainAgent
from multi_agent_system.logger import get_logger

# Настройка логгера
logger = get_logger(__name__)

class GeneralAgent(LangChainAgent):
    """
    Агент общего назначения для обработки широкого спектра запросов.
    """
    
    def __init__(
        self, 
        llm: Optional[BaseLLM] = None,
        mistral_api_url: str = "http://localhost:8080/completion",
        tools: Optional[List[Any]] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Инициализация агента общего назначения.
        
        Args:
            llm: Модель языка для агента (если None, будет использоваться API Mistral)
            mistral_api_url: URL для API Mistral
            tools: Список инструментов, доступных агенту
            system_prompt: Системный промпт для агента
        """
        # Имя и описание для агента общего назначения
        name = "General Assistant"
        description = (
            "Я агент общего назначения, способный отвечать на широкий спектр вопросов и запросов. "
            "Я могу предоставлять информацию по различным темам, давать рекомендации, "
            "объяснять концепции и помогать с повседневными задачами. "
            "Если запрос требует специальных знаний, я могу перенаправить его специализированному агенту."
        )
        
        # Системный промпт по умолчанию для агента общего назначения
        default_system_prompt = (
            "Ты — опытный ассистент общего назначения, способный отвечать на широкий спектр вопросов. "
            "Твои ответы должны быть информативными, полезными и дружелюбными. "
            "Ты должен стремиться предоставить наиболее точную и полезную информацию. "
            "Если вопрос выходит за рамки твоих знаний или требует специализированной экспертизы, "
            "честно признайся в этом и предложи обратиться к соответствующему специалисту. "
            "Всегда старайся быть учтивым и полезным, даже если запрос пользователя неясен или неполон."
        )
        
        # Используем предоставленный системный промпт или промпт по умолчанию
        system_prompt = system_prompt or default_system_prompt
        
        # Инициализируем базовый класс
        super().__init__(
            name=name,
            description=description,
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            mistral_api_url=mistral_api_url
        )
        
        logger.info("Агент общего назначения инициализирован")
    
    def process(self, user_input: str, chat_history: List[Any] = None) -> Dict[str, Any]:
        """
        Обрабатывает запрос пользователя.
        
        Args:
            user_input: Запрос пользователя
            chat_history: История чата (опционально)
        
        Returns:
            Dict: Результат обработки запроса
        """
        # Вызываем метод базового класса для обработки запроса
        result = super().process(user_input, chat_history)
        
        # Логируем обработку запроса
        logger.info(f"Агент общего назначения обработал запрос: '{user_input[:50]}...' (если длинный)")
        
        return result 