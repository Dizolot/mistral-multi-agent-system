"""
Основной модуль Telegram-бота для взаимодействия с моделью Mistral.
Обрабатывает сообщения пользователей и отправляет запросы к API.
"""

import os
import logging
import asyncio
import psutil
import time
import sys
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

from telegram_bot.config import (
    TELEGRAM_TOKEN, ADMIN_CHAT_ID, MISTRAL_API_URL, ORCHESTRATOR_API_URL,
    DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS,
    REQUEST_TIMEOUT, POLL_INTERVAL, MAX_MESSAGE_LENGTH,
    WELCOME_MESSAGE, HELP_MESSAGE, RESET_MESSAGE,
    PROCESSING_MESSAGE, ERROR_MESSAGE, TIMEOUT_MESSAGE,
    USE_ORCHESTRATOR
)
from telegram_bot.mistral_client import MistralClient
from telegram_bot.conversation_manager import ConversationManager
from telegram_bot.orchestrator_adapter import OrchestratorAdapter, FallbackHandler

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

# Инициализация клиентов и менеджера диалогов
mistral_client = MistralClient(base_url=MISTRAL_API_URL)
conversation_manager = ConversationManager()

# Инициализация адаптера оркестратора, если используется
orchestrator_adapter = OrchestratorAdapter(api_url=ORCHESTRATOR_API_URL) if USE_ORCHESTRATOR else None
fallback_handler = FallbackHandler(mistral_client)

# Режим работы (прямой или через оркестратор)
bot_mode = "orchestrator" if USE_ORCHESTRATOR else "direct"

# Функция для проверки и остановки уже запущенных экземпляров бота
def check_and_kill_duplicate_bots():
    """
    Проверяет наличие других запущенных экземпляров бота 
    и завершает их перед запуском.
    """
    try:
        current_pid = os.getpid()
        current_process = psutil.Process(current_pid)
        bot_processes_found = False
        
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            if process.info['pid'] != current_pid and process.info['name'] == current_process.name():
                cmdline = ' '.join(process.info['cmdline']) if process.info['cmdline'] else ''
                if any(x in cmdline for x in ['run_telegram_bot.py', 'telegram_bot.py']):
                    # Проверяем, не является ли процесс родительским для текущего
                    if process.info['pid'] != os.getppid():
                        logger.warning(f"Найден дубликат процесса бота с PID {process.info['pid']}, завершаем его")
                        try:
                            process.terminate()
                            bot_processes_found = True
                        except psutil.NoSuchProcess:
                            logger.warning(f"Процесс {process.info['pid']} уже завершен")
        
        # Если нашли другие процессы, ждем их завершения
        if bot_processes_found:
            logger.info("Ожидаем завершения других экземпляров бота...")
            time.sleep(2)  # Даем время на корректное завершение
            
        return bot_processes_found
    except Exception as e:
        logger.warning(f"Ошибка при проверке дубликатов бота: {e}")
        return False

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
    
    # Добавляем кнопки переключения режима
    if USE_ORCHESTRATOR:
        keyboard.append([
            InlineKeyboardButton("Режим: Прямой", callback_data="mode_direct"),
            InlineKeyboardButton("Режим: Оркестратор", callback_data="mode_orchestrator")
        ])
    
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

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /mode для переключения режима"""
    global bot_mode
    user_id = update.effective_user.id
    
    # Получаем аргумент команды (если есть)
    args = context.args
    if args and len(args) > 0:
        mode = args[0].lower()
        if mode in ["direct", "orchestrator"]:
            bot_mode = mode
            logger.info(f"Пользователь {user_id} переключил режим на: {bot_mode}")
            await update.message.reply_text(f"Режим работы изменен: {'через оркестратор' if bot_mode == 'orchestrator' else 'прямой'}")
        else:
            await update.message.reply_text("Неверный режим. Доступные режимы: direct, orchestrator")
    else:
        await update.message.reply_text(f"Текущий режим: {'через оркестратор' if bot_mode == 'orchestrator' else 'прямой'}")

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
    
    # Функция обратного вызова для обновления статуса обработки
    async def update_status(status_text: str):
        try:
            # Обновляем сообщение о статусе обработки
            await processing_message.edit_text(f"{status_text}")
            logger.info(f"Обновлен статус для пользователя {user_id}: {status_text}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса: {str(e)}")
    
    try:
        # Выбираем способ обработки в зависимости от режима
        if bot_mode == "orchestrator" and orchestrator_adapter:
            logger.info(f"Обработка через оркестратор для пользователя {user_id}")
            response = await orchestrator_adapter.process_message(user_id, message_text, update_status)
        else:
            logger.info(f"Прямая обработка для пользователя {user_id}")
            response = await fallback_handler.process_message(user_id, message_text, update_status)
        
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
        await update.message.reply_text(f"{ERROR_MESSAGE}: {str(e)}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    global bot_mode
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
    
    elif callback_data == "mode_direct":
        bot_mode = "direct"
        await query.message.reply_text("Режим работы изменен: прямой")
    
    elif callback_data == "mode_orchestrator":
        if USE_ORCHESTRATOR:
            bot_mode = "orchestrator"
            await query.message.reply_text("Режим работы изменен: через оркестратор")
        else:
            await query.message.reply_text("Режим оркестратора недоступен")

def main() -> None:
    """Основная функция для запуска телеграм-бота"""
    
    # Проверяем и останавливаем другие экземпляры бота
    check_and_kill_duplicate_bots()
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("mode", mode_command))
    
    # Добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик нажатий на кнопки
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Обработчик ошибок
    async def error_handler(update, context):
        error = context.error
        try:
            raise error
        except telegram.error.Conflict:
            # Обработка ошибки конфликта
            logger.error("Обнаружен конфликт: другой экземпляр бота использует тот же токен")
            logger.info("Пробуем остановить другие экземпляры бота...")
            check_and_kill_duplicate_bots()
            # Подождем некоторое время и попробуем перезапустить
            logger.info("Ожидаем 10 секунд перед повторной попыткой...")
            import time
            time.sleep(10)
            logger.info("Повторная попытка запуска...")
            return application.run_polling()
        except Exception as e:
            logger.error(f"Необработанная ошибка: {str(e)}")
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info(f"Запуск бота в режиме: {bot_mode}")
    
    # Пробуем запустить бота с обработкой ошибок
    try:
        application.run_polling()
    except telegram.error.Conflict:
        logger.error("Конфликт при запуске бота, возможно другой экземпляр уже запущен")
        logger.info("Пробуем остановить все экземпляры бота и перезапустить...")
        check_and_kill_duplicate_bots()
        # Подождем 10 секунд и повторим попытку
        import time
        time.sleep(10)
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}")

if __name__ == "__main__":
    main() 