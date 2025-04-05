#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для интеграции Telegram-бота с системой непрерывного улучшения.

Этот модуль обеспечивает взаимодействие между Telegram и системой агентов,
позволяет отправлять отчеты и управлять работой агентов через Telegram.
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable

# Логирование
logger = logging.getLogger(__name__)

class TelegramIntegration:
    """Класс для интеграции Telegram-бота с системой агентов."""
    
    def __init__(
        self,
        agent_orchestrator,
        improvement_tracker,
        telegram_reporter,
        admin_chat_id: str,
        reporting_interval: int = 3600,
        api_url: str = "http://localhost:8080",
        standalone_mode: bool = False
    ):
        """Инициализация TelegramIntegration.
        
        Args:
            agent_orchestrator: Экземпляр AgentOrchestrator.
            improvement_tracker: Экземпляр ImprovementTracker.
            telegram_reporter: Экземпляр TelegramReporter.
            admin_chat_id: ID чата администратора.
            reporting_interval: Интервал отправки регулярных отчетов в секундах.
            api_url: URL API сервера.
            standalone_mode: Режим работы без оркестратора и трекера (только для тестирования).
        """
        self.agent_orchestrator = agent_orchestrator
        self.improvement_tracker = improvement_tracker
        self.telegram_reporter = telegram_reporter
        self.admin_chat_id = admin_chat_id
        self.reporting_interval = reporting_interval
        self.api_url = api_url
        self.standalone_mode = standalone_mode
        
        self.running = False
        self.reporting_task = None
        
        # Регистрируем обработчики команд
        self._register_handlers()
        
    async def start(self):
        """Запуск интеграции с Telegram."""
        if self.running:
            logger.warning("TelegramIntegration уже запущен")
            return
        
        try:
            logger.info("Запуск TelegramIntegration...")
            
            # Регистрируем обработчики событий, если есть компоненты системы
            if not self.standalone_mode:
                self._register_event_handlers()
                
            # Запускаем задачу регулярной отправки отчетов
            self.reporting_task = asyncio.create_task(self._regular_reporting())
            
            self.running = True
            logger.info("TelegramIntegration успешно запущен")
            
            # Отправляем уведомление о запуске
            await self._send_startup_notification()
            
        except Exception as e:
            logger.error(f"Ошибка при запуске TelegramIntegration: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Остановка интеграции с Telegram."""
        if not self.running:
            return
        
        logger.info("Остановка TelegramIntegration...")
        
        # Останавливаем задачу регулярной отправки отчетов
        if self.reporting_task:
            self.reporting_task.cancel()
            try:
                await self.reporting_task
            except asyncio.CancelledError:
                pass
        
        self.running = False
        logger.info("TelegramIntegration остановлен")
    
    # Обработчики команд
    
    async def _handle_status_command(self, update, context):
        """Обработка команды /status."""
        try:
            if self.standalone_mode:
                status = self._get_mock_status()
            else:
                status = await self._get_system_status()
                
            await self.telegram_reporter.send_status_report(status, update.effective_chat.id)
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /status: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def _handle_metrics_command(self, update, context):
        """Обработка команды /metrics."""
        try:
            if self.standalone_mode:
                await update.message.reply_text("⚠️ Режим без системы: метрики недоступны")
                return
                
            metrics = await self._get_system_metrics()
            report = self._format_metrics_report(metrics)
            await update.message.reply_text(report, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /metrics: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def _handle_logs_command(self, update, context):
        """Обработка команды /logs."""
        try:
            lines = 50  # По умолчанию 50 строк
            if context.args and context.args[0].isdigit():
                lines = min(int(context.args[0]), 200)  # Не более 200 строк
                
            logs = await self._get_system_logs(lines)
            
            if not logs:
                await update.message.reply_text("ℹ️ Логи отсутствуют или недоступны")
                return
                
            # Отправляем логи в виде текстового файла, если они слишком большие
            if len(logs) > 4000:
                logs_file = "logs_temp.txt"
                with open(logs_file, "w", encoding="utf-8") as f:
                    f.write(logs)
                    
                with open(logs_file, "rb") as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        filename="system_logs.txt",
                        caption=f"📄 Последние {lines} строк логов системы"
                    )
                    
                os.remove(logs_file)
            else:
                # Отправляем логи как текстовое сообщение
                await update.message.reply_text(
                    f"📋 <b>Последние {lines} строк логов:</b>\n\n<pre>{logs}</pre>",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /logs: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def _handle_force_improve_command(self, update, context):
        """Обработка команды /force_improve."""
        try:
            if self.standalone_mode:
                await update.message.reply_text("⚠️ Режим без системы: улучшения недоступны")
                return
                
            # Получаем аргументы команды (target_files, type)
            target_files = []
            improvement_type = "auto"
            
            if context.args:
                for arg in context.args:
                    if arg.startswith("type="):
                        improvement_type = arg.split("=")[1]
                    elif not arg.startswith("type="):
                        target_files.append(arg)
            
            await update.message.reply_text(
                f"🔄 Запуск процесса улучшения...\n"
                f"Тип: {improvement_type}\n"
                f"Файлы: {', '.join(target_files) if target_files else 'все'}"
            )
            
            # Запускаем процесс улучшения
            result = await self._force_improvement(target_files, improvement_type)
            
            if result:
                await update.message.reply_text(
                    f"✅ Процесс улучшения запущен\n"
                    f"ID улучшения: {result}"
                )
            else:
                await update.message.reply_text("❌ Не удалось запустить процесс улучшения")
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /force_improve: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def _handle_approve_command(self, update, context):
        """Обработка команды /approve."""
        try:
            if self.standalone_mode:
                await update.message.reply_text("⚠️ Режим без системы: улучшения недоступны")
                return
                
            if not context.args:
                await update.message.reply_text("❌ Необходимо указать ID улучшения: /approve <id>")
                return
                
            improvement_id = context.args[0]
            
            await update.message.reply_text(f"🔄 Одобрение улучшения {improvement_id}...")
            
            # Одобряем улучшение
            success = await self._approve_improvement(improvement_id)
            
            if success:
                await update.message.reply_text(f"✅ Улучшение {improvement_id} одобрено")
            else:
                await update.message.reply_text(f"❌ Не удалось одобрить улучшение {improvement_id}")
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /approve: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def _handle_reject_command(self, update, context):
        """Обработка команды /reject."""
        try:
            if self.standalone_mode:
                await update.message.reply_text("⚠️ Режим без системы: улучшения недоступны")
                return
                
            if not context.args:
                await update.message.reply_text("❌ Необходимо указать ID улучшения: /reject <id>")
                return
                
            improvement_id = context.args[0]
            reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Не указана причина"
            
            await update.message.reply_text(f"🔄 Отклонение улучшения {improvement_id}...")
            
            # Отклоняем улучшение
            success = await self._reject_improvement(improvement_id, reason)
            
            if success:
                await update.message.reply_text(f"✅ Улучшение {improvement_id} отклонено")
            else:
                await update.message.reply_text(f"❌ Не удалось отклонить улучшение {improvement_id}")
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /reject: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    async def _handle_help_command(self, update, context):
        """Обработка команды /help."""
        help_message = self._generate_help_message()
        await update.message.reply_text(help_message, parse_mode="HTML")
    
    async def _handle_report_command(self, update, context):
        """Обработка команды /report."""
        try:
            if self.standalone_mode:
                await update.message.reply_text("⚠️ Режим без системы: отчёт недоступен")
                return
            
            await update.message.reply_text("🔄 Формирование отчёта о состоянии системы...")
            
            # Получаем данные о системе
            status = await self._get_system_status()
            metrics = await self._get_system_metrics()
            
            # Формируем полный отчёт
            report = self._generate_full_report(status, metrics)
            
            await update.message.reply_text(report, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды /report: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Вспомогательные методы
    
    def _register_handlers(self):
        """Регистрация обработчиков команд в TelegramReporter."""
        if not self.telegram_reporter:
            logger.warning("TelegramReporter не инициализирован, обработчики не зарегистрированы")
            return
            
        self.telegram_reporter.register_command_handler("status", self._handle_status_command)
        self.telegram_reporter.register_command_handler("metrics", self._handle_metrics_command)
        self.telegram_reporter.register_command_handler("logs", self._handle_logs_command)
        self.telegram_reporter.register_command_handler("force_improve", self._handle_force_improve_command)
        self.telegram_reporter.register_command_handler("approve", self._handle_approve_command)
        self.telegram_reporter.register_command_handler("reject", self._handle_reject_command)
        self.telegram_reporter.register_command_handler("help", self._handle_help_command)
        self.telegram_reporter.register_command_handler("report", self._handle_report_command)
        
        # Регистрируем обработчики callback-запросов
        self.telegram_reporter.register_callback_handler("approve_", self._handle_approve_callback)
        self.telegram_reporter.register_callback_handler("reject_", self._handle_reject_callback)
    
    def _register_event_handlers(self):
        """Регистрация обработчиков событий от компонентов системы."""
        if not self.improvement_tracker:
            logger.warning("ImprovementTracker не инициализирован, обработчики событий не зарегистрированы")
            return
            
        # Регистрируем обработчики событий от ImprovementTracker
        # (в реальном коде здесь будет регистрация функций-обработчиков событий)
    
    async def _regular_reporting(self):
        """Периодическая отправка отчетов о статусе системы."""
        try:
            logger.info(f"Запуск регулярной отправки отчетов с интервалом {self.reporting_interval} сек.")
            
            while self.running:
                # Ждем указанное время
                await asyncio.sleep(self.reporting_interval)
                
                if not self.running:
                    break
                    
                try:
                    logger.debug("Подготовка регулярного отчета...")
                    
                    if self.standalone_mode:
                        status = self._get_mock_status()
                    else:
                        status = await self._get_system_status()
                        
                    # Отправляем отчет о статусе системы
                    await self.telegram_reporter.send_status_report(status, self.admin_chat_id)
                    
                    logger.debug("Регулярный отчет отправлен")
                except Exception as e:
                    logger.error(f"Ошибка при отправке регулярного отчета: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("Задача регулярной отправки отчетов остановлена")
        except Exception as e:
            logger.error(f"Неожиданная ошибка в задаче регулярной отправки отчетов: {e}", exc_info=True)
    
    async def _send_startup_notification(self):
        """Отправка уведомления о запуске системы."""
        try:
            message = (
                "🚀 <b>Система запущена</b>\n\n"
                f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Режим: {'Автономный' if self.standalone_mode else 'Полный'}\n\n"
                "Используйте /status для проверки текущего состояния системы."
            )
            
            await self.telegram_reporter.send_message(
                chat_id=self.admin_chat_id,
                text=message
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о запуске: {e}", exc_info=True)
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Получение статуса системы.
        
        Returns:
            Словарь с данными о статусе системы.
        """
        # В реальном коде здесь будет логика получения статуса системы
        # от AgentOrchestrator и ImprovementTracker
        status = {
            "status": "running",
            "uptime": "0:00:00",
            "agents": [],
            "improvements": {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "pending": 0,
                "rejected": 0
            },
            "resources": {
                "cpu": 0,
                "memory": 0,
                "disk": 0
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Получаем данные от оркестратора агентов
        if self.agent_orchestrator:
            # В реальном коде здесь будет вызов методов AgentOrchestrator
            pass
            
        # Получаем данные от трекера улучшений
        if self.improvement_tracker:
            # В реальном коде здесь будет вызов методов ImprovementTracker
            pass
            
        return status
    
    def _get_mock_status(self) -> Dict[str, Any]:
        """Создание mock-данных о статусе системы для автономного режима.
        
        Returns:
            Словарь с mock-данными о статусе системы.
        """
        return {
            "status": "running",
            "uptime": "0:10:00",
            "agents": [
                {"id": "mock-agent-1", "type": "code_optimizer", "status": "active"},
                {"id": "mock-agent-2", "type": "bug_finder", "status": "idle"}
            ],
            "improvements": {
                "total": 5,
                "completed": 2,
                "in_progress": 1,
                "pending": 1,
                "rejected": 1
            },
            "resources": {
                "cpu": 15,
                "memory": 30,
                "disk": 50
            },
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Получение метрик системы.
        
        Returns:
            Словарь с метриками системы.
        """
        # В реальном коде здесь будет логика получения метрик системы
        return {}
    
    def _format_metrics_report(self, metrics: Dict[str, Any]) -> str:
        """Форматирование отчета о метриках системы.
        
        Args:
            metrics: Словарь с метриками системы.
            
        Returns:
            Отформатированный отчет.
        """
        # В реальном коде здесь будет логика форматирования метрик
        return "<b>Метрики системы</b>\n\nНет доступных метрик"
    
    async def _get_system_logs(self, lines: int = 50) -> str:
        """Получение логов системы.
        
        Args:
            lines: Количество строк логов.
            
        Returns:
            Строки логов.
        """
        # В реальном коде здесь будет логика получения логов системы
        return "Логи системы недоступны в данный момент"
    
    async def _force_improvement(self, target_files: List[str], improvement_type: str) -> Optional[str]:
        """Запуск процесса улучшения.
        
        Args:
            target_files: Список файлов для улучшения.
            improvement_type: Тип улучшения.
            
        Returns:
            ID созданного улучшения или None в случае ошибки.
        """
        # В реальном коде здесь будет логика запуска улучшения
        return "mock-improvement-1"
    
    async def _approve_improvement(self, improvement_id: str) -> bool:
        """Одобрение улучшения.
        
        Args:
            improvement_id: ID улучшения.
            
        Returns:
            True, если улучшение успешно одобрено, иначе False.
        """
        # В реальном коде здесь будет логика одобрения улучшения
        return True
    
    async def _reject_improvement(self, improvement_id: str, reason: str) -> bool:
        """Отклонение улучшения.
        
        Args:
            improvement_id: ID улучшения.
            reason: Причина отклонения.
            
        Returns:
            True, если улучшение успешно отклонено, иначе False.
        """
        # В реальном коде здесь будет логика отклонения улучшения
        return True
    
    async def _handle_approve_callback(self, query, context):
        """Обработка callback-запроса на одобрение улучшения."""
        improvement_id = query.data.split("_")[1]
        await query.edit_message_text(f"🔄 Одобрение улучшения {improvement_id}...")
        
        try:
            success = await self._approve_improvement(improvement_id)
            
            if success:
                await query.edit_message_text(f"✅ Улучшение {improvement_id} одобрено")
            else:
                await query.edit_message_text(f"❌ Не удалось одобрить улучшение {improvement_id}")
        except Exception as e:
            logger.error(f"Ошибка при обработке callback на одобрение: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    
    async def _handle_reject_callback(self, query, context):
        """Обработка callback-запроса на отклонение улучшения."""
        improvement_id = query.data.split("_")[1]
        await query.edit_message_text(f"🔄 Отклонение улучшения {improvement_id}...")
        
        try:
            success = await self._reject_improvement(improvement_id, "Отклонено через интерфейс")
            
            if success:
                await query.edit_message_text(f"✅ Улучшение {improvement_id} отклонено")
            else:
                await query.edit_message_text(f"❌ Не удалось отклонить улучшение {improvement_id}")
        except Exception as e:
            logger.error(f"Ошибка при обработке callback на отклонение: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    
    def _generate_help_message(self) -> str:
        """Генерация сообщения с помощью.
        
        Returns:
            Сообщение с помощью.
        """
        message = (
            "🤖 <b>Доступные команды</b>:\n\n"
            "/status - Статус системы\n"
            "/report - Полный отчёт о состоянии системы\n"
            "/metrics - Метрики производительности\n"
            "/logs [N] - Последние N строк логов системы\n"
            "/force_improve [файлы] [type=тип] - Запустить улучшение кода\n"
            "/approve <id> - Принять улучшение\n"
            "/reject <id> [причина] - Отклонить улучшение\n"
            "/help - Показать это сообщение\n\n"
            
            "<b>Примеры использования:</b>\n"
            "/logs 100 - Показать последние 100 строк логов\n"
            "/force_improve src/main.py - Улучшить конкретный файл\n"
            "/force_improve type=bug_fix - Запустить исправление ошибок\n"
            "/reject 123 Требуется доработка - Отклонить с указанием причины"
        )
        return message 
    
    def _generate_full_report(self, status: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        """Генерация полного отчёта о системе.
        
        Args:
            status: Данные о статусе системы.
            metrics: Метрики системы.
            
        Returns:
            Отформатированный отчёт.
        """
        report = "📑 <b>ПОЛНЫЙ ОТЧЁТ О СИСТЕМЕ</b>\n\n"
        
        # Добавляем информацию о статусе
        report += "📊 <b>СТАТУС СИСТЕМЫ</b>\n"
        report += f"├── Состояние: {status.get('status', 'неизвестно')}\n"
        report += f"├── Время работы: {status.get('uptime', '0:00:00')}\n"
        
        # Информация об агентах
        report += "\n👥 <b>АГЕНТЫ</b>\n"
        agents = status.get('agents', [])
        if agents:
            for i, agent in enumerate(agents, 1):
                agent_status = agent.get('status', 'неизвестно')
                status_emoji = "🟢" if agent_status == "active" else "⚪" if agent_status == "idle" else "🔴"
                report += f"├── {i}. {status_emoji} {agent.get('type', 'Агент')} ({agent.get('id', 'ID?')})\n"
        else:
            report += "├── Нет активных агентов\n"
        
        # Информация об улучшениях
        report += "\n🔧 <b>УЛУЧШЕНИЯ</b>\n"
        improvements = status.get('improvements', {})