"""
Интеграционный тест для модуля CodeImprovementAgent.

Этот тест проверяет совместную работу компонентов:
- CodeImprovementAgent
- CodeAnalyzer
- CodeTransformer
- MistralAdapter
- MemoryManager
"""

import pytest
import asyncio
from typing import Dict, Any, Optional

from src.agents.code_improvement_agent import CodeImprovementAgent
from src.agents.code_analyzer import CodeAnalyzer
from src.agents.code_transformer import CodeTransformer
from src.model_service.model_adapter.mistral_adapter import MistralAdapter
from src.core.memory_system.memory_manager import MemoryManager


class TestMistralAdapter:
    """Тестовый адаптер для эмуляции работы модели Mistral."""
    
    async def generate_text(
        self, 
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """Эмулирует генерацию текста моделью."""
        # Добавляем задержку для имитации сетевого запроса
        await asyncio.sleep(0.1)
        
        # Возвращаем разные ответы в зависимости от типа запроса
        if 'Анализ' in prompt or 'анализ' in prompt:
            return f"""
            Анализ кода:
            - Сложность: низкая
            - Проблемы:
              - Отсутствие комментариев
              - Длинные строки кода
            - Рекомендации:
              - Добавить документацию
              - Разбить длинные функции
            
            Оценка сложности: 2.5
            Оценка поддерживаемости: 3.7
            """
        elif 'улучшени' in prompt.lower() or 'рекомендац' in prompt.lower():
            return f"""
            Предлагаю следующие улучшения:
            
            1. Добавить документацию:
               - Добавить docstrings к функциям
               - Пояснить параметры и возвращаемые значения
               
            2. Улучшить форматирование:
               - Разбить длинные строки
               - Добавить отступы для улучшения читаемости
            """
        else:
            return f"""
            Улучшенный код:
            
            ```python
            def hello_world():
                '''
                Функция для вывода приветствия.
                
                Returns:
                    None
                '''
                print("Hello, World!")
                # Разбитая на несколько строк длинная строка кода
                # для лучшей читаемости и соответствия стандартам PEP 8
            ```
            """


@pytest.mark.asyncio
async def test_code_improvement_agent_integration():
    """
    Тестирует интеграцию между CodeImprovementAgent и его зависимостями.
    """
    # Подготовка
    test_code = """
    def hello_world():
        print("Hello, World!")
        # Это очень длинная строка кода, которая нарушает стандарты форматирования PEP 8 и делает код менее читаемым для других разработчиков
    """
    
    # Инициализация компонентов
    model_adapter = TestMistralAdapter()
    memory_manager = MemoryManager()
    
    # Создание агента улучшения кода
    agent = CodeImprovementAgent(
        model_adapter=model_adapter,
        memory_manager=memory_manager,
        config={
            "max_context_length": 4000,
            "temperature": 0.5,
            "top_p": 0.8
        }
    )
    
    # Проверка анализа кода
    analysis_result = await agent.analyze_code(test_code)
    
    # Проверка результатов
    assert hasattr(analysis_result, 'issues')
    assert hasattr(analysis_result, 'suggestions')
    assert hasattr(analysis_result, 'complexity_score')
    assert hasattr(analysis_result, 'maintainability_index')
    
    # Генерация предложений по улучшению
    suggestions = await agent.suggest_improvements(
        code=test_code,
        analysis_result=analysis_result
    )
    
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    
    # Применение улучшений
    improved_code = await agent.apply_improvements(
        code=test_code,
        improvements=suggestions
    )
    
    assert isinstance(improved_code, str)
    assert improved_code != test_code  # Код должен измениться


@pytest.mark.asyncio
async def test_end_to_end_code_improvement():
    """
    Комплексный сквозной тест процесса улучшения кода.
    """
    # Подготовка
    test_code = """
    def calculate_sum(a, b):
        return a + b
    """
    
    # Инициализация компонентов
    model_adapter = TestMistralAdapter()
    memory_manager = MemoryManager()
    
    # Создание агента улучшения кода
    agent = CodeImprovementAgent(
        model_adapter=model_adapter,
        memory_manager=memory_manager
    )
    
    # Выполнение полного цикла улучшения кода
    analysis_result = await agent.analyze_code(test_code)
    suggestions = await agent.suggest_improvements(
        code=test_code,
        analysis_result=analysis_result
    )
    improved_code = await agent.apply_improvements(
        code=test_code,
        improvements=suggestions
    )
    
    # Проверка, что все этапы обработки выполнены успешно
    assert analysis_result is not None
    assert suggestions is not None
    assert improved_code is not None
    
    # Проверка логов
    # Здесь можно добавить проверку логов, если это необходимо 