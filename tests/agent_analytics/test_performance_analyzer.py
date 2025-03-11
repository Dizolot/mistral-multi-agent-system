import os
import pytest
import shutil
import json
from datetime import datetime

# Импортируем модули для тестирования
from multi_agent_system.agent_analytics.performance_analyzer import PerformanceAnalyzer
from multi_agent_system.agent_analytics.data_collector import AgentDataCollector


@pytest.fixture
def test_results_dir():
    """Фикстура для создания и очистки тестовой директории для результатов."""
    path = "test_results"
    # Создаем директорию, если она не существует
    os.makedirs(path, exist_ok=True)
    yield path
    # Очищаем тестовую директорию после тестов
    shutil.rmtree(path)


@pytest.fixture
def test_data_collector():
    """Фикстура для создания тестового экземпляра AgentDataCollector с данными."""
    path = "test_collector_data"
    # Создаем директорию, если она не существует
    os.makedirs(path, exist_ok=True)
    
    # Инициализируем коллектор
    collector = AgentDataCollector(json_dir=path)
    
    # Добавляем тестовые данные
    for i in range(20):
        success = i % 5 != 0  # 80% успешных взаимодействий
        collector.record_interaction(
            user_id=f"user_{i % 5}",
            session_id=f"session_{i}",
            agent_name="test_agent",
            request=f"test request {i}",
            response=f"test response {i}" if success else "Error: Cannot process request",
            processing_time=0.5 + (i % 5) * 0.1,
            is_successful=success,
            metadata={"error": f"error type {i % 3}"} if not success else None
        )
    
    yield collector
    
    # Очищаем тестовую директорию после тестов
    shutil.rmtree(path)


def test_performance_analyzer_init(test_results_dir):
    """Тест инициализации PerformanceAnalyzer."""
    # Тест с параметрами по умолчанию
    analyzer = PerformanceAnalyzer()
    assert analyzer.results_dir is not None
    
    # Тест с пользовательскими параметрами
    analyzer = PerformanceAnalyzer(results_dir=test_results_dir)
    assert test_results_dir in analyzer.results_dir


def test_analyze_agent_performance(test_data_collector, test_results_dir):
    """Тест анализа эффективности агента."""
    analyzer = PerformanceAnalyzer(
        data_collector_instance=test_data_collector,
        results_dir=test_results_dir
    )
    
    # Анализируем производительность
    result = analyzer.analyze_agent_performance("test_agent")
    
    # Проверяем структуру результата
    assert "agent_name" in result
    assert "metrics" in result
    assert "success_rate" in result["metrics"]
    assert "avg_processing_time" in result["metrics"]
    assert "problematic_patterns" in result
    assert "recommendations" in result
    
    # Проверяем корректность значений
    assert result["agent_name"] == "test_agent"
    assert 0.75 <= result["metrics"]["success_rate"] <= 0.85  # 80% успешных взаимодействий
    assert result["metrics"]["avg_processing_time"] > 0


def test_identify_problematic_patterns():
    """Тест выявления проблемных паттернов."""
    analyzer = PerformanceAnalyzer()
    
    # Тестовые данные о неудачных взаимодействиях
    failed_interactions = [
        {"request": "как запустить python скрипт", "is_successful": False, "error": "не найден интерпретатор"},
        {"request": "запусти python script.py", "is_successful": False, "error": "не найден интерпретатор"},
        {"request": "запуск программы на python", "is_successful": False, "error": "не найден интерпретатор"},
        {"request": "анализ данных", "is_successful": False, "error": "недостаточно информации"}
    ]
    
    patterns = analyzer.identify_problematic_patterns(failed_interactions)
    
    # Проверяем результаты
    assert len(patterns) > 0
    # Проверяем, что первый паттерн - самый частый
    assert patterns[0]["frequency"] >= patterns[-1]["frequency"]
    # Проверяем, что самый частый паттерн связан с python
    assert "python" in patterns[0]["keyword"].lower()


def test_generate_recommendations():
    """Тест генерации рекомендаций."""
    analyzer = PerformanceAnalyzer()
    
    # Тестовые данные
    problematic_patterns = [
        {"keyword": "python", "frequency": 3, "percentage": 75.0, "examples": ["запусти python script.py", "как запустить python скрипт"]},
        {"keyword": "данных", "frequency": 1, "percentage": 25.0, "examples": ["анализ данных"]}
    ]
    
    recommendations = analyzer.generate_recommendations(
        agent_name="test_agent",
        success_rate=0.7,
        avg_processing_time=2.5,
        problematic_patterns=problematic_patterns
    )
    
    # Проверяем результаты
    assert len(recommendations) > 0
    # Проверяем, что рекомендации по самым частым проблемам идут в приоритете
    assert any("python" in rec["description"].lower() for rec in recommendations)


def test_save_analysis_result(test_results_dir):
    """Тест сохранения результатов анализа."""
    analyzer = PerformanceAnalyzer(results_dir=test_results_dir)
    
    # Текущая дата для проверки имени файла
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Тестовые данные
    result = {
        "agent_name": "test_agent",
        "metrics": {
            "success_rate": 0.8,
            "avg_processing_time": 1.5
        },
        "problematic_patterns": [
            {"keyword": "test", "frequency": 3, "percentage": 75.0, "examples": []}
        ],
        "recommendations": [
            {"description": "Test recommendation", "priority": "high"}
        ]
    }
    
    # Сохраняем результаты
    analyzer._save_analysis_result(result)
    
    # Проверяем, что файл создан
    expected_file = os.path.join(test_results_dir, f"analysis_test_agent_{date_str}.json")
    assert os.path.exists(expected_file)
    
    # Проверяем содержимое файла
    with open(expected_file, 'r') as f:
        saved_data = json.load(f)
    
    assert saved_data["agent_name"] == "test_agent"
    assert saved_data["metrics"]["success_rate"] == 0.8


def test_analyze_nonexistent_agent():
    """Тест анализа несуществующего агента."""
    analyzer = PerformanceAnalyzer()
    
    # Анализируем несуществующего агента
    result = analyzer.analyze_agent_performance("nonexistent_agent")
    
    # Проверяем результаты
    assert "status" in result
    assert result["status"] == "insufficient_data"
    assert "message" in result
    assert "Недостаточно данных" in result["message"]


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 