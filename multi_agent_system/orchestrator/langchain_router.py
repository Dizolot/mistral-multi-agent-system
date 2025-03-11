"""
Модуль маршрутизации запросов между агентами с использованием LangChain.
Осуществляет анализ входящих запросов и перенаправление их соответствующим агентам.
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Импорты LangChain
from langchain_core.language_models import BaseLLM, LLM
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

# Импорты для LangGraph (часть экосистемы LangChain)
try:
    from langchain.graphs.state_graph import StateGraph, Node, END
except ImportError:
    logging.warning("LangGraph не установлен. Используйте команду: pip install langchain-experimental")

# Локальные импорты
from multi_agent_system.logger import get_logger
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector
from multi_agent_system.memory.conversation_memory import ConversationMemoryManager

# Настройка логгера
logger = get_logger(__name__)

# Инициализация глобального коллектора данных
data_collector = AgentDataCollector()

class LangChainRouter:
    """
    Маршрутизатор запросов на основе LangChain.
    Анализирует входящие запросы и перенаправляет их соответствующим агентам.
    """
    
    def __init__(
        self, 
        llm: Optional[BaseLLM] = None,
        mistral_api_url: str = "http://localhost:8080/completion",
        agent_configs: Optional[List[Dict[str, Any]]] = None,
        memory_manager: Optional[ConversationMemoryManager] = None
    ):
        """
        Инициализация маршрутизатора.
        
        Args:
            llm: Модель языка для маршрутизации (если None, будет использоваться API Mistral)
            mistral_api_url: URL для API Mistral
            agent_configs: Конфигурации агентов в формате списка словарей
            memory_manager: Менеджер памяти разговоров, если None - будет создан новый
        """
        self.llm = llm
        self.mistral_api_url = mistral_api_url
        self.agent_configs = agent_configs or []
        
        # Инициализация менеджера памяти
        self.memory_manager = memory_manager or ConversationMemoryManager()
        
        # Список доступных агентов
        self.available_agents = {}
        
        # Интеграция с Mistral через собственный API (если llm не указан)
        if self.llm is None:
            # Здесь будет код для интеграции с Mistral API
            logger.info(f"Используется Mistral API по адресу: {self.mistral_api_url}")
        
        # Создаем промпт для маршрутизатора
        self._create_router_prompt()
        
        # Регистрируем агентов из конфигураций
        if self.agent_configs:
            self._register_agents_from_config()
        
        logger.info("LangChainRouter инициализирован с менеджером памяти")
    
    def _create_router_prompt(self):
        """Создает промпт для маршрутизатора"""
        self.router_system_prompt = (
            "Ты - маршрутизатор запросов, который определяет, какому агенту нужно направить "
            "запрос пользователя. Проанализируй запрос и определи, какой агент лучше всего "
            "подходит для его обработки на основе доступных агентов и их описаний.\n\n"
            "Доступные агенты:\n"
            "{agent_descriptions}\n\n"
            "История диалога (для контекста):\n"
            "{chat_summary}\n\n"
            "Выведи только имя агента, которому нужно перенаправить запрос, без дополнительного текста."
        )
        
        self.router_prompt = ChatPromptTemplate.from_messages([
            ("system", self.router_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_input}")
        ])
        
        logger.debug("Промпт для маршрутизатора создан")
    
    def _register_agents_from_config(self):
        """Регистрирует агентов из конфигураций"""
        for agent_config in self.agent_configs:
            agent_name = agent_config.get("name")
            agent_description = agent_config.get("description", "")
            agent_handler = agent_config.get("handler")
            
            if agent_name and agent_handler:
                self.available_agents[agent_name] = {
                    "description": agent_description,
                    "handler": agent_handler
                }
                logger.info(f"Зарегистрирован агент: {agent_name}")
            else:
                logger.warning(f"Некорректная конфигурация агента: {agent_config}")
    
    def register_agent(self, name: str, description: str, handler: callable):
        """
        Регистрирует нового агента в маршрутизаторе.
        
        Args:
            name: Имя агента
            description: Описание агента
            handler: Функция-обработчик запросов для агента
        """
        self.available_agents[name] = {
            "description": description,
            "handler": handler
        }
        logger.info(f"Зарегистрирован агент: {name}")
        
    def route_request(self, user_input: str, chat_history: List[Any] = None, user_id: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        Маршрутизирует запрос пользователя соответствующему агенту.
        
        Args:
            user_input: Запрос пользователя
            chat_history: История чата (опционально)
            user_id: Идентификатор пользователя (опционально)
            session_id: Идентификатор сессии (опционально)
        
        Returns:
            Dict: Результат обработки запроса выбранным агентом
        """
        chat_history = chat_history or []
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        session_id = session_id or f"session_{uuid.uuid4().hex}"
        
        # Засекаем время начала обработки запроса для аналитики
        start_time = time.time()
        
        # Добавляем сообщение пользователя в память
        self.memory_manager.add_user_message(user_id, user_input)
        
        # Получаем историю чата из памяти, если chat_history не предоставлен
        if not chat_history:
            # Получаем историю сообщений из менеджера памяти
            chat_history = self.memory_manager.get_chat_history(user_id)
        
        # Получаем резюме предыдущего диалога
        chat_summary = self.memory_manager.get_chat_summary(user_id)
        
        # Если нет зарегистрированных агентов, возвращаем ошибку
        if not self.available_agents:
            logger.error("Нет зарегистрированных агентов для маршрутизации")
            
            error_response = "Система не настроена. Пожалуйста, зарегистрируйте агентов."
            
            # Добавляем ответ в память
            self.memory_manager.add_ai_message(user_id, error_response, agent_name="system")
            
            # Записываем неудачное взаимодействие в аналитику
            data_collector.record_interaction(
                user_id=user_id,
                session_id=session_id,
                agent_name="system",
                request=user_input,
                response=error_response,
                processing_time=time.time() - start_time,
                is_successful=False,
                metadata={"error": "no_agents_available"}
            )
            
            return {
                "error": "Нет доступных агентов для обработки запроса",
                "response": error_response
            }
        
        # Формируем описания агентов для промпта
        agent_descriptions = "\n".join([
            f"- {name}: {details['description']}" for name, details in self.available_agents.items()
        ])
        
        # Определяем, какому агенту направить запрос
        try:
            # Готовим промпт для маршрутизатора
            prompt_input = {
                "agent_descriptions": agent_descriptions,
                "chat_history": chat_history,
                "chat_summary": chat_summary,
                "user_input": user_input
            }
            
            # Если есть модель LLM, используем ее
            if self.llm:
                router_chain = self.router_prompt | self.llm | StrOutputParser()
                agent_name = router_chain.invoke(prompt_input).strip()
            else:
                # Здесь будет код для вызова Mistral API напрямую
                # Временная заглушка
                agent_name = list(self.available_agents.keys())[0]
                logger.warning(f"Прямой вызов Mistral API не реализован, выбран первый агент: {agent_name}")
            
            logger.info(f"Запрос маршрутизирован к агенту: {agent_name}")
            
            # Проверяем, существует ли выбранный агент
            if agent_name not in self.available_agents:
                logger.warning(f"Агент {agent_name} не найден, используем первого доступного агента")
                agent_name = list(self.available_agents.keys())[0]
            
            # Засекаем время перед вызовом агента
            agent_start_time = time.time()
            
            # Вызываем обработчик выбранного агента с передачей истории диалога
            handler = self.available_agents[agent_name]["handler"]
            
            # Если обработчик принимает параметр chat_history, передаем историю диалога
            import inspect
            sig = inspect.signature(handler)
            
            if 'chat_history' in sig.parameters:
                result = handler(user_input, chat_history=chat_history)
            else:
                result = handler(user_input)
            
            # Сохраняем ответ агента в менеджере памяти
            self.memory_manager.add_ai_message(user_id, result, agent_name=agent_name)
            
            # Вычисляем общее время обработки
            processing_time = time.time() - start_time
            agent_processing_time = time.time() - agent_start_time
            
            # Записываем успешное взаимодействие в аналитику
            data_collector.record_interaction(
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name,
                request=user_input,
                response=result,
                processing_time=processing_time,
                is_successful=True,
                metadata={
                    "router_time": agent_start_time - start_time,
                    "agent_time": agent_processing_time,
                    "chat_history_length": len(chat_history)
                }
            )
            
            return {
                "agent": agent_name,
                "response": result,
                "status": "success",
                "processing_time": processing_time
            }
            
        except Exception as e:
            # Вычисляем время до ошибки
            error_time = time.time() - start_time
            
            logger.error(f"Ошибка при маршрутизации запроса: {str(e)}")
            
            error_response = f"Произошла ошибка при обработке вашего запроса."
            
            # Сохраняем сообщение об ошибке в менеджере памяти
            self.memory_manager.add_ai_message(user_id, error_response, agent_name="error")
            
            # Записываем неудачное взаимодействие в аналитику
            data_collector.record_interaction(
                user_id=user_id,
                session_id=session_id,
                agent_name="error",
                request=user_input,
                response=error_response,
                processing_time=error_time,
                is_successful=False,
                metadata={"error": str(e)}
            )
            
            return {
                "error": f"Ошибка при обработке запроса: {str(e)}",
                "response": error_response,
                "status": "error"
            }

    def setup_langgraph(self):
        """
        Настраивает граф состояний LangGraph для маршрутизации запросов.
        Этот метод требует установки langchain-experimental.
        
        Returns:
            StateGraph: Настроенный граф состояний
        """
        try:
            # Проверяем, что LangGraph доступен
            if 'StateGraph' not in globals():
                raise ImportError("LangGraph не установлен")
            
            # Создаем базовое состояние графа
            state_dict = {
                "messages": [],
                "current_agent": None,
                "next_agent": None,
                "final_response": None,
                "user_id": None,  # Добавляем информацию о пользователе для работы с памятью
                "session_id": None,
                "chat_history": []  # Добавляем историю чата
            }
            
            # Создаем узлы для каждого агента
            nodes = {}
            for agent_name, agent_data in self.available_agents.items():
                # Создаем обертку для обработчика, чтобы включить использование памяти
                def create_agent_handler(agent_name, handler):
                    def agent_with_memory(state):
                        user_id = state["user_id"]
                        
                        # Получаем историю диалога из памяти
                        chat_history = self.memory_manager.get_chat_history(user_id)
                        
                        # Получаем последнее сообщение пользователя
                        user_message = state["messages"][-1].get("content", "")
                        if isinstance(user_message, dict):  # На случай, если сообщение в формате LangChain
                            user_message = user_message.get("content", "")
                        
                        # Вызываем обработчик агента
                        response = handler(user_message, chat_history=chat_history)
                        
                        # Сохраняем ответ в памяти
                        self.memory_manager.add_ai_message(user_id, response, agent_name=agent_name)
                        
                        # Обновляем состояние
                        state["final_response"] = response
                        state["current_agent"] = agent_name
                        
                        return state
                    
                    return agent_with_memory
                
                # Регистрируем обработчик с поддержкой памяти
                nodes[agent_name] = Node(create_agent_handler(agent_name, agent_data["handler"]))
            
            # Добавляем узел маршрутизатора
            def router_node(state):
                user_id = state["user_id"] or f"user_{uuid.uuid4().hex[:8]}"
                state["user_id"] = user_id
                
                # Получаем последнее сообщение пользователя
                user_message = state["messages"][-1].get("content", "")
                if isinstance(user_message, dict):  # На случай, если сообщение в формате LangChain
                    user_message = user_message.get("content", "")
                
                # Добавляем сообщение пользователя в память
                self.memory_manager.add_user_message(user_id, user_message)
                
                # Получаем историю чата из памяти
                chat_history = self.memory_manager.get_chat_history(user_id)
                state["chat_history"] = chat_history
                
                # Получаем резюме предыдущего диалога
                chat_summary = self.memory_manager.get_chat_summary(user_id)
                
                # Формируем описания агентов для промпта
                agent_descriptions = "\n".join([
                    f"- {name}: {details['description']}" for name, details in self.available_agents.items()
                ])
                
                # Готовим промпт для маршрутизатора
                prompt_input = {
                    "agent_descriptions": agent_descriptions,
                    "chat_history": chat_history,
                    "chat_summary": chat_summary,
                    "user_input": user_message
                }
                
                # Определяем агента
                try:
                    if self.llm:
                        router_chain = self.router_prompt | self.llm | StrOutputParser()
                        agent_name = router_chain.invoke(prompt_input).strip()
                    else:
                        # Временная заглушка
                        agent_name = list(self.available_agents.keys())[0]
                    
                    # Проверяем, существует ли агент
                    if agent_name not in self.available_agents:
                        agent_name = list(self.available_agents.keys())[0]
                    
                    # Обновляем состояние
                    state["next_agent"] = agent_name
                    
                except Exception as e:
                    logger.error(f"Ошибка в маршрутизаторе LangGraph: {str(e)}")
                    # В случае ошибки используем первого доступного агента
                    state["next_agent"] = list(self.available_agents.keys())[0]
                
                return state
            
            nodes["router"] = Node(router_node)
            
            # Создаем граф
            graph = StateGraph(state_dict)
            
            # Добавляем узлы в граф
            for name, node in nodes.items():
                graph.add_node(name, node)
            
            # Настраиваем связи между узлами
            # Входной узел - всегда маршрутизатор
            graph.set_entry_point("router")
            
            # Маршрутизатор определяет следующего агента
            for agent_name in self.available_agents.keys():
                # Условие: если next_agent == agent_name, то перейти к этому агенту
                graph.add_conditional_edges(
                    "router",
                    lambda state, agent=agent_name: state["next_agent"] == agent,
                    {agent_name: "Переход к агенту"},
                )
            
            # После обработки агентом запрос завершается
            for agent_name in self.available_agents.keys():
                graph.add_edge(agent_name, END)
            
            # Создаем и компилируем граф
            return graph.compile()
            
        except Exception as e:
            logger.error(f"Ошибка при настройке LangGraph: {str(e)}")
            return None 