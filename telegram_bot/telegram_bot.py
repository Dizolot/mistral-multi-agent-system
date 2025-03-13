"""
Основной модуль Telegram бота
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from telegram_bot.config import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    RESET_MESSAGE,
    PROCESSING_MESSAGE,
    ERROR_MESSAGE,
    TIMEOUT_MESSAGE,
    MAX_MESSAGE_LENGTH,
    MAX_HISTORY_LENGTH
)

from telegram_bot.mistral_client import MistralClient
from telegram_bot.orchestrator_adapter import OrchestratorAdapter

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Словарь для хранения истории диалогов
chat_histories: Dict[int, List[Dict[str, str]]] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start
    """
    if not update.effective_chat:
        return
        
    chat_id = update.effective_chat.id
    chat_histories[chat_id] = []
    
    await update.message.reply_text(WELCOME_MESSAGE)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /help
    """
    if not update.message:
        return
        
    await update.message.reply_text(HELP_MESSAGE)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /reset - очищает историю диалога
    """
    if not update.effective_chat:
        return
        
    chat_id = update.effective_chat.id
    chat_histories[chat_id] = []
    
    await update.message.reply_text(RESET_MESSAGE)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик текстовых сообщений
    """
    if not update.message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    user_message = update.message.text

    # Инициализируем историю диалога, если её нет
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    # Добавляем сообщение пользователя в историю
    chat_histories[chat_id].append({
        "role": "user",
        "content": user_message
    })

    # Ограничиваем длину истории
    if len(chat_histories[chat_id]) > MAX_HISTORY_LENGTH:
        chat_histories[chat_id] = chat_histories[chat_id][-MAX_HISTORY_LENGTH:]

    try:
        # Отправляем сообщение о начале обработки
        processing_message = await update.message.reply_text(
            PROCESSING_MESSAGE,
            reply_to_message_id=update.message.message_id
        )

        # Получаем ответ от модели
        response = await context.bot_data["client"].generate_chat_response(
            messages=chat_histories[chat_id]
        )

        # Добавляем ответ в историю
        chat_histories[chat_id].append({
            "role": "assistant",
            "content": response
        })

        # Отправляем ответ пользователю
        if len(response) > MAX_MESSAGE_LENGTH:
            # Разбиваем длинные сообщения на части
            for i in range(0, len(response), MAX_MESSAGE_LENGTH):
                chunk = response[i:i + MAX_MESSAGE_LENGTH]
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response)

    except asyncio.TimeoutError:
        logger.error("Timeout при обработке запроса")
        await update.message.reply_text(TIMEOUT_MESSAGE)

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}", exc_info=True)
        await update.message.reply_text(ERROR_MESSAGE)

    finally:
        # Удаляем сообщение о процессе обработки
        try:
            await processing_message.delete()
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение о процессе: {str(e)}")

async def create_application(config) -> Application:
    """
    Создает и настраивает приложение бота
    """
    # Создаем приложение
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Инициализируем клиент Mistral
    client = MistralClient(config.MISTRAL_API_BASE_URL)
    application.bot_data["client"] = client
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))
    
    # Добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    return application

def main():
    """
    Основная функция для запуска бота
    """
    from telegram_bot.config import config
    
    # Создаем и запускаем приложение
    application = asyncio.run(create_application(config))
    
    # Запускаем бота
    application.run_polling()
    
    logger.info("Бот запущен и готов к работе") 