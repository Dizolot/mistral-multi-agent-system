"""
Модуль для регистрации агентов в маршрутизаторе LangChain.

Этот модуль создает и регистрирует агентов, которые будут использоваться
в мульти-агентной системе для обработки запросов пользователей.
"""

import os
from typing import Dict, Any, List, Optional, Callable

# Импортируем модуль async_utils для поддержки вложенных циклов событий
from multi_agent_system.async_utils import get_or_create_event_loop, sync_to_async

from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain_core.messages import SystemMessage

from multi_agent_system.logger import get_logger
from multi_agent_system.orchestrator.langchain_router import LangChainRouter
from telegram_bot.mistral_client import MistralClient

logger = get_logger(__name__)

def create_general_agent(mistral_client: MistralClient) -> Callable:
    """
    Создает общего ассистента для широкого спектра вопросов.
    
    Args:
        mistral_client: Клиент для работы с API Mistral
        
    Returns:
        Callable: Функция-обработчик для агента
    """
    system_message = """
    Вы — универсальный ассистент Mistral, способный отвечать на широкий спектр вопросов.
    Ваши ответы должны быть информативными, полезными и дружелюбными.
    Если вы не знаете ответ, честно признайтесь в этом, но предложите альтернативную информацию.
    """
    
    def general_agent_handler(query: str, chat_history=None) -> str:
        """Обработчик запросов для общего ассистента"""
        try:
            # Формируем контекст из системного сообщения и истории чата
            context = [{"role": "system", "content": system_message}]
            
            # Добавляем историю чата, если она есть
            if chat_history and isinstance(chat_history, list):
                context.extend(chat_history)
            
            # Добавляем текущий запрос пользователя
            context.append({"role": "user", "content": query})
            
            # Получаем ответ от модели Mistral
            response = mistral_client.generate_text(context=context)
            
            return response
        except Exception as e:
            logger.error(f"Ошибка в general_agent_handler: {str(e)}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    return general_agent_handler

def create_programming_agent(mistral_client: MistralClient) -> Callable:
    """
    Создает ассистента для помощи с программированием.
    
    Args:
        mistral_client: Клиент для работы с API Mistral
        
    Returns:
        Callable: Функция-обработчик для агента
    """
    system_message = """
    Вы — специализированный ассистент по программированию.
    Ваша задача — помогать с написанием, отладкой и объяснением кода.
    Предоставляйте понятные объяснения, примеры кода и рекомендации по лучшим практикам.
    Если код содержит ошибки, укажите на них и предложите исправления.
    """
    
    def programming_agent_handler(query: str, chat_history=None) -> str:
        """Обработчик запросов для программного ассистента"""
        try:
            # Формируем контекст из системного сообщения и истории чата
            context = [{"role": "system", "content": system_message}]
            
            # Добавляем историю чата, если она есть
            if chat_history and isinstance(chat_history, list):
                context.extend(chat_history)
            
            # Добавляем текущий запрос пользователя
            context.append({"role": "user", "content": query})
            
            # Получаем ответ от модели Mistral
            response = mistral_client.generate_text(context=context)
            
            return response
        except Exception as e:
            logger.error(f"Ошибка в programming_agent_handler: {str(e)}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    return programming_agent_handler

def create_science_agent(mistral_client: MistralClient) -> Callable:
    """
    Создает ассистента для научных и математических вопросов.
    
    Args:
        mistral_client: Клиент для работы с API Mistral
        
    Returns:
        Callable: Функция-обработчик для агента
    """
    system_message = """
    Вы — специализированный ассистент по научным и математическим вопросам.
    Ваша задача — предоставлять точные ответы на вопросы по математике, физике,
    химии, биологии и другим естественным наукам.
    Используйте формулы и научные принципы для объяснения концепций.
    Если вопрос выходит за рамки вашей компетенции, укажите это и предложите
    обратиться к другому специалисту.
    """
    
    def science_agent_handler(query: str, chat_history=None) -> str:
        """Обработчик запросов для научного ассистента"""
        try:
            # Формируем контекст из системного сообщения и истории чата
            context = [{"role": "system", "content": system_message}]
            
            # Добавляем историю чата, если она есть
            if chat_history and isinstance(chat_history, list):
                context.extend(chat_history)
            
            # Добавляем текущий запрос пользователя
            context.append({"role": "user", "content": query})
            
            # Получаем ответ от модели Mistral
            response = mistral_client.generate_text(context=context)
            
            return response
        except Exception as e:
            logger.error(f"Ошибка в science_agent_handler: {str(e)}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    return science_agent_handler

def register_agents(router: LangChainRouter, mistral_client: MistralClient) -> None:
    """
    Регистрирует всех агентов в маршрутизаторе.
    
    Args:
        router: Экземпляр маршрутизатора LangChain
        mistral_client: Клиент для работы с API Mistral
    """
    # Создаем обработчики для каждого типа агентов
    general_handler = create_general_agent(mistral_client)
    programming_handler = create_programming_agent(mistral_client)
    science_handler = create_science_agent(mistral_client)
    
    # Регистрируем агентов в маршрутизаторе
    router.register_agent(
        name="general",
        description="Общий ассистент, который может отвечать на широкий спектр вопросов повседневной жизни, давать советы и информацию на общие темы.",
        handler=general_handler
    )
    
    router.register_agent(
        name="programming",
        description="Программный ассистент, специализирующийся на вопросах программирования, разработки, написания и отладки кода.",
        handler=programming_handler
    )
    
    router.register_agent(
        name="science",
        description="Научный ассистент, специализирующийся на вопросах математики, физики, химии, биологии и других естественных наук.",
        handler=science_handler
    )
    
    logger.info(f"Зарегистрировано агентов: {len(router.available_agents)}")
    for agent_name in router.available_agents:
        logger.info(f"  - {agent_name}: {router.available_agents[agent_name]['description'][:50]}...") 