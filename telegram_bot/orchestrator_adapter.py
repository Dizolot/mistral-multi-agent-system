"""
Адаптер для связи телеграм-бота с оркестратором.

Этот модуль создает связь между существующим телеграм-ботом 
и оркестратором мульти-агентной системы.
"""

import logging
import aiohttp
import asyncio
import requests
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from multi_agent_system.async_utils import run_async_safely

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OrchestratorAdapter:
    """
    Адаптер для связи телеграм-бота с оркестратором.
    
    Обеспечивает асинхронное взаимодействие между телеграм-ботом
    и оркестратором мульти-агентной системы.
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
        self.logger = logging.getLogger(__name__)
        logger.info(f"Инициализирован адаптер оркестратора с базовым URL: {base_url}")
    
    async def initialize(self):
        """
        Инициализирует сессию для HTTP-запросов.
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()
            logger.info("Создана сессия для HTTP-запросов")
        return True
    
    def initialize_sync(self):
        """
        Синхронная версия инициализации. Проверяет доступность оркестратора.
        
        Returns:
            bool: True, если оркестратор доступен
        """
        logger.info(f"Проверка доступности оркестратора: {self.base_url}")
        try:
            # Выполняем GET-запрос для проверки доступности оркестратора
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("Оркестратор доступен")
                return True
            else:
                logger.error(f"Оркестратор недоступен. Статус: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке доступности оркестратора: {e}")
            return False
    
    async def close(self):
        """
        Закрывает сессию HTTP-запросов.
        """
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Сессия HTTP-запросов закрыта")
    
    async def process_message(self, user_id: str, message_text: str) -> str:
        """
        Обрабатывает сообщение через оркестратор
        
        Args:
            user_id: ID пользователя
            message_text: Текст сообщения
            
        Returns:
            str: Ответ от оркестратора
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Используем контекстный менеджер для запроса
            async with self.session.post(
                f"{self.base_url}/process",
                json={
                    "user_id": user_id,
                    "text": message_text,
                    "session_id": f"telegram_{user_id}"
                },
                timeout=aiohttp.ClientTimeout(total=180)  # 3 минуты таймаут
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("content", "Ошибка: нет ответа в результате")
                else:
                    error_text = await response.text()
                    self.logger.error(f"Ошибка от оркестратора: {error_text}")
                    return f"Ошибка при обработке запроса: {error_text}"
                    
        except asyncio.TimeoutError:
            self.logger.error("Таймаут при ожидании ответа от оркестратора")
            return "Превышено время ожидания ответа. Пожалуйста, попробуйте позже."
            
        except aiohttp.ClientError as e:
            self.logger.error(f"Ошибка при подключении к оркестратору: {str(e)}")
            return f"Ошибка при подключении к серверу: {str(e)}"
            
        except Exception as e:
            self.logger.error(f"Ошибка при отправке запроса к оркестратору: {str(e)}")
            return f"Ошибка при обработке запроса: {str(e)}"
        
# Создаем класс для прямого взаимодействия с моделью через mistral_client
# в случае, если оркестратор недоступен
class FallbackHandler:
    """
    Обработчик для прямого взаимодействия с моделью в случае,
    если оркестратор недоступен.
    """
    
    def __init__(self, mistral_client):
        """
        Инициализирует обработчик.
        
        Args:
            mistral_client: Клиент для взаимодействия с моделью Mistral
        """
        self.mistral_client = mistral_client
        logger.info("Инициализирован запасной обработчик для прямого взаимодействия с моделью")
    
    async def process_message(self, user_id: str, message_text: str, status_callback: Optional[Callable[[str], Awaitable[None]]] = None) -> str:
        """
        Обрабатывает сообщение от пользователя напрямую через модель.
        
        Args:
            user_id: Идентификатор пользователя
            message_text: Текст сообщения
            status_callback: Функция обратного вызова для обновления статуса обработки
            
        Returns:
            str: Ответ от модели
        """
        logger.info(f"Прямая обработка сообщения для пользователя {user_id} через модель")
        
        # Таймеры для обновления статуса
        start_time = time.time()
        status_update_interval = 10  # секунды между обновлениями статуса
        last_status_update = start_time
        
        # Максимальное время выполнения запроса (10 минут)
        max_execution_time = 600
        
        # Запускаем отдельную задачу для обновления статуса
        status_updater_task = None
        
        if status_callback:
            # Отправляем начальный статус
            await status_callback("🔄 Подготовка запроса к модели...")
            
            # Функция для периодического обновления статуса
            async def update_status():
                nonlocal last_status_update
                elapsed_time = 0
                
                while True:
                    current_time = time.time()
                    elapsed_time = int(current_time - start_time)
                    
                    # Проверяем, не превышено ли максимальное время выполнения
                    if elapsed_time > max_execution_time:
                        logger.warning(f"Запрос для пользователя {user_id} выполняется слишком долго (> {max_execution_time} сек)")
                        await status_callback(f"⚠️ Запрос выполняется слишком долго ({elapsed_time} сек)... Ожидание ответа от модели.")
                        await asyncio.sleep(10)  # Обновляем реже при длительном ожидании
                        continue
                        
                    if current_time - last_status_update >= status_update_interval:
                        # Показываем реальное время ожидания
                        await status_callback(f"⏳ Ожидание ответа от модели... ({elapsed_time} сек)")
                        last_status_update = current_time
                    
                    await asyncio.sleep(1)  # проверяем каждую секунду
            
            # Запускаем обновления статуса
            status_updater_task = asyncio.create_task(update_status())
        
        try:
            # Отправляем начальный статус
            if status_callback:
                await status_callback(f"🔄 Отправка запроса к модели...")
                
            # Создаем задачу для запроса к модели с таймаутом
            request_task = asyncio.create_task(
                self.mistral_client.generate_response(message_text)
            )
            
            # Ожидаем завершения запроса с максимальным временем выполнения
            try:
                response = await asyncio.wait_for(request_task, timeout=max_execution_time)
                
                if status_callback:
                    await status_callback(f"✅ Ответ получен, обработка данных...")
                    
                logger.info(f"Получен ответ от модели для пользователя {user_id}")
                return response
                
            except asyncio.TimeoutError:
                logger.error(f"Превышено максимальное время выполнения запроса ({max_execution_time} сек)")
                # Отменяем запрос
                if not request_task.done():
                    request_task.cancel()
                    try:
                        await request_task
                    except asyncio.CancelledError:
                        pass
                return f"Запрос выполнялся слишком долго (более {max_execution_time} сек) и был отменен. Пожалуйста, упростите запрос или попробуйте позже."
                
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {str(e)}")
            return f"Произошла ошибка: {str(e)}"
        
        finally:
            # Отменяем задачу обновления статуса, если она была запущена
            if status_updater_task:
                status_updater_task.cancel()
                try:
                    await status_updater_task
                except asyncio.CancelledError:
                    pass  # ожидаемая отмена 