#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для запуска непрерывной мульти-агентной системы улучшения кода AI-секретаря.
"""

import os
import sys
import asyncio
import logging
import argparse
import signal
import json
from pathlib import Path
from datetime import datetime
import traceback
import time

# Настройка логирования
def setup_logging(log_dir="logs"):
    """Настройка логирования с ротацией файлов."""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True, parents=True)
    
    log_file = log_path / f"multi_agent_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Логирование настроено в {log_file}")
    return logger

# Глобальные переменные для управления работой системы
is_running = True
restart_counter = 0
max_restarts = 5
restart_delay = 60  # Задержка перед перезапуском в секундах

# Обработчики сигналов
def handle_shutdown(signum, frame):
    """Обработчик сигналов для корректного завершения работы."""
    global is_running
    if signum == signal.SIGINT:
        logging.info("Получен сигнал SIGINT (Ctrl+C). Завершаю работу...")
    elif signum == signal.SIGTERM:
        logging.info("Получен сигнал SIGTERM. Завершаю работу...")
    is_running = False

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

async def load_config(config_path="config.json"):
    """Загрузка конфигурации из файла."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(f"Ошибка при загрузке конфигурации: {e}")
        return None

async def create_task_for_analysis(secretary_code_path="src/agents/secretary_agent.py"):
    """Создание задачи анализа кода для добавления в очередь."""
    return {
        "type": "analysis",
        "description": f"Плановый анализ кода секретаря ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        "target": secretary_code_path,
        "file_path": secretary_code_path,
        "priority": "normal",
        "scheduled": True,
        "created_at": datetime.now().isoformat()
    }

async def main_loop():
    """Основной цикл работы системы с обработкой ошибок."""
    global restart_counter, is_running
    
    # Настройка логирования
    logger = setup_logging()
    logger.info(f"Запуск непрерывной системы улучшения (попытка {restart_counter + 1})")
    
    try:
        # Загрузка конфигурации
        config = await load_config()
        if not config:
            logger.error("Не удалось загрузить конфигурацию")
            return False
        
        # Проверка переменных окружения
        telegram_token = os.getenv("TELEGRAM_TOKEN")
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        
        if not telegram_token or not admin_chat_id:
            logger.error("Не указаны TELEGRAM_TOKEN или ADMIN_CHAT_ID в переменных окружения")
            return False
            
        logger.info(f"Найден TELEGRAM_TOKEN длиной {len(telegram_token)} символов")
        logger.info(f"Найден ADMIN_CHAT_ID: {admin_chat_id}")
        
        # Импорт необходимых компонентов здесь, чтобы избежать циклических зависимостей
        from src.agents.chat_interaction.chat_manager import ChatManager
        from src.reporting.telegram_reporter import TelegramReporter
        from src.agent_orchestrator import AgentOrchestrator
        from src.core.memory_system.memory_manager import MemoryManager
        from src.core.memory_system.embedding_provider import MistralEmbeddingProvider
        
        # Инициализация компонентов системы
        logger.info("Инициализация компонентов системы")
        
        # Инициализация TelegramReporter (передаем токен и чат_id напрямую, а не весь объект config)
        telegram_reporter = TelegramReporter(telegram_token, admin_chat_id)
        
        # Директории для хранения данных
        Path("data/agent_chat").mkdir(parents=True, exist_ok=True)
        Path("data/monitoring").mkdir(parents=True, exist_ok=True)
        Path("data/memory").mkdir(parents=True, exist_ok=True)
        
        # Инициализация чат-менеджера
        chat_manager = ChatManager(config=config)
        await chat_manager.initialize()
        
        # Инициализация менеджера памяти
        embedding_provider = MistralEmbeddingProvider()
        memory_manager = MemoryManager(
            storage_dir="data/memory",
            embedding_provider=embedding_provider
        )
        
        # Инициализация оркестратора агентов
        orchestrator = AgentOrchestrator(memory_manager, config)
        
        # Убедимся, что файл секретаря существует
        secretary_path = config.get("code_analysis", {}).get("secretary_path", "src/agents/secretary_agent.py")
        secretary_file = Path(secretary_path)
        
        if not secretary_file.exists():
            logger.warning(f"Файл секретаря {secretary_path} не найден. Проверьте путь в конфигурации.")
            
            # Находим существующий файл, если путь неверный
            alternate_paths = [
                "src/agents/secretary_agent.py",
                "src/agents/secretary_agent/secretary_agent.py",
                "multi_agent_system/agents/secretary_agent.py"
            ]
            
            for alt_path in alternate_paths:
                if Path(alt_path).exists():
                    secretary_path = alt_path
                    logger.info(f"Найден альтернативный путь к файлу секретаря: {secretary_path}")
                    break
            
            # Обновляем конфигурацию
            if "code_analysis" not in config:
                config["code_analysis"] = {}
            config["code_analysis"]["secretary_path"] = secretary_path
        
        # Запуск компонентов
        logger.info("Запуск компонентов системы")
        
        # Запуск чат-менеджера уже выполнен в initialize()
        # await chat_manager.start()  # Этого метода нет в классе ChatManager из src
        
        # Запуск оркестратора агентов
        await orchestrator.start()
        
        # Регистрация агентов в чат-менеджере
        for agent_id, agent in orchestrator.agents.items():
            agent_name = agent.__class__.__name__
            agent_role = {
                'product': 'Управление требованиями',
                'developer': 'Разработка улучшений',
                'tester': 'Тестирование изменений',
                'deployer': 'Внедрение улучшений'
            }.get(agent_id, 'Неопределена')
            
            agent_info = {
                "name": agent_name,
                "role": agent_role,
                "description": f"Агент {agent_name} для {agent_role}"
            }
            
            await chat_manager.register_agent(agent_id, agent_info)
        
        # Отправка приветственного сообщения
        start_message = (
            "🚀 Непрерывная система улучшения AI-секретаря запущена!\n\n"
            f"📅 Дата запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"⚙️ Режим работы: Круглосуточный мониторинг и улучшение\n\n"
            "Доступные команды:\n"
            "- /status - Получить текущий статус системы\n"
            "- /report - Запросить отчет о работе системы\n"
            "- /improve - Запустить процесс улучшения секретаря\n"
            "- /stop - Остановить систему"
        )
        
        await telegram_reporter.send_message(admin_chat_id, start_message)
        
        # Создаем и добавляем первую задачу для анализа кода секретаря
        initial_task = await create_task_for_analysis(
            config.get("code_analysis", {}).get("secretary_path", "src/agents/secretary_agent.py")
        )
        initial_task["priority"] = "high"  # Устанавливаем высокий приоритет для первой задачи
        
        await orchestrator.add_task(initial_task)
        
        # Сбрасываем счетчик перезапусков
        restart_counter = 0
        
        # Основной цикл работы системы
        logger.info("Система запущена и работает в непрерывном режиме")
        
        # Время последнего анализа кода
        last_analysis_time = datetime.now()
        analysis_interval = config.get("code_analysis", {}).get("interval", 86400)  # 24 часа по умолчанию
        
        while is_running:
            try:
                # Проверяем, нужно ли запустить новый анализ кода
                current_time = datetime.now()
                time_since_last_analysis = (current_time - last_analysis_time).total_seconds()
                
                if time_since_last_analysis >= analysis_interval:
                    logger.info("Запуск периодического анализа кода")
                    
                    # Создаем новую задачу анализа
                    analysis_task = await create_task_for_analysis(
                        config.get("code_analysis", {}).get("secretary_path", "src/agents/secretary_agent.py")
                    )
                    
                    # Добавляем задачу в очередь
                    await orchestrator.add_task(analysis_task)
                    
                    # Отправляем уведомление
                    await telegram_reporter.send_message(
                        admin_chat_id,
                        "🔄 Запущен периодический анализ кода AI-секретаря"
                    )
                    
                    # Обновляем время последнего анализа
                    last_analysis_time = current_time
                
                # Получаем статус системы для логирования
                status = await orchestrator.get_status()
                logger.debug(f"Статус системы: {status}")
                
                # Проверяем очередь задач - если она пуста, можно запустить анализ раньше срока
                if orchestrator.task_queue.empty() and time_since_last_analysis >= 3600:  # Если прошел хотя бы час
                    logger.info("Очередь задач пуста, запускаем внеплановый анализ кода")
                    
                    # Создаем новую задачу анализа
                    analysis_task = await create_task_for_analysis(
                        config.get("code_analysis", {}).get("secretary_path", "src/agents/secretary_agent.py")
                    )
                    analysis_task["description"] = "Внеплановый анализ кода AI-секретаря (свободная очередь)"
                    
                    # Добавляем задачу в очередь
                    await orchestrator.add_task(analysis_task)
                    
                    # Обновляем время последнего анализа
                    last_analysis_time = current_time
                
                # Ожидаем перед следующей проверкой
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Основной цикл отменен")
                break
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}", exc_info=True)
                await asyncio.sleep(10)
        
        logger.info("Основной цикл работы системы завершен")
        
        # Корректное завершение работы компонентов
        logger.info("Завершение работы компонентов системы")
        
        # Останавливаем оркестратор агентов
        await orchestrator.stop()
        
        # Останавливаем чат-менеджер - этого метода нет в классе ChatManager из src
        # await chat_manager.stop()
        
        # Отправляем сообщение о завершении работы
        await telegram_reporter.send_message(
            admin_chat_id,
            "🛑 Система улучшения AI-секретаря остановлена."
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске системы: {e}", exc_info=True)
        
        # Пытаемся отправить сообщение об ошибке
        try:
            from src.reporting.telegram_reporter import TelegramReporter
            telegram_reporter = TelegramReporter(os.getenv("TELEGRAM_TOKEN", ""))
            
            error_message = (
                f"❌ Критическая ошибка при запуске системы:\n\n"
                f"{str(e)}\n\n"
                f"Подробности: {traceback.format_exc()[:1000]}...\n\n"
                f"Система будет перезапущена через {restart_delay} секунд."
            )
            
            await telegram_reporter.send_message(os.getenv("ADMIN_CHAT_ID", ""), error_message)
        except Exception as notify_error:
            logger.error(f"Ошибка при отправке уведомления: {notify_error}")
        
        return False

async def main():
    """Главная функция с циклом перезапуска."""
    global is_running, restart_counter, max_restarts
    
    parser = argparse.ArgumentParser(description="Запуск непрерывной системы улучшения AI-секретаря")
    parser.add_argument("--config", type=str, default="config.json", help="Путь к файлу конфигурации")
    args = parser.parse_args()
    
    while is_running:
        # Запуск основного цикла
        success = await main_loop()
        
        # Если работа завершилась с ошибкой и не превышен лимит перезапусков
        if not success and is_running:
            restart_counter += 1
            
            if restart_counter > max_restarts:
                logging.error(f"Превышено максимальное количество перезапусков ({max_restarts}). Завершение работы.")
                break
                
            logging.info(f"Перезапуск системы через {restart_delay} секунд (попытка {restart_counter}/{max_restarts})...")
            await asyncio.sleep(restart_delay)
        elif not is_running:
            # Пользователь запросил завершение
            logging.info("Система остановлена по запросу пользователя.")
            break
        else:
            # Успешное завершение
            logging.info("Система завершила работу успешно.")
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Прервано пользователем. Завершение работы...")
        time.sleep(1)  # Даем время для корректного завершения 