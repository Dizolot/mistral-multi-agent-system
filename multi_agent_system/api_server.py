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

# Импорт маршрутизатора LangChain и агентов
from multi_agent_system.orchestrator.langchain_router import LangChainRouter
from multi_agent_system.agents.general_agent import GeneralAgent
from multi_agent_system.agents.programming_agent import ProgrammingAgent

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

# Инициализация маршрутизатора LangChain и агентов
router = LangChainRouter(mistral_api_url=MISTRAL_API_URL)

# Инициализация агентов
general_agent = GeneralAgent(mistral_api_url=MISTRAL_API_URL)
programming_agent = ProgrammingAgent(mistral_api_url=MISTRAL_API_URL)

# Регистрация агентов в маршрутизаторе
router.register_agent(
    name=general_agent.name,
    description=general_agent.description,
    handler=general_agent.process
)

router.register_agent(
    name=programming_agent.name,
    description=programming_agent.description,
    handler=programming_agent.process
)

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
    logger.info(f"LangChain маршрутизатор: {len(router.available_agents)} агентов зарегистрировано")

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
    """Возвращает список доступных агентов из маршрутизатора LangChain"""
    result = []
    for agent_name, agent_details in router.available_agents.items():
        result.append({
            "name": agent_name,
            "description": agent_details.get("description", ""),
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
    """Обрабатывает сообщение от телеграм-бота через систему маршрутизации LangChain"""
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
        
        # Получаем историю сообщений пользователя
        chat_history = get_chat_history_for_langchain(user_id)
        
        # Используем маршрутизатор LangChain для обработки запроса
        logger.info(f"Маршрутизация запроса пользователя {user_id} с использованием LangChain")
        
        # Начинаем процесс генерации ответа
        result = router.route_request(
            user_input=text, 
            chat_history=chat_history,
            user_id=user_id,
            session_id=session_id
        )
        
        # Получаем имя использованного агента и ответ
        agent_name = result.get("agent", "Unknown")
        response_text = result.get("response", "Извините, не удалось обработать ваш запрос.")
        status = result.get("status", "error")
        processing_time = result.get("processing_time", 0)
        
        logger.info(f"Запрос пользователя {user_id} обработан агентом {agent_name}")
        
        # Добавляем ответ в историю диалога
        conversation_manager.add_assistant_message(user_id, response_text)
        
        # Формируем и возвращаем результат
        return {
            "content": response_text,
            "type": "text",
            "session_id": session_id,
            "agent": agent_name,
            "status": status,
            "processing_time": processing_time
        }
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {str(e)}")
        return {
            "content": f"Произошла ошибка при обработке запроса: {str(e)}. Пожалуйста, повторите попытку позже.",
            "type": "text",
            "session_id": session_id,
            "error": True
        }

def get_chat_history_for_langchain(user_id: str) -> List[Dict[str, str]]:
    """
    Преобразует историю диалога пользователя в формат, подходящий для LangChain.
    
    Args:
        user_id: Идентификатор пользователя
        
    Returns:
        List[Dict[str, str]]: История диалога в формате LangChain
    """
    messages = []
    
    # Получаем историю диалога пользователя
    history = conversation_manager.get_conversation_history(user_id)
    
    # Преобразуем историю в формат LangChain
    if history:
        for message in history:
            if message["role"] == "user":
                messages.append({"type": "human", "content": message["content"]})
            elif message["role"] == "assistant":
                messages.append({"type": "ai", "content": message["content"]})
    
    return messages

def prepare_messages_for_agent(user_id: int, agent) -> List[Dict[str, str]]:
    """
    Подготавливает сообщения для отправки агенту с учетом контекста диалога.
    
    Args:
        user_id: Идентификатор пользователя
        agent: Объект агента, который будет обрабатывать запрос
        
    Returns:
        List[Dict[str, str]]: Список сообщений в формате для модели
    """
    # Получаем историю диалога пользователя
    history = conversation_manager.get_conversation_history(user_id)
    
    # Формируем список сообщений для модели
    messages = []
    
    # Добавляем системный промпт агента
    messages.append({
        "role": "system",
        "content": agent.system_prompt
    })
    
    # Добавляем историю диалога
    for message in history:
        messages.append(message)
        
    logger.debug(f"Подготовлено {len(messages)} сообщений для агента")
    
    return messages

async def process_with_mistral(user_id: str, text: str) -> str:
    """
    Обрабатывает запрос с помощью Mistral API.
    
    Args:
        user_id: Идентификатор пользователя
        text: Текст запроса
        
    Returns:
        str: Ответ модели
    """
    try:
        # Сохраняем сообщение пользователя
        conversation_manager.add_user_message(user_id, text)
        
        # Формируем историю диалога
        history = conversation_manager.get_conversation_history(user_id)
        
        # Формируем промпт для модели
        prompt = "".join([f"{msg['role']}: {msg['content']}\n" for msg in history])
        prompt += "assistant: "
        
        # Отправляем запрос к модели
        response = await mistral_client.generate_response(
            prompt=prompt,
        )
        
        # Сохраняем ответ модели
        conversation_manager.add_assistant_message(user_id, response)
        
        return response
    except Exception as e:
        logger.error(f"Ошибка при обращении к Mistral API: {str(e)}")
        return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"

async def process_task(task_id: str):
    """
    Обрабатывает задачу в фоне.
    
    Args:
        task_id: Идентификатор задачи
    """
    if task_id not in tasks:
        logger.error(f"Задача {task_id} не найдена")
        return
    
    logger.info(f"Начата обработка задачи {task_id}")
    
    task = tasks[task_id]
    task["status"] = "processing"
    
    try:
        # Имитация асинхронной обработки
        await asyncio.sleep(5)
        
        # Обновляем статус задачи
        task["status"] = "completed"
        task["result"] = {"message": "Задача успешно выполнена"}
        
        logger.info(f"Задача {task_id} успешно выполнена")
    except Exception as e:
        logger.error(f"Ошибка при обработке задачи {task_id}: {str(e)}")
        task["status"] = "failed"
        task["result"] = {"error": str(e)}

async def process_message_task(task_id: str):
    """
    Обрабатывает задачу обработки сообщения.
    
    Args:
        task_id: Идентификатор задачи
    """
    if task_id not in tasks:
        logger.error(f"Задача {task_id} не найдена")
        return
    
    task = tasks[task_id]
    message = task["data"]
    
    try:
        # Выполняем обработку сообщения
        user_id = message.get("user_id", "unknown")
        session_id = message.get("session_id", "default")
        text = message.get("text", "")
        
        # Добавляем статусы к задаче для отслеживания прогресса
        task["status_messages"] = ["Начало обработки сообщения"]
        
        # Имитация обработки
        await asyncio.sleep(2)
        task["status_messages"].append("Анализ запроса")
        
        await asyncio.sleep(3)
        task["status_messages"].append("Генерация ответа")
        
        # Обрабатываем запрос с помощью LangChain маршрутизатора
        chat_history = get_chat_history_for_langchain(user_id)
        result = router.route_request(
            user_input=text, 
            chat_history=chat_history,
            user_id=user_id,
            session_id=session_id
        )
        
        # Добавляем ответ к задаче
        task["result"] = result
        task["status"] = "completed"
        task["status_messages"].append("Обработка завершена")
        
        logger.info(f"Задача {task_id} успешно выполнена")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}")
        task["status"] = "failed"
        task["result"] = {"error": str(e)}
        task["status_messages"].append(f"Ошибка: {str(e)}")

def run_server():
    """Запускает сервер оркестратора"""
    # Проверяем, не запущен ли уже сервер
    if check_and_kill_duplicate():
        logger.info("Найдены запущенные экземпляры сервера, они будут завершены")
    
    # Настраиваем обработчик сигналов для корректного завершения
    def handle_exit(signum, frame):
        logger.info(f"Получен сигнал {signum}, завершаем работу")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_exit)
    
    # Запускаем сервер
    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    run_server() 