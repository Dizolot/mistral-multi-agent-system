"""
Клиент для взаимодействия с оркестратором.

Этот модуль обеспечивает связь с API оркестратора для отправки
запросов и получения результатов.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

class OrchestratorClient:
    """
    Клиент для взаимодействия с оркестратором.
    
    Обеспечивает связь с API оркестратора для отправки
    запросов и получения результатов.
    """
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Инициализирует клиент оркестратора.
        
        Args:
            api_url: URL API оркестратора
        """
        self.api_url = api_url
        self.session = None
        
        logger.info(f"OrchestratorClient инициализирован с URL: {api_url}")
    
    async def initialize(self):
        """Инициализирует клиент."""
        logger.info("Инициализация OrchestratorClient...")
        self.session = aiohttp.ClientSession()
        
        # Проверяем доступность оркестратора
        try:
            async with self.session.get(f"{self.api_url}/health") as response:
                if response.status == 200:
                    logger.info("Оркестратор доступен")
                    return True
                else:
                    logger.error(f"Оркестратор недоступен. Статус: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при проверке доступности оркестратора: {e}")
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Отправляет сообщение оркестратору.
        
        Args:
            message: Сообщение для отправки
        
        Returns:
            Optional[Dict[str, Any]]: Ответ от оркестратора или None в случае ошибки
        """
        if not self.session:
            logger.error("Сессия не инициализирована. Вызовите initialize() перед отправкой сообщений.")
            return None
        
        try:
            logger.info(f"Отправка сообщения оркестратору: {message}")
            
            async with self.session.post(
                f"{self.api_url}/process",
                json=message,
                timeout=60
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Получен ответ от оркестратора: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка при отправке сообщения оркестратору: {response.status}, {error_text}")
                    return None
        except asyncio.TimeoutError:
            logger.error("Таймаут при отправке сообщения оркестратору")
            return None
        except Exception as e:
            logger.exception(f"Ошибка при отправке сообщения оркестратору: {e}")
            return None
    
    async def create_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """
        Создает задачу в оркестраторе.
        
        Args:
            task_data: Данные задачи
        
        Returns:
            Optional[str]: ID созданной задачи или None в случае ошибки
        """
        if not self.session:
            logger.error("Сессия не инициализирована. Вызовите initialize() перед созданием задач.")
            return None
        
        try:
            logger.info(f"Создание задачи в оркестраторе: {task_data}")
            
            async with self.session.post(
                f"{self.api_url}/tasks",
                json=task_data,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    task_id = result.get("task_id")
                    logger.info(f"Создана задача с ID: {task_id}")
                    return task_id
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка при создании задачи: {response.status}, {error_text}")
                    return None
        except Exception as e:
            logger.exception(f"Ошибка при создании задачи: {e}")
            return None
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает статус задачи из оркестратора.
        
        Args:
            task_id: ID задачи
        
        Returns:
            Optional[Dict[str, Any]]: Статус задачи или None в случае ошибки
        """
        if not self.session:
            logger.error("Сессия не инициализирована. Вызовите initialize() перед получением статуса задачи.")
            return None
        
        try:
            logger.info(f"Получение статуса задачи {task_id}")
            
            async with self.session.get(
                f"{self.api_url}/tasks/{task_id}",
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Получен статус задачи {task_id}: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка при получении статуса задачи: {response.status}, {error_text}")
                    return None
        except Exception as e:
            logger.exception(f"Ошибка при получении статуса задачи: {e}")
            return None
    
    async def wait_for_task_completion(self, task_id: str, timeout: int = 300, poll_interval: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Ожидает завершения задачи.
        
        Args:
            task_id: ID задачи
            timeout: Таймаут ожидания в секундах
            poll_interval: Интервал опроса в секундах
        
        Returns:
            Optional[Dict[str, Any]]: Результат задачи или None в случае ошибки или таймаута
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            task_status = await self.get_task_status(task_id)
            
            if not task_status:
                logger.error(f"Не удалось получить статус задачи {task_id}")
                return None
            
            status = task_status.get("status")
            
            if status == "completed":
                logger.info(f"Задача {task_id} завершена успешно")
                return task_status.get("result")
            
            if status == "failed":
                logger.error(f"Задача {task_id} завершена с ошибкой")
                return task_status.get("result")
            
            if status == "cancelled":
                logger.warning(f"Задача {task_id} отменена")
                return None
            
            # Ждем перед следующим опросом
            await asyncio.sleep(poll_interval)
        
        logger.error(f"Таймаут ожидания завершения задачи {task_id}")
        return None
    
    async def close(self):
        """Закрывает сессию клиента."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Сессия OrchestratorClient закрыта") 