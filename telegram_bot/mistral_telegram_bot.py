"""
Базовый Telegram бот с интеграцией Mistral API и LangChain маршрутизатором.

Этот модуль предоставляет простой Telegram бот, который обрабатывает сообщения 
пользователей и отправляет их в Mistral API через LangChain маршрутизатор.
"""

import os
import sys
import json
import logging
import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

import httpx
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

# Добавляем корневую директорию проекта в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from multi_agent_system.memory.conversation_memory import ConversationMemoryManager
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector
from multi_agent_system.memory.memory_analytics_integration import MemoryAnalyticsIntegration
from multi_agent_system.langchain_integration.langchain_router import LangChainRouter
from multi_agent_system.logger import get_logger

# Настройка логирования
logger = get_logger(__name__)


class MistralTelegramBot:
    """
    Telegram бот с интеграцией Mistral API и LangChain маршрутизатором.
    
    Этот класс обрабатывает сообщения пользователей, отправляет их в Mistral API
    через LangChain маршрутизатор и возвращает ответы.
    """
    
    def __init__(
        self,
        telegram_token: str,
        mistral_api_url: str = "http://localhost:8080/completion",
        use_langchain_router: bool = True,
        memory_manager: Optional[ConversationMemoryManager] = None,
        data_collector: Optional[AgentDataCollector] = None
    ):
        """
        Инициализирует Telegram бот.
        
        Args:
            telegram_token: Токен Telegram бота
            mistral_api_url: URL API Mistral
            use_langchain_router: Использовать ли LangChain маршрутизатор
            memory_manager: Менеджер памяти (опционально)
            data_collector: Коллектор данных (опционально)
        """
        self.telegram_token = telegram_token
        self.mistral_api_url = mistral_api_url
        self.use_langchain_router = use_langchain_router
        
        # Инициализируем компоненты
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.data_collector = data_collector or AgentDataCollector()
        
        # Инициализируем интеграцию памяти и аналитики
        self.memory_analytics = MemoryAnalyticsIntegration(
            memory_manager=self.memory_manager,
            data_collector=self.data_collector
        )
        
        # Инициализируем LangChain маршрутизатор, если он используется
        self.langchain_router = None
        if self.use_langchain_router:
            self.langchain_router = LangChainRouter()
        
        # Создаем Telegram приложение
        self.application = Application.builder().token(telegram_token).build()
        
        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(CommandHandler("mode", self.mode_command))
        
        # Добавляем обработчик сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Добавляем обработчик обратных вызовов
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Добавляем обработчик ошибок
        self.application.add_error_handler(self.error_handler)
        
        # Словарь для хранения сообщений с прогрессом
        self.progress_messages = {}
        
        logger.info("Telegram бот с Mistral API инициализирован")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /start.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика Telegram
        """
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name
        
        # Создаем приветственное сообщение
        welcome_message = (
            f"Привет, {user_name}! Я бот, использующий Mistral AI для ответов на ваши вопросы.\n\n"
            "Вот что я могу делать:\n"
            "• Отвечать на вопросы на различные темы\n"
            "• Помогать с программированием и техническими проблемами\n"
            "• Объяснять сложные концепции простым языком\n\n"
            "Напишите сообщение, чтобы начать общение!"
        )
        
        # Добавляем системное сообщение в память
        self.memory_manager.add_system_message(
            user_id=user_id,
            message=f"Пользователь {user_name} (ID: {user_id}) начал диалог."
        )
        
        # Отправляем приветственное сообщение
        await update.message.reply_text(welcome_message)
        logger.info(f"Пользователь {user_id} ({user_name}) начал диалог")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /help.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика Telegram
        """
        help_message = (
            "🤖 *Справка по командам бота*\n\n"
            "*/start* - Начать диалог с ботом\n"
            "*/help* - Показать эту справку\n"
            "*/reset* - Сбросить историю диалога\n"
            "*/mode* - Переключить режим работы (Mistral API или LangChain Router)\n\n"
            "Просто напишите сообщение, чтобы получить ответ от Mistral AI."
        )
        
        await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /reset.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика Telegram
        """
        user_id = str(update.effective_user.id)
        
        # Сохраняем историю в аналитику перед сбросом
        self.memory_analytics.process_conversation_history(
            user_id=user_id,
            process_all=True
        )
        
        # Сбрасываем историю диалога
        self.memory_manager.clear_memory(user_id)
        
        await update.message.reply_text("История диалога сброшена. Вы можете начать новый диалог!")
        logger.info(f"Пользователь {user_id} сбросил историю диалога")
    
    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /mode.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика Telegram
        """
        # Создаем клавиатуру с кнопками выбора режима
        keyboard = [
            [
                InlineKeyboardButton("Mistral API", callback_data="mode_mistral"),
                InlineKeyboardButton("LangChain Router", callback_data="mode_langchain")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите режим работы бота:",
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает нажатия на кнопки.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика Telegram
        """
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        callback_data = query.data
        
        # Обрабатываем выбор режима
        if callback_data == "mode_mistral":
            self.use_langchain_router = False
            await query.edit_message_text("Режим работы изменен на Mistral API")
            logger.info(f"Пользователь {user_id} переключился на режим Mistral API")
        
        elif callback_data == "mode_langchain":
            if self.langchain_router is None:
                self.langchain_router = LangChainRouter()
            
            self.use_langchain_router = True
            await query.edit_message_text("Режим работы изменен на LangChain Router")
            logger.info(f"Пользователь {user_id} переключился на режим LangChain Router")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает текстовые сообщения от пользователей.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика Telegram
        """
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name
        message_text = update.message.text
        
        # Сохраняем сообщение пользователя в памяти
        self.memory_manager.add_user_message(user_id, message_text)
        
        # Отправляем индикатор набора текста
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Отправляем начальное сообщение о прогрессе
        progress_message = await update.message.reply_text("⏳ Обрабатываю запрос...")
        
        # Сохраняем ID сообщения с прогрессом
        self.progress_messages[user_id] = {
            "message_id": progress_message.message_id,
            "chat_id": update.effective_chat.id,
            "start_time": time.time(),
            "last_update": time.time()
        }
        
        # Запускаем фоновую задачу для обновления сообщения с прогрессом
        asyncio.create_task(self.update_progress_message(context.bot, user_id))
        
        try:
            # В зависимости от режима работы, используем разные методы обработки
            if self.use_langchain_router and self.langchain_router:
                response = await self.process_with_langchain(user_id, message_text)
            else:
                response = await self.process_with_mistral_api(user_id, message_text)
            
            # Сохраняем ответ в памяти
            self.memory_manager.add_ai_message(
                user_id=user_id,
                message=response,
                agent_name=self.langchain_router.get_last_used_agent() if self.use_langchain_router else "mistral_api"
            )
            
            # Удаляем запись о сообщении с прогрессом
            self.progress_messages.pop(user_id, None)
            
            # Редактируем сообщение с ответом
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text=response
            )
            
            # Сохраняем взаимодействие в аналитику
            self.data_collector.record_interaction(
                user_id=user_id,
                session_id=user_id,  # Используем ID пользователя в качестве ID сессии
                agent_name=self.langchain_router.get_last_used_agent() if self.use_langchain_router else "mistral_api",
                request=message_text,
                response=response,
                processing_time=time.time() - self.progress_messages.get(user_id, {}).get("start_time", time.time()),
                is_successful=True,
                metadata={"source": "telegram_bot"}
            )
            
            logger.info(f"Пользователь {user_id} получил ответ на запрос: {message_text[:50]}...")
        
        except Exception as e:
            error_message = f"Произошла ошибка при обработке запроса: {str(e)}"
            logger.error(f"Ошибка при обработке запроса от пользователя {user_id}: {str(e)}")
            
            # Удаляем запись о сообщении с прогрессом
            self.progress_messages.pop(user_id, None)
            
            # Редактируем сообщение с ошибкой
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text=error_message
            )
    
    async def update_progress_message(self, bot: Bot, user_id: str) -> None:
        """
        Обновляет сообщение с прогрессом обработки запроса.
        
        Args:
            bot: Объект бота Telegram
            user_id: ID пользователя
        """
        progress_chars = ["⏳", "⌛"]
        progress_idx = 0
        
        while user_id in self.progress_messages:
            progress_info = self.progress_messages[user_id]
            current_time = time.time()
            elapsed_time = current_time - progress_info["start_time"]
            
            # Обновляем сообщение с прогрессом каждые 2 секунды
            if current_time - progress_info["last_update"] >= 2.0:
                try:
                    progress_char = progress_chars[progress_idx]
                    progress_idx = (progress_idx + 1) % len(progress_chars)
                    
                    # Форматируем время
                    elapsed_str = f"{int(elapsed_time)}s"
                    
                    # Получаем текст о статусе маршрутизации, если используется LangChain Router
                    routing_status = ""
                    if self.use_langchain_router and self.langchain_router:
                        last_agent = self.langchain_router.get_last_used_agent()
                        routing_status = f"\nАгент: {last_agent}" if last_agent else "\nВыполняется маршрутизация..."
                    
                    # Обновляем сообщение
                    await bot.edit_message_text(
                        chat_id=progress_info["chat_id"],
                        message_id=progress_info["message_id"],
                        text=f"{progress_char} Обрабатываю запрос... ({elapsed_str}){routing_status}"
                    )
                    
                    # Обновляем время последнего обновления
                    self.progress_messages[user_id]["last_update"] = current_time
                
                except Exception as e:
                    logger.warning(f"Ошибка при обновлении сообщения с прогрессом для пользователя {user_id}: {str(e)}")
            
            # Пауза перед следующей проверкой
            await asyncio.sleep(0.5)
    
    async def process_with_mistral_api(self, user_id: str, message: str) -> str:
        """
        Обрабатывает запрос пользователя через Mistral API.
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения пользователя
            
        Returns:
            Ответ от Mistral API
        """
        # Получаем историю диалога
        chat_history = self.memory_manager.get_formatted_history(user_id)
        
        # Формируем запрос к Mistral API
        payload = {
            "model": "mistral-7b-instruct",
            "messages": chat_history + [{"role": "user", "content": message}],
            "temperature": 0.7,
            "max_tokens": 4000,
            "top_p": 0.95,
            "stream": False
        }
        
        # Отправляем запрос к Mistral API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.mistral_api_url,
                json=payload
            )
            
            if response.status_code != 200:
                error_message = f"Ошибка API Mistral ({response.status_code}): {response.text}"
                logger.error(error_message)
                raise Exception(error_message)
            
            response_data = response.json()
            
            # Извлекаем текст ответа из ответа API
            if "choices" in response_data and len(response_data["choices"]) > 0:
                message_content = response_data["choices"][0].get("message", {}).get("content", "")
                return message_content
            else:
                error_message = "Не удалось получить ответ от API Mistral"
                logger.error(error_message)
                raise Exception(error_message)
    
    async def process_with_langchain(self, user_id: str, message: str) -> str:
        """
        Обрабатывает запрос пользователя через LangChain маршрутизатор.
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения пользователя
            
        Returns:
            Ответ от LangChain маршрутизатора
        """
        if not self.langchain_router:
            error_message = "LangChain маршрутизатор не инициализирован"
            logger.error(error_message)
            raise Exception(error_message)
        
        # Получаем историю диалога
        chat_history = self.memory_manager.get_chat_history(user_id)
        
        # Формируем запрос к LangChain маршрутизатору
        result = self.langchain_router.route_request(
            user_input=message,
            user_id=user_id,
            chat_history=chat_history
        )
        
        if not result or not isinstance(result, str):
            error_message = "Не удалось получить ответ от LangChain маршрутизатора"
            logger.error(error_message)
            raise Exception(error_message)
        
        return result
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает ошибки Telegram.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика Telegram
        """
        logger.error(f"Ошибка Telegram: {context.error}")
        
        # Отправляем сообщение об ошибке пользователю
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз позже."
            )
    
    def run(self, polling: bool = True, webhook_url: Optional[str] = None) -> None:
        """
        Запускает бота.
        
        Args:
            polling: Использовать ли long polling
            webhook_url: URL для webhook (используется, если polling=False)
        """
        if polling:
            # Запускаем бота с использованием long polling
            self.application.run_polling()
        else:
            # Запускаем бота с использованием webhook
            if not webhook_url:
                raise ValueError("webhook_url должен быть указан при использовании webhook")
            
            self.application.run_webhook(
                listen="0.0.0.0",
                port=8443,
                webhook_url=webhook_url
            )


if __name__ == "__main__":
    # Получаем токен из переменных окружения
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    mistral_api_url = os.getenv("MISTRAL_API_URL", "http://localhost:8080/completion")
    
    if not telegram_token:
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения")
        sys.exit(1)
    
    # Создаем и запускаем бота
    bot = MistralTelegramBot(
        telegram_token=telegram_token,
        mistral_api_url=mistral_api_url,
        use_langchain_router=True
    )
    
    bot.run(polling=True) 