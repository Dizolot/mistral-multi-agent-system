"""
Модульные тесты для интерфейса улучшения кода в Telegram-боте.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List

from telegram_bot.code_improver_ui import CodeImproverUI
from src.agents.code_improvement_agent import CodeAnalysisResult


class TestCodeImproverUI:
    """
    Тесты для класса CodeImproverUI.
    """
    
    @pytest.fixture
    def mock_model_adapter(self):
        """Создает mock для адаптера модели."""
        adapter = AsyncMock()
        adapter.generate_text = AsyncMock(return_value="Сгенерированный текст")
        return adapter
    
    @pytest.fixture
    def mock_analysis_result(self):
        """Создает mock для результата анализа кода."""
        result = MagicMock(spec=CodeAnalysisResult)
        result.issues = [
            {"id": 1, "description": "Проблема 1", "priority": "high"},
            {"id": 2, "description": "Проблема 2", "priority": "medium"}
        ]
        result.suggestions = [
            {"id": 1, "description": "Предложение 1", "priority": "high"},
            {"id": 2, "description": "Предложение 2", "priority": "medium"}
        ]
        result.complexity_score = 7.5
        result.maintainability_index = 65.0
        return result
    
    @pytest.fixture
    def mock_improvements(self):
        """Создает mock для списка улучшений."""
        return [
            {
                "id": 1, 
                "description": "Улучшение 1", 
                "priority": "high",
                "reasoning": "Причина 1",
                "before_snippet": "def old_func():\n    pass",
                "after_snippet": "def improved_func():\n    return True"
            },
            {
                "id": 2, 
                "description": "Улучшение 2", 
                "priority": "medium"
            }
        ]
    
    @pytest.fixture
    def code_improver_ui(self, mock_model_adapter):
        """Создает экземпляр CodeImproverUI с mock адаптером."""
        return CodeImproverUI(
            model_adapter=mock_model_adapter,
            config={"agent_config": {"temperature": 0.7}}
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, code_improver_ui, mock_model_adapter):
        """Тест инициализации CodeImproverUI."""
        assert code_improver_ui.improvement_agent is not None
        assert code_improver_ui.improvement_agent.model_adapter == mock_model_adapter
        assert isinstance(code_improver_ui.user_code, dict)
        assert len(code_improver_ui.user_code) == 0
    
    @pytest.mark.asyncio
    async def test_format_analysis_result(self, code_improver_ui, mock_analysis_result):
        """Тест форматирования результатов анализа."""
        formatted = code_improver_ui._format_analysis_result(mock_analysis_result, "python")
        
        # Проверяем наличие ключевой информации в отформатированном результате
        assert "Результаты анализа кода на языке python" in formatted
        assert "Оценка сложности: 7.50/10" in formatted
        assert "Индекс поддерживаемости: 65.00/100" in formatted
        assert "Выявленные проблемы (2)" in formatted
        assert "Проблема 1" in formatted
        assert "Проблема 2" in formatted
        assert "Предложения по улучшению (2)" in formatted
        assert "Предложение 1" in formatted
        assert "Предложение 2" in formatted
    
    @pytest.mark.asyncio
    async def test_format_improvement_suggestions(self, code_improver_ui, mock_improvements):
        """Тест форматирования предложений по улучшению."""
        formatted = code_improver_ui._format_improvement_suggestions(mock_improvements, "python")
        
        # Проверяем наличие ключевой информации в отформатированном результате
        assert "Предложения по улучшению кода на языке python" in formatted
        assert "Улучшение 1" in formatted
        assert "Улучшение 2" in formatted
        assert "Обоснование: Причина 1" in formatted
        assert "Было:" in formatted
        assert "def old_func():" in formatted
        assert "Стало:" in formatted
        assert "def improved_func():" in formatted
        assert "Чтобы применить эти улучшения" in formatted
    
    @pytest.mark.asyncio
    async def test_format_code_diff(self, code_improver_ui):
        """Тест форматирования разницы между оригинальным и улучшенным кодом."""
        original_code = "def old_func():\n    pass"
        improved_code = "def improved_func():\n    return True"
        
        formatted = code_improver_ui._format_code_diff(original_code, improved_code, "python")
        
        # Проверяем наличие ключевой информации в отформатированном результате
        assert "Сравнение оригинального и улучшенного кода" in formatted
        assert "Оригинальный код:" in formatted
        assert original_code in formatted
        assert "Улучшенный код:" in formatted
        assert improved_code in formatted
        
    @pytest.mark.asyncio
    async def test_analyze_command_with_valid_code(self, code_improver_ui, mock_analysis_result):
        """Тест команды /analyze с валидным кодом."""
        # Подготавливаем моки
        update = AsyncMock()
        update.effective_chat.id = 12345
        update.message.text = "/analyze ```python\ndef test():\n    pass\n```"
        
        context = MagicMock()
        
        # Подменяем метод analyze_code
        code_improver_ui.improvement_agent.analyze_code = AsyncMock(return_value=mock_analysis_result)
        
        # Вызываем метод
        await code_improver_ui.analyze_command(update, context)
        
        # Проверяем, что метод analyze_code был вызван правильно
        code_improver_ui.improvement_agent.analyze_code.assert_called_once()
        assert "def test():" in code_improver_ui.improvement_agent.analyze_code.call_args[0][0]
        
        # Проверяем, что код был сохранен
        assert 12345 in code_improver_ui.user_code
        assert code_improver_ui.user_code[12345]["code"] == "def test():\n    pass\n"
        assert code_improver_ui.user_code[12345]["language"] == "python"
        
        # Проверяем, что сообщение было отправлено
        update.message.reply_text.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_improve_command_end_to_end(self, code_improver_ui, mock_analysis_result, mock_improvements):
        """Интеграционный тест команды /improve."""
        # Подготавливаем моки
        update = AsyncMock()
        update.effective_chat.id = 12345
        update.message.text = "/improve ```python\ndef test():\n    pass\n```"
        
        context = MagicMock()
        
        # Подменяем методы агента
        code_improver_ui.improvement_agent.analyze_code = AsyncMock(return_value=mock_analysis_result)
        code_improver_ui.improvement_agent.suggest_improvements = AsyncMock(return_value=mock_improvements)
        code_improver_ui.improvement_agent.apply_improvements = AsyncMock(return_value="def improved_test():\n    return True\n")
        
        # Вызываем метод
        await code_improver_ui.improve_command(update, context)
        
        # Проверяем, что все методы агента были вызваны правильно
        code_improver_ui.improvement_agent.analyze_code.assert_called_once()
        code_improver_ui.improvement_agent.suggest_improvements.assert_called_once()
        code_improver_ui.improvement_agent.apply_improvements.assert_called_once()
        
        # Проверяем, что данные были сохранены
        assert 12345 in code_improver_ui.user_code
        assert code_improver_ui.user_code[12345]["code"] == "def test():\n    pass\n"
        assert code_improver_ui.user_code[12345]["language"] == "python"
        assert code_improver_ui.user_code[12345]["improved_code"] == "def improved_test():\n    return True\n"
        
        # Проверяем, что сообщение было отправлено
        update.message.reply_text.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 