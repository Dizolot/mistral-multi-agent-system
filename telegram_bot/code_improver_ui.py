"""
Модуль для обработки запросов на улучшение кода в Telegram-боте.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.agents.code_improvement_agent import CodeImprovementAgent, CodeAnalysisResult
from src.model_service.model_adapter.mistral_adapter import MistralAdapter
from src.core.memory_system.memory_manager import MemoryManager

# Настройка логирования
logger = logging.getLogger(__name__)

class CodeImproverUI:
    """
    Класс для взаимодействия с пользователем через Telegram
    для улучшения кода.
    """
    
    def __init__(
        self,
        model_adapter: MistralAdapter,
        memory_manager: Optional[MemoryManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Инициализация интерфейса улучшения кода.
        
        Args:
            model_adapter: Адаптер для работы с моделью Mistral
            memory_manager: Менеджер памяти для сохранения контекста
            config: Конфигурация интерфейса
        """
        self.config = config or {}
        
        # Создаем экземпляр агента для улучшения кода
        self.improvement_agent = CodeImprovementAgent(
            model_adapter=model_adapter,
            memory_manager=memory_manager,
            config=self.config.get("agent_config", {})
        )
        
        # Хранилище для кода пользователей
        self.user_code: Dict[int, Dict[str, Any]] = {}
        
        logger.info("CodeImproverUI initialized")
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /analyze - анализирует предоставленный код
        """
        if not update.effective_chat or not update.message:
            return
        
        chat_id = update.effective_chat.id
        user_message = update.message.text
        
        # Проверяем, если текст сообщения содержит только команду
        if user_message.strip() == "/analyze":
            await update.message.reply_text(
                "Пожалуйста, предоставьте код для анализа. Формат: /analyze ```язык\nваш_код```"
            )
            return
        
        # Извлекаем код из сообщения
        code_match = re.search(r'```(?:(\w+)\n)?([\s\S]+?)```', user_message)
        if not code_match:
            await update.message.reply_text(
                "Код должен быть обрамлен в тройные кавычки (```). Формат: /analyze ```язык\nваш_код```"
            )
            return
        
        language = code_match.group(1) or "python"  # По умолчанию Python
        code = code_match.group(2)
        
        # Уведомляем пользователя о начале анализа
        processing_message = await update.message.reply_text(
            f"Анализирую ваш код на языке {language}. Это может занять некоторое время..."
        )
        
        try:
            # Анализируем код
            context_info = {"language": language}
            analysis_result = await self.improvement_agent.analyze_code(code, context_info)
            
            # Сохраняем код и результаты анализа
            self.user_code[chat_id] = {
                "code": code,
                "language": language,
                "analysis_result": analysis_result
            }
            
            # Формируем сообщение с результатами анализа
            response = self._format_analysis_result(analysis_result, language)
            
            # Создаем клавиатуру для дальнейших действий
            keyboard = [
                [InlineKeyboardButton("Предложить улучшения", callback_data="suggest_improvements")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем результат
            await processing_message.edit_text(response, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error analyzing code: {e}", exc_info=True)
            await processing_message.edit_text(
                f"Произошла ошибка при анализе кода: {str(e)}\n"
                "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
            )
    
    async def suggest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /suggest - предлагает улучшения для кода
        """
        if not update.effective_chat or not update.message:
            return
        
        chat_id = update.effective_chat.id
        
        # Проверяем, есть ли сохраненный код и результаты анализа
        if chat_id not in self.user_code or "analysis_result" not in self.user_code[chat_id]:
            await update.message.reply_text(
                "Сначала выполните анализ кода с помощью команды /analyze."
            )
            return
        
        processing_message = await update.message.reply_text(
            "Генерирую предложения по улучшению кода. Это может занять некоторое время..."
        )
        
        try:
            # Получаем сохраненные данные
            data = self.user_code[chat_id]
            code = data["code"]
            language = data["language"]
            analysis_result = data["analysis_result"]
            
            # Получаем предложения по улучшению
            context_info = {"language": language}
            improvements = await self.improvement_agent.suggest_improvements(
                code, analysis_result, context_info
            )
            
            # Сохраняем предложения
            self.user_code[chat_id]["improvements"] = improvements
            
            # Формируем сообщение с предложениями
            response = self._format_improvement_suggestions(improvements, language)
            
            # Создаем клавиатуру для дальнейших действий
            keyboard = [
                [InlineKeyboardButton("Применить улучшения", callback_data="apply_improvements")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем результат
            await processing_message.edit_text(response, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error suggesting improvements: {e}", exc_info=True)
            await processing_message.edit_text(
                f"Произошла ошибка при генерации предложений: {str(e)}\n"
                "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
            )
    
    async def improve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /improve - анализирует и улучшает код одним действием
        """
        if not update.effective_chat or not update.message:
            return
        
        chat_id = update.effective_chat.id
        user_message = update.message.text
        
        # Проверяем, если текст сообщения содержит только команду
        if user_message.strip() == "/improve":
            await update.message.reply_text(
                "Пожалуйста, предоставьте код для улучшения. Формат: /improve ```язык\nваш_код```"
            )
            return
        
        # Извлекаем код из сообщения
        code_match = re.search(r'```(?:(\w+)\n)?([\s\S]+?)```', user_message)
        if not code_match:
            await update.message.reply_text(
                "Код должен быть обрамлен в тройные кавычки (```). Формат: /improve ```язык\nваш_код```"
            )
            return
        
        language = code_match.group(1) or "python"  # По умолчанию Python
        code = code_match.group(2)
        
        # Уведомляем пользователя о начале анализа
        processing_message = await update.message.reply_text(
            f"Анализирую и улучшаю ваш код на языке {language}. Это может занять некоторое время..."
        )
        
        try:
            # Анализируем код
            context_info = {"language": language}
            analysis_result = await self.improvement_agent.analyze_code(code, context_info)
            
            # Получаем предложения по улучшению
            improvements = await self.improvement_agent.suggest_improvements(
                code, analysis_result, context_info
            )
            
            # Применяем улучшения
            improved_code = await self.improvement_agent.apply_improvements(
                code, improvements, context_info
            )
            
            # Сохраняем код, результаты анализа и улучшения
            self.user_code[chat_id] = {
                "code": code,
                "language": language,
                "analysis_result": analysis_result,
                "improvements": improvements,
                "improved_code": improved_code
            }
            
            # Формируем сообщение с результатами
            response = (
                f"✅ Код успешно улучшен!\n\n"
                f"Было выявлено проблем: {len(analysis_result.issues)}\n"
                f"Было предложено улучшений: {len(improvements)}\n\n"
                f"Улучшенный код:\n```{language}\n{improved_code}```\n\n"
                f"Чтобы увидеть подробный анализ, используйте команду /analysis"
            )
            
            # Отправляем результат
            await processing_message.edit_text(response)
            
        except Exception as e:
            logger.error(f"Error improving code: {e}", exc_info=True)
            await processing_message.edit_text(
                f"Произошла ошибка при улучшении кода: {str(e)}\n"
                "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
            )
    
    async def diff_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /diff - показывает разницу между оригинальным и улучшенным кодом
        """
        if not update.effective_chat or not update.message:
            return
        
        chat_id = update.effective_chat.id
        
        # Проверяем, есть ли сохраненный и улучшенный код
        if (chat_id not in self.user_code or 
            "code" not in self.user_code[chat_id] or 
            "improved_code" not in self.user_code[chat_id]):
            await update.message.reply_text(
                "Сначала выполните улучшение кода с помощью команды /improve."
            )
            return
        
        try:
            # Получаем сохраненные данные
            data = self.user_code[chat_id]
            original_code = data["code"]
            improved_code = data["improved_code"]
            language = data["language"]
            
            # Формируем сообщение с разницей
            response = self._format_code_diff(original_code, improved_code, language)
            
            # Отправляем результат
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error showing diff: {e}", exc_info=True)
            await update.message.reply_text(
                f"Произошла ошибка при отображении разницы: {str(e)}\n"
                "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
            )
    
    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик нажатий на кнопки
        """
        if not update.callback_query or not update.effective_chat:
            return
        
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        callback_data = query.data
        
        if callback_data == "suggest_improvements" and chat_id in self.user_code:
            # Симулируем команду /suggest
            context.args = []
            class TempMessage:
                text = "/suggest"
            update.message = TempMessage()
            await self.suggest_command(update, context)
        
        elif callback_data == "apply_improvements" and chat_id in self.user_code:
            # Применяем улучшения
            await query.edit_message_text(
                "Применяю улучшения к коду. Это может занять некоторое время..."
            )
            
            try:
                # Получаем сохраненные данные
                data = self.user_code[chat_id]
                code = data["code"]
                language = data["language"]
                improvements = data.get("improvements", [])
                
                if not improvements:
                    await query.edit_message_text(
                        "Нет сохраненных предложений по улучшению. Пожалуйста, выполните команду /suggest сначала."
                    )
                    return
                
                # Применяем улучшения
                context_info = {"language": language}
                improved_code = await self.improvement_agent.apply_improvements(
                    code, improvements, context_info
                )
                
                # Сохраняем улучшенный код
                self.user_code[chat_id]["improved_code"] = improved_code
                
                # Формируем сообщение с результатами
                response = (
                    f"✅ Код успешно улучшен!\n\n"
                    f"Улучшенный код:\n```{language}\n{improved_code}```\n\n"
                    f"Чтобы увидеть разницу между оригинальным и улучшенным кодом, используйте команду /diff"
                )
                
                # Отправляем результат
                await query.edit_message_text(response)
                
            except Exception as e:
                logger.error(f"Error applying improvements: {e}", exc_info=True)
                await query.edit_message_text(
                    f"Произошла ошибка при применении улучшений: {str(e)}\n"
                    "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
                )
    
    def _format_analysis_result(self, result: CodeAnalysisResult, language: str) -> str:
        """
        Форматирует результат анализа кода для отображения в Telegram.
        
        Args:
            result: Результат анализа кода
            language: Язык программирования
            
        Returns:
            str: Отформатированное сообщение
        """
        issues_count = len(result.issues)
        suggestions_count = len(result.suggestions)
        
        response = f"📊 Результаты анализа кода на языке {language}:\n\n"
        
        # Добавляем метрики
        response += f"🔍 Метрики кода:\n"
        response += f"- Оценка сложности: {result.complexity_score:.2f}/10\n"
        response += f"- Индекс поддерживаемости: {result.maintainability_index:.2f}/100\n\n"
        
        # Добавляем проблемы
        if issues_count > 0:
            response += f"⚠️ Выявленные проблемы ({issues_count}):\n"
            for i, issue in enumerate(result.issues[:5], 1):  # Показываем первые 5 проблем
                response += f"{i}. {issue['description']}\n"
            
            if issues_count > 5:
                response += f"... и еще {issues_count - 5} проблем(ы)\n"
            response += "\n"
        else:
            response += "✅ Проблем не выявлено\n\n"
        
        # Добавляем предложения
        if suggestions_count > 0:
            response += f"💡 Предложения по улучшению ({suggestions_count}):\n"
            for i, suggestion in enumerate(result.suggestions[:3], 1):  # Показываем первые 3 предложения
                response += f"{i}. {suggestion['description']}\n"
            
            if suggestions_count > 3:
                response += f"... и еще {suggestions_count - 3} предложений(я)\n"
        else:
            response += "🔄 Предложений по улучшению нет\n"
        
        return response
    
    def _format_improvement_suggestions(self, improvements: List[Dict[str, Any]], language: str) -> str:
        """
        Форматирует предложения по улучшению кода для отображения в Telegram.
        
        Args:
            improvements: Список предложений по улучшению
            language: Язык программирования
            
        Returns:
            str: Отформатированное сообщение
        """
        if not improvements:
            return "Не найдено предложений по улучшению кода."
        
        response = f"💡 Предложения по улучшению кода на языке {language}:\n\n"
        
        # Добавляем предложения
        for i, improvement in enumerate(improvements, 1):
            priority = improvement.get("priority", "medium").upper()
            priority_emoji = "🔴" if priority == "HIGH" else "🟡" if priority == "MEDIUM" else "🟢"
            
            response += f"{i}. {priority_emoji} {improvement['description']}\n"
            if 'reasoning' in improvement:
                response += f"   📝 Обоснование: {improvement['reasoning']}\n"
            if 'before_snippet' in improvement and 'after_snippet' in improvement:
                response += f"   ⚙️ Пример изменения:\n"
                response += f"   Было:\n```{language}\n{improvement['before_snippet']}```\n"
                response += f"   Стало:\n```{language}\n{improvement['after_snippet']}```\n"
            response += "\n"
        
        response += "Чтобы применить эти улучшения, нажмите на кнопку ниже."
        
        return response
    
    def _format_code_diff(self, original_code: str, improved_code: str, language: str) -> str:
        """
        Форматирует разницу между оригинальным и улучшенным кодом для отображения в Telegram.
        
        Args:
            original_code: Оригинальный код
            improved_code: Улучшенный код
            language: Язык программирования
            
        Returns:
            str: Отформатированное сообщение
        """
        response = f"📊 Сравнение оригинального и улучшенного кода:\n\n"
        
        response += f"Оригинальный код:\n```{language}\n{original_code}```\n\n"
        response += f"Улучшенный код:\n```{language}\n{improved_code}```\n"
        
        return response 