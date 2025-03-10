"""
API-сервер оркестратора для тестирования интеграции.

Этот модуль обеспечивает базовый REST API для взаимодействия с оркестратором.
"""

import asyncio
import os
import signal
import sys
import json
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import uuid
import aiohttp

# Импорт модуля логирования
from multi_agent_system.logger import get_logger

# Импорт клиента Mistral и средств для управления диалогами
from telegram_bot.mistral_client import MistralClient
from telegram_bot.conversation_manager import ConversationManager

# Импорт менеджера агентов
from multi_agent_system.agents.agent_manager import agent_manager

# Настройка логирования для API-сервера
logger = get_logger("api_server", "api_server.log")

# Создание директории для логов, если она не существует
os.makedirs("logs", exist_ok=True)

# Инициализация клиента Mistral и менеджера диалогов
MISTRAL_API_URL = os.environ.get("MISTRAL_API_URL", "http://139.59.241.176:8080")
mistral_client = MistralClient(base_url=MISTRAL_API_URL)
conversation_manager = ConversationManager()

# Проверка, исполняется ли уже этот сервис
def check_and_kill_duplicate():
    try:
        import psutil
        current_pid = os.getpid()
        current_process = psutil.Process(current_pid)
        other_processes_found = False
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            if process.info['pid'] != current_pid and process.info['name'] == current_process.name():
                cmdline = ' '.join(process.info['cmdline']) if process.info['cmdline'] else ''
                if any(arg in cmdline for arg in [__file__, os.path.basename(__file__)]):
                    # Проверяем, не является ли процесс родительским для текущего
                    if process.info['pid'] != os.getppid():
                        logger.warning(f"Найден дубликат процесса с PID {process.info['pid']}, завершаем его")
                        try:
                            process.terminate()
                            other_processes_found = True
                        except psutil.NoSuchProcess:
                            logger.warning(f"Процесс {process.info['pid']} уже завершен")
        return other_processes_found
    except ImportError:
        logger.warning("Модуль psutil не установлен, пропускаем проверку дубликатов")
        return False
    except Exception as e:
        logger.warning(f"Ошибка при проверке дубликатов: {e}")
        return False

# Создаем приложение FastAPI
app = FastAPI(
    title="Orchestrator API",
    description="API for Mistral Multi-Agent System Orchestrator",
    version="0.1.0"
)

# Добавляем middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Словарь для хранения задач
tasks = {}

@app.on_event("startup")
async def startup_event():
    """Выполняется при запуске сервера"""
    # Проверяем наличие дубликатов, но не завершаем работу
    check_and_kill_duplicate()
    logger.info("API-сервер оркестратора запущен")

@app.on_event("shutdown")
async def shutdown_event():
    """Выполняется при остановке сервера"""
    logger.info("API-сервер оркестратора остановлен")

@app.get("/health")
async def health_check():
    """Эндпоинт для проверки здоровья API-сервера"""
    return {"status": "ok"}

@app.get("/agents")
async def list_agents():
    """Возвращает список доступных агентов"""
    result = []
    for agent_id, agent in agent_manager.agents.items():
        result.append({
            "id": agent_id,
            "name": agent.name,
            "description": agent.description,
            "is_default": agent_id == agent_manager.default_agent_id
        })
    return result

@app.post("/tasks")
async def create_task(task_data: Dict[str, Any], background_tasks: BackgroundTasks):
    """Создает новую задачу"""
    task_id = str(uuid.uuid4())
    task_type = task_data.get("type", "default")
    
    task = {
        "id": task_id,
        "type": task_type,
        "status": "created",
        "data": task_data.get("data", {}),
        "result": None
    }
    
    tasks[task_id] = task
    
    # Запускаем обработку задачи в фоне
    background_tasks.add_task(process_task, task_id)
    
    logger.info(f"Создана задача {task_id} типа {task_type}")
    return {"task_id": task_id}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Получает информацию о задаче по ID"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
    
    return tasks[task_id]

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Отменяет задачу по ID"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
    
    tasks[task_id]["status"] = "cancelled"
    logger.info(f"Задача {task_id} отменена")
    
    return {"status": "ok", "message": f"Задача {task_id} отменена"}

@app.post("/message")
async def process_message(message: Dict[str, Any]):
    """Обрабатывает сообщение от клиента"""
    message_type = message.get("type", "direct")
    user_id = message.get("user_id", "unknown")
    session_id = message.get("session_id", "default")
    text = message.get("text", "")
    
    logger.info(f"Получено сообщение типа {message_type} от пользователя {user_id}")
    
    if message_type == "direct":
        # Обрабатываем сообщение с помощью Mistral
        response = await process_with_mistral(user_id, text)
        return {
            "content": response,
            "type": "text",
            "session_id": session_id
        }
    else:
        # Создаем задачу обработки сложного запроса
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "type": "message_process",
            "status": "processing",
            "data": message,
            "result": None
        }
        tasks[task_id] = task
        
        # Имитируем асинхронную обработку
        asyncio.create_task(process_message_task(task_id))
        
        return {
            "task_id": task_id,
            "status": "processing"
        }

@app.post("/process")
async def process_telegram_message(message: Dict[str, Any]):
    """Обрабатывает сообщение от телеграм-бота"""
    user_id = message.get("user_id", "unknown")
    session_id = message.get("session_id", "default")
    text = message.get("text", "")
    
    logger.info(f"Получено сообщение от телеграм-бота, пользователь {user_id}: {text[:50]}...")
    
    try:
        # Проверяем подключение к серверу Mistral
        try:
            # Простая проверка доступности сервера Mistral
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f'{MISTRAL_API_URL}/health',
                        timeout=5
                    ) as response:
                        if response.status != 200:
                            logger.error(f"Сервер Mistral недоступен: {response.status}")
                            return {
                                "content": "Сервер Mistral в настоящий момент недоступен. Пожалуйста, повторите запрос позже.",
                                "type": "text",
                                "session_id": session_id,
                                "error": True
                            }
                except aiohttp.ClientError:
                    # У llama.cpp может не быть эндпоинта /health, пробуем прямой запрос
                    logger.warning("Эндпоинт /health недоступен, пробуем прямой запрос к модели")
        except Exception as e:
            logger.error(f"Ошибка при проверке доступности сервера Mistral: {str(e)}")
            # Продолжаем выполнение, так как у llama.cpp может не быть эндпоинта /health
        
        # Добавляем сообщение пользователя в историю
        conversation_manager.add_user_message(user_id, text)
        
        # Определяем агента для обработки запроса
        agent_id = agent_manager.route_to_agent(text)
        logger.info(f"Запрос пользователя {user_id} направлен агенту: {agent_id}")
        
        # Получаем агента
        agent = agent_manager.get_agent(agent_id)
        if agent is None:
            agent = agent_manager.get_default_agent()
            agent_id = agent.agent_id
            logger.warning(f"Агент {agent_id} не найден, используем агента по умолчанию: {agent.agent_id}")
        
        # Формируем запрос к модели с учетом контекста диалога и системного промпта
        messages = prepare_messages_for_agent(user_id, agent)
        logger.info(f"Подготовлены сообщения для модели: {len(messages)} сообщений")
        
        # Генерируем ответ с помощью модели Mistral
        logger.info(f"Отправка запроса к Mistral для пользователя {user_id}")
        
        try:
            # Используем прямой запрос к модели
            response_text = await mistral_client.generate_response(
                prompt=text,
                temperature=0.7,
                max_tokens=1000
            )
        except Exception as e:
            logger.error(f"Ошибка при запросе к модели: {str(e)}")
            return {
                "content": f"Произошла ошибка при обработке запроса: {str(e)}",
                "type": "text",
                "session_id": session_id,
                "error": True
            }
        
        # Проверяем, не получили ли мы сообщение об ошибке
        if response_text.startswith("Произошла ошибка"):
            logger.error(f"Ошибка от Mistral: {response_text}")
            return {
                "content": "Не удалось получить ответ от модели. Пожалуйста, попробуйте еще раз или упростите запрос.",
                "type": "text",
                "session_id": session_id,
                "error": True
            }
        
        # Сохраняем ответ ассистента в историю
        conversation_manager.add_assistant_message(user_id, response_text)
        
        # Логируем успешную обработку
        logger.info(f"Успешно обработано сообщение от пользователя {user_id} агентом {agent_id}")
        
        # Возвращаем ответ
        return {
            "content": response_text,
            "type": "text",
            "session_id": session_id,
            "agent": agent_id
        }
        
    except Exception as e:
        # В случае ошибки логируем и возвращаем сообщение об ошибке
        logger.exception(f"Ошибка при обработке сообщения от пользователя {user_id}: {str(e)}")
        return {
            "content": f"Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
            "type": "text",
            "session_id": session_id,
            "error": True
        }

def prepare_messages_for_agent(user_id: int, agent) -> List[Dict[str, str]]:
    """
    Формирует список сообщений для модели с учетом системного промпта агента и истории диалога
    
    Args:
        user_id: ID пользователя
        agent: Объект агента
        
    Returns:
        List[Dict[str, str]]: Список сообщений для отправки модели
    """
    # Получаем историю сообщений пользователя
    history = conversation_manager.get_messages(user_id)
    
    # Добавляем системный промпт в начало
    system_prompt = agent.system_prompt
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Добавляем историю сообщений (последние 10 сообщений, чтобы не перегружать контекст)
    messages.extend(history[-10:])
    
    return messages

async def process_with_mistral(user_id: str, text: str) -> str:
    """
    Обрабатывает сообщение с помощью модели Mistral
    
    Args:
        user_id: ID пользователя
        text: Текст запроса
        
    Returns:
        str: Ответ модели
    """
    try:
        # Добавляем сообщение в историю
        conversation_manager.add_user_message(user_id, text)
        
        # Определяем агента и формируем сообщения
        agent_id = agent_manager.route_to_agent(text)
        agent = agent_manager.get_agent(agent_id)
        
        if agent is None:
            agent = agent_manager.get_default_agent()
            logger.warning(f"Агент {agent_id} не найден, используем агента по умолчанию: {agent.agent_id}")
        
        messages = prepare_messages_for_agent(user_id, agent)
        
        # Запрашиваем ответ от модели
        response = await mistral_client.generate_chat_response(messages)
        
        # Сохраняем ответ в историю
        conversation_manager.add_assistant_message(user_id, response)
        
        return response
    except Exception as e:
        logger.error(f"Ошибка при обработке с помощью Mistral: {str(e)}")
        return f"Произошла ошибка при обработке вашего запроса: {str(e)}"

async def process_task(task_id: str):
    """Обрабатывает задачу в фоновом режиме"""
    if task_id not in tasks:
        logger.error(f"Задача {task_id} не найдена для обработки")
        return
    
    task = tasks[task_id]
    
    try:
        # Меняем статус на "processing"
        task["status"] = "processing"
        
        # Имитируем обработку
        await asyncio.sleep(2)
        
        # В реальном приложении здесь будет логика обработки задачи
        task["result"] = {"message": "Задача успешно обработана"}
        task["status"] = "completed"
        
        logger.info(f"Задача {task_id} успешно обработана")
    except Exception as e:
        task["status"] = "failed"
        task["result"] = {"error": str(e)}
        logger.error(f"Ошибка при обработке задачи {task_id}: {e}")

async def process_message_task(task_id: str):
    """Обрабатывает задачу обработки сообщения"""
    if task_id not in tasks:
        logger.error(f"Задача {task_id} не найдена для обработки")
        return
    
    task = tasks[task_id]
    message = task["data"]
    
    try:
        # Обработка сообщения с помощью Mistral
        user_id = message.get("user_id", "unknown")
        text = message.get("text", "")
        
        response = await process_with_mistral(user_id, text)
        
        task["result"] = {
            "content": response,
            "type": "text"
        }
        task["status"] = "completed"
        
        logger.info(f"Задача обработки сообщения {task_id} выполнена успешно")
    except Exception as e:
        task["status"] = "failed"
        task["result"] = {"error": str(e)}
        logger.error(f"Ошибка при обработке задачи сообщения {task_id}: {e}")

def run_server():
    """Запускает сервер FastAPI с использованием Uvicorn"""
    try:
        # Получаем порт из переменной окружения или используем порт по умолчанию
        port = int(os.environ.get("API_SERVER_PORT", 8002))
        
        # Запускаем сервер с Uvicorn
        uvicorn.run(
            "multi_agent_system.api_server:app",
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Не удалось запустить API-сервер: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Запускаем сервер
    run_server() 