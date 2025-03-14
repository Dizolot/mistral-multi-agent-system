import pytest
import asyncio
from typing import Optional
from src.agents.code_improvement_agent import CodeImprovementAgent, CodeAnalysisResult


# Dummy-адаптер для моделирования работы generate_text
class DummyModelAdapter:
    async def generate_text(self, prompt, max_tokens, temperature, top_p):
        # Возвращаем переданный промпт для тестирования
        return prompt


# Dummy-агент, переопределяющий методы формирования и парсинга промптов
class DummyCodeImprovementAgent(CodeImprovementAgent):
    def _create_analysis_prompt(self, code: str, context: Optional[dict] = None) -> str:
        return f"Analyze: {code}"
    
    def _parse_analysis_response(self, response: str) -> CodeAnalysisResult:
        # Возвращаем тестовый результат анализа кода
        return CodeAnalysisResult(issues=[], suggestions=[], complexity_score=1.0, maintainability_index=1.0)
    
    def _create_improvement_prompt(self, code: str, analysis_result: CodeAnalysisResult, context: Optional[dict] = None) -> str:
        return f"Improve: {code}"
    
    def _parse_improvements_response(self, response: str) -> list:
        return [{"improvement": "dummy improvement"}]
    
    def _create_apply_improvements_prompt(self, code: str, improvements: list, context: Optional[dict] = None) -> str:
        return f"Apply improvements to: {code}"


@pytest.mark.asyncio
async def test_analyze_code():
    dummy_adapter = DummyModelAdapter()
    agent = DummyCodeImprovementAgent(model_adapter=dummy_adapter)
    code = "print('Hello, world!')"
    result = await agent.analyze_code(code)
    assert isinstance(result, CodeAnalysisResult)
    assert result.complexity_score == 1.0


@pytest.mark.asyncio
async def test_suggest_improvements():
    dummy_adapter = DummyModelAdapter()
    agent = DummyCodeImprovementAgent(model_adapter=dummy_adapter)
    code = "print('Hello, world!')"
    # Используем тестовый результат анализа
    analysis_result = CodeAnalysisResult(issues=[], suggestions=[], complexity_score=1.0, maintainability_index=1.0)
    improvements = await agent.suggest_improvements(code, analysis_result)
    assert isinstance(improvements, list)
    assert improvements[0]["improvement"] == "dummy improvement"


@pytest.mark.asyncio
async def test_apply_improvements():
    dummy_adapter = DummyModelAdapter()
    agent = DummyCodeImprovementAgent(model_adapter=dummy_adapter)
    code = "print('Hello, world!')"
    improvements = [{"improvement": "dummy improvement"}]
    improved_code = await agent.apply_improvements(code, improvements)
    assert "Apply improvements" in improved_code 