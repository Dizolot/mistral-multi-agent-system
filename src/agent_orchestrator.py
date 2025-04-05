"""
Оркестратор агентов для управления взаимодействием в Telegram-чате.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import os

from src.agents.base_agent import BaseAgent
from src.agents.developer_agent import DeveloperAgent
from src.agents.tester_agent import TesterAgent
from src.agents.product_agent import ProductAgent
from src.agents.deployer_agent import DeployerAgent
from src.reporting.telegram_reporter import TelegramReporter
from src.core.memory_system.memory_manager import MemoryManager
from src.core.memory_system.embedding_provider import MistralEmbeddingProvider
from src.monitoring.task_monitor import TaskMonitor
from src.periodic_tasks.code_analysis_scheduler import CodeAnalysisScheduler
from src.agents.code_analyzer import CodeAnalyzer
from src.utils.git_manager import GitManager

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Класс для управления взаимодействием агентов в Telegram-чате."""
    
    def __init__(self, memory_manager: MemoryManager, config: Dict[str, Any]):
        """
        Инициализация оркестратора.
        
        Args:
            memory_manager: Менеджер памяти для хранения контекста
            config: Конфигурация системы
        """
        self.memory_manager = memory_manager
        self.config = config
        self.chat_id = config.get("telegram", {}).get("chat_id") or config.get("telegram", {}).get("admin_chat_id")
        
        # Создаем репортер для отправки сообщений в Telegram
        token = config.get("telegram", {}).get("token") or os.getenv("TELEGRAM_TOKEN")
        admin_chat_id = config.get("telegram", {}).get("admin_chat_id") or os.getenv("ADMIN_CHAT_ID")
        
        if token and admin_chat_id:
            self.telegram_reporter = TelegramReporter(token, admin_chat_id)
            logger.info("TelegramReporter успешно инициализирован")
        else:
            logger.warning("Не удалось инициализировать TelegramReporter: отсутствуют token или admin_chat_id")
            self.telegram_reporter = None
        
        # Создаем базовую конфигурацию для агентов
        base_config = {
            "model": config.get("model", {}),
            "telegram": config.get("telegram", {})
        }
        
        # Создаем общие зависимости
        code_analyzer = CodeAnalyzer(base_config)
        git_manager = GitManager()
        
        # Создаем агентов
        self.agents = {
            'product': ProductAgent(memory_manager, base_config),
            'developer': DeveloperAgent(
                memory_manager=memory_manager, 
                config=base_config,
                code_analyzer=code_analyzer,
                git_manager=git_manager
            ),
            'tester': TesterAgent(memory_manager, base_config),
            'deployer': DeployerAgent(memory_manager, base_config)
        }
        
        # Устанавливаем message_sender для всех агентов
        if self.telegram_reporter:
            for agent_id, agent in self.agents.items():
                if hasattr(agent, 'set_message_sender') and callable(agent.set_message_sender):
                    agent.set_message_sender(self.telegram_reporter)
                    logger.info(f"Установлен message_sender для агента {agent_id}")
        
        # Инициализируем очередь задач
        self.task_queue = asyncio.Queue()
        
        # Флаг работы системы
        self.is_running = False
        
        # Создаем монитор задач
        self.task_monitor = TaskMonitor(
            telegram_reporter=self.telegram_reporter,
            chat_id=self.chat_id,
            stats_interval=config.get("monitoring", {}).get("stats_interval", 3600)
        )
        
        # Создаем планировщик анализа кода
        self.code_analysis_scheduler = CodeAnalysisScheduler(
            task_callback=self.add_task,
            analysis_interval=config.get("code_analysis", {}).get("interval", 86400),
            secretary_code_path=config.get("code_analysis", {}).get("secretary_path", "src/agents/secretary_agent")
        )
        
    async def start(self) -> None:
        """Запуск оркестратора."""
        if self.is_running:
            logger.warning("Оркестратор уже запущен")
            return
            
        self.is_running = True
        
        # Отправляем стартовое сообщение
        await self.telegram_reporter.send_message(
            self.chat_id,
            "🚀 Запуск системы мульти-агентного улучшения..."
        )
        
        # Описываем роли агентов
        agent_roles = (
            "👨‍💼 Product Manager - формирование задач\n"
            "👨‍💻 Developer - разработка улучшений\n"
            "🧪 Tester - тестирование изменений\n"
            "🚀 Deployer - внедрение улучшений"
        )
        
        await self.telegram_reporter.send_message(
            self.chat_id,
            f"Роли агентов:\n{agent_roles}"
        )
        
        # Запускаем агентов
        for agent_id, agent in self.agents.items():
            await agent.start()
            logger.info(f"Агент {agent_id} успешно запущен")
        
        # Запускаем обработчик задач
        asyncio.create_task(self._process_tasks())
        
        # Запускаем монитор задач
        await self.task_monitor.start()
        
        # Запускаем планировщик анализа кода
        await self.code_analysis_scheduler.start()
        
        logger.info("Оркестратор успешно запущен")
        
    async def stop(self) -> None:
        """Остановка оркестратора."""
        if not self.is_running:
            logger.warning("Оркестратор не запущен")
            return
            
        self.is_running = False
        
        # Останавливаем монитор задач
        await self.task_monitor.stop()
        
        # Останавливаем планировщик анализа кода
        await self.code_analysis_scheduler.stop()
        
        # Отправляем сообщение об остановке
        await self.telegram_reporter.send_message(
            self.chat_id,
            "🛑 Система мульти-агентного улучшения остановлена."
        )
        
        logger.info("Оркестратор остановлен")
        
    async def _process_tasks(self) -> None:
        """Обработка задач из очереди."""
        while self.is_running:
            try:
                # Получаем задачу из очереди
                task = await self.task_queue.get()
                
                # Стандартизируем данные задачи для совместимости между агентами
                standardized_task = await self._standardize_task_data(task)
                
                # Получаем последовательность агентов для обработки задачи
                agent_sequence = self._get_agent_sequence(standardized_task)
                
                # Обрабатываем задачу последовательно через цепочку агентов
                result = standardized_task
                for agent_name in agent_sequence:
                    if agent_name in self.agents:
                        logger.info(f"Передача задачи агенту {agent_name}")
                        
                        # Отправляем сообщение о передаче задачи
                        await self.telegram_reporter.send_message(
                            self.chat_id,
                            f"⏩ Задача передана {agent_name} агенту:\n"
                            f"- Тип: {result.get('type', 'Неизвестный')}\n"
                            f"- Описание: {result.get('description', 'Нет описания')}"
                        )
                        
                        # Обрабатываем задачу текущим агентом
                        try:
                            result = await self.agents[agent_name].process_task(result)
                            
                            # Обновляем статистику задач
                            result['agent_type'] = agent_name
                            await self.task_monitor.update_task_stats(result)
                            
                        except Exception as e:
                            error_msg = f"Ошибка при обработке агентом {agent_name}: {e}"
                            logger.error(error_msg)
                            
                            # Создаем структурированный ответ с ошибкой
                            result = await self.agents[agent_name].handle_error(e, result)
                            await self.task_monitor.update_task_stats(result)
                            
                            # Прерываем цепочку, если произошла ошибка
                            break
                    else:
                        logger.warning(f"Агент {agent_name} не найден")
                        
                # Отправляем сообщение о завершении задачи
                status_emoji = "✅" if result.get('status') == 'success' else "❌"
                await self.telegram_reporter.send_message(
                    self.chat_id,
                    f"{status_emoji} Задача завершена:\n"
                    f"- Статус: {result.get('status', 'Неизвестно')}\n"
                    f"- Результат: {result.get('description', 'Нет описания')}"
                )
                    
                # Отмечаем задачу как выполненную
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Ошибка при обработке задачи: {e}")
                await self.telegram_reporter.send_message(
                    self.chat_id,
                    f"❌ Произошла ошибка при обработке задачи: {e}"
                )
                
    async def _standardize_task_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Стандартизирует данные задачи для обеспечения совместимости между агентами.
        
        Args:
            task: Исходная задача
            
        Returns:
            Стандартизированная задача
        """
        if not task:
            return {}
            
        standardized = task.copy()
        
        # Стандартизация путей к файлам
        file_path = None
        for key in ['file_path', 'target_file', 'target', 'path', 'source_file']:
            if key in task and task[key] is not None:
                file_path = task[key]
                break
        
        if file_path:
            # Стандартизируем все ключи путей к файлам
            standardized['file_path'] = file_path
            standardized['target_file'] = file_path
            standardized['target'] = file_path
        
        # Стандартизация списков файлов
        files_changed = None
        for key in ['files_changed', 'files', 'modified_files', 'changed_files']:
            if key in task and task[key] is not None:
                # Проверяем, что значение является списком или кортежем перед использованием
                if isinstance(task[key], (list, tuple)):
                    files_changed = task[key]
                    break
        
        if files_changed:
            standardized['files_changed'] = files_changed
            standardized['files'] = files_changed
        
        return standardized
        
    def _get_agent_sequence(self, task: dict) -> List[str]:
        """
        Определение последовательности агентов для обработки задачи.
        
        Args:
            task: Задача для обработки
            
        Returns:
            Список имен агентов в порядке их вызова
        """
        # Определяем последовательность агентов в зависимости от типа задачи
        task_type = task.get('type', 'improvement')
        
        if task_type == 'analysis':
            # Для задач анализа нам не нужен тестировщик и деплоер
            return ['product', 'developer']
        elif task_type == 'bug':
            # Для исправления багов важно включить все этапы
            return ['product', 'developer', 'tester', 'deployer']
        elif task_type == 'improvement':
            # Стандартная последовательность для улучшения кода
            return ['product', 'developer', 'tester', 'deployer']
        elif task_type == 'testing':
            # Только тестирование существующего кода
            return ['tester']
        elif task_type == 'deployment':
            # Только деплоймент уже протестированного кода
            return ['deployer']
        else:
            # Для неизвестных типов используем полную последовательность
            logger.warning(f"Неизвестный тип задачи: {task_type}, используем полную последовательность")
            return ['product', 'developer', 'tester', 'deployer']
        
    async def add_task(self, task: dict) -> None:
        """
        Добавление новой задачи в очередь.
        
        Args:
            task: Задача для выполнения
        """
        await self.task_queue.put(task)
        logger.info(f"Добавлена новая задача в очередь: {task}")
        
    async def get_status(self) -> str:
        """
        Получение статуса системы.
        
        Returns:
            Строка с информацией о статусе системы
        """
        status_lines = [
            "📊 Статус системы мульти-агентного улучшения:",
            f"- Статус: {'🟢 Работает' if self.is_running else '🔴 Остановлена'}",
            f"- Задач в очереди: {self.task_queue.qsize()}",
            "\nСтатус агентов:"
        ]
        
        for name, agent in self.agents.items():
            status = "🟢 Активен" if agent.is_active else "🔴 Неактивен"
            tasks = len(agent.completed_tasks)
            status_lines.append(f"- {name}: {status} (выполнено задач: {tasks})")
            
        return "\n".join(status_lines) 