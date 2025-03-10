"""
Основной модуль Telegram-бота для взаимодействия с моделью Mistral.
Обрабатывает сообщения пользователей и отправляет запросы к API.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import (
    TELEGRAM_TOKEN, ADMIN_CHAT_ID, MISTRAL_API_URL,
    DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS,
    REQUEST_TIMEOUT, POLL_INTERVAL, MAX_MESSAGE_LENGTH,
    WELCOME_MESSAGE, HELP_MESSAGE, RESET_MESSAGE,
    PROCESSING_MESSAGE, ERROR_MESSAGE, TIMEOUT_MESSAGE
)
from mistral_client import MistralClient
from conversation_manager import ConversationManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join("logs", "telegram_bot.log"))
    ]
)
logger = logging.getLogger(__name__)

# Инициализация клиента Mistral API и менеджера диалогов
mistral_client = MistralClient(base_url=MISTRAL_API_URL)
conversation_manager = ConversationManager()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    logger.info(f"Пользователь {user_id} запустил бота")
    
    # Сбрасываем историю диалога при запуске
    conversation_manager.reset_conversation(user_id)
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("Помощь", callback_data="help")],
        [InlineKeyboardButton("Сбросить диалог", callback_data="reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветственное сообщение
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=reply_markup
    )
    
    # Если есть ID администратора, отправляем ему уведомление
    if ADMIN_CHAT_ID:
        try:
            admin_id = int(ADMIN_CHAT_ID)
            if admin_id != user_id:  # Не отправляем уведомление, если админ запустил бота
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"Пользователь {user.full_name} (ID: {user_id}) запустил бота."
                )
        except (ValueError, Exception) as e:
            logger.error(f"Ошибка при отправке уведомления администратору: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} запросил помощь")
    
    await update.message.reply_text(HELP_MESSAGE)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /reset"""
    user_id = update.effective_user.id
    logger.info(f"Пользователь {user_id} сбросил диалог")
    
    conversation_manager.reset_conversation(user_id)
    await update.message.reply_text(RESET_MESSAGE)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Проверяем длину сообщения
    if len(message_text) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text(
            f"Ваше сообщение слишком длинное. Максимальная длина: {MAX_MESSAGE_LENGTH} символов."
        )
        return
    
    logger.info(f"Получено сообщение от пользователя {user_id}: {message_text[:50]}...")
    
    # Добавляем сообщение пользователя в историю
    conversation_manager.add_user_message(user_id, message_text)
    
    # Отправляем сообщение о том, что запрос обрабатывается
    processing_message = await update.message.reply_text(PROCESSING_MESSAGE)
    
    try:
        # Получаем историю сообщений
        messages = conversation_manager.get_messages(user_id)
        
        # Отправляем запрос к модели
        response = await mistral_client.generate_response(
            prompt=message_text,
        )
        
        # Если получили ответ, добавляем его в историю и отправляем пользователю
        if response:
            conversation_manager.add_assistant_message(user_id, response)
            await processing_message.delete()  # Удаляем сообщение о обработке
            await update.message.reply_text(response)
        else:
            # Если ответ не получен, отправляем сообщение об ошибке
            await processing_message.delete()
            await update.message.reply_text(ERROR_MESSAGE)
    
    except asyncio.TimeoutError:
        # Если превышено время ожидания
        await processing_message.delete()
        await update.message.reply_text(TIMEOUT_MESSAGE)
    
    except Exception as e:
        # В случае других ошибок
        logger.error(f"Ошибка при обработке сообщения: {str(e)}")
        await processing_message.delete()
        await update.message.reply_text(ERROR_MESSAGE)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"Пользователь {user_id} нажал кнопку: {callback_data}")
    
    # Отправляем уведомление о получении запроса
    await query.answer()
    
    if callback_data == "help":
        await query.message.reply_text(HELP_MESSAGE)
    
    elif callback_data == "reset":
        conversation_manager.reset_conversation(user_id)
        await query.message.reply_text(RESET_MESSAGE)

def main() -> None:
    """Основная функция для запуска бота"""
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # Добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик нажатий на кнопки
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запускаем бота
    logger.info("Запуск бота...")
    application.run_polling()

if __name__ == "__main__":
    main() 