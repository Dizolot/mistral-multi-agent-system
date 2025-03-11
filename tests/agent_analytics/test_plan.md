# План тестирования системы аналитики агентов

## 1. Модульное тестирование

### 1.1. Тестирование DataCollector

#### 1.1.1. Тестирование конструктора
- **ID теста:** DC-INIT-001
- **Цель:** Проверить корректность инициализации DataCollector с различными параметрами
- **Входные данные:** Различные параметры конструктора
- **Ожидаемый результат:** Корректная инициализация экземпляра класса

```python
def test_data_collector_init():
    # Тест с параметрами по умолчанию
    collector = DataCollector()
    assert collector.storage_type == "json"
    assert collector.storage_path == "agent_analytics/data"
    
    # Тест с пользовательскими параметрами
    collector = DataCollector(storage_type="sqlite", storage_path="custom/path")
    assert collector.storage_type == "sqlite"
    assert collector.storage_path == "custom/path"
```

#### 1.1.2. Тестирование сохранения взаимодействий
- **ID теста:** DC-STORE-001
- **Цель:** Проверить корректность сохранения данных о взаимодействиях
- **Входные данные:** Тестовое взаимодействие с агентом
- **Ожидаемый результат:** Данные корректно сохраняются и могут быть извлечены

```python
def test_store_interaction():
    collector = DataCollector(storage_path="test/data")
    interaction = {
        "user_id": "test_user",
        "agent_name": "test_agent",
        "request": "test request",
        "response": "test response",
        "timestamp": "2025-01-01T12:00:00",
        "success": True
    }
    collector.store_interaction(interaction)
    
    # Проверяем, что данные сохранены
    interactions = collector.get_agent_interactions("test_agent")
    assert len(interactions) == 1
    assert interactions[0]["user_id"] == "test_user"
    assert interactions[0]["request"] == "test request"
```

#### 1.1.3. Тестирование получения взаимодействий
- **ID теста:** DC-GET-001
- **Цель:** Проверить корректность получения данных о взаимодействиях с фильтрацией
- **Входные данные:** Набор тестовых взаимодействий
- **Ожидаемый результат:** Данные корректно фильтруются по запрошенным критериям

```python
def test_get_interactions_with_filters():
    collector = DataCollector(storage_path="test/data")
    # Очистка данных для теста
    collector._clear_data()
    
    # Добавление тестовых данных
    for i in range(10):
        interaction = {
            "user_id": f"user_{i % 3}",
            "agent_name": f"agent_{i % 2}",
            "request": f"request {i}",
            "response": f"response {i}",
            "timestamp": f"2025-01-{(i % 30) + 1:02d}T12:00:00",
            "success": i % 2 == 0
        }
        collector.store_interaction(interaction)
    
    # Проверка фильтрации по агенту
    agent0_interactions = collector.get_agent_interactions("agent_0")
    assert len(agent0_interactions) == 5
    
    # Проверка фильтрации по пользователю
    user1_interactions = collector.get_user_interactions("user_1")
    assert len(user1_interactions) == 3
    
    # Проверка фильтрации по дате
    jan_interactions = collector.get_interactions_by_date_range(
        start_date="2025-01-01",
        end_date="2025-01-15"
    )
    assert len(jan_interactions) == 10  # Все взаимодействия в январе
    
    # Проверка фильтрации по успешности
    success_interactions = collector.get_interactions_by_success(success=True)
    assert len(success_interactions) == 5
```

### 1.2. Тестирование PerformanceAnalyzer

#### 1.2.1. Тестирование анализа эффективности агента
- **ID теста:** PA-ANALYZE-001
- **Цель:** Проверить корректность анализа эффективности агента
- **Входные данные:** Тестовые данные о взаимодействиях с агентом
- **Ожидаемый результат:** Корректно рассчитанные метрики и выявленные паттерны

```python
def test_analyze_agent_performance():
    # Создаем тестовый экземпляр DataCollector с тестовыми данными
    collector = create_test_data_collector()
    
    # Инициализируем PerformanceAnalyzer
    analyzer = PerformanceAnalyzer(data_collector_instance=collector, results_dir="test/results")
    
    # Анализируем производительность
    result = analyzer.analyze_agent_performance("test_agent")
    
    # Проверяем наличие ожидаемых ключей в результате
    assert "success_rate" in result
    assert "avg_processing_time" in result
    assert "problematic_patterns" in result
    assert "recommendations" in result
    
    # Проверяем корректность расчетов
    # Предполагаем, что в тестовых данных 70% успешных взаимодействий
    assert 0.65 <= result["success_rate"] <= 0.75
```

#### 1.2.2. Тестирование выявления проблемных паттернов
- **ID теста:** PA-PATTERNS-001
- **Цель:** Проверить корректность выявления проблемных паттернов
- **Входные данные:** Набор неудачных взаимодействий
- **Ожидаемый результат:** Корректно выявленные паттерны с частотой встречаемости

```python
def test_identify_problematic_patterns():
    analyzer = PerformanceAnalyzer()
    
    # Тестовые данные о неудачных взаимодействиях
    failed_interactions = [
        {"request": "как запустить python скрипт", "success": False, "error": "не найден интерпретатор"},
        {"request": "запусти python script.py", "success": False, "error": "не найден интерпретатор"},
        {"request": "запуск программы на python", "success": False, "error": "не найден интерпретатор"},
        {"request": "анализ данных", "success": False, "error": "недостаточно информации"}
    ]
    
    patterns = analyzer.identify_problematic_patterns(failed_interactions)
    
    # Проверяем, что обнаружены паттерны
    assert len(patterns) > 0
    # Проверяем, что самый частый паттерн связан с интерпретатором Python
    assert "интерпретатор" in patterns[0]["description"].lower()
    assert patterns[0]["frequency"] >= 3
```

#### 1.2.3. Тестирование генерации рекомендаций
- **ID теста:** PA-RECOMMEND-001
- **Цель:** Проверить корректность генерации рекомендаций
- **Входные данные:** Данные об эффективности агента и проблемных паттернах
- **Ожидаемый результат:** Осмысленные рекомендации, соответствующие выявленным проблемам

```python
def test_generate_recommendations():
    analyzer = PerformanceAnalyzer()
    
    # Тестовые данные
    problematic_patterns = [
        {"description": "Проблемы с интерпретатором Python", "frequency": 3},
        {"description": "Недостаточно информации в запросе", "frequency": 1}
    ]
    
    recommendations = analyzer.generate_recommendations(
        agent_name="test_agent",
        success_rate=0.7,
        avg_processing_time=2.5,
        problematic_patterns=problematic_patterns
    )
    
    # Проверяем наличие рекомендаций
    assert len(recommendations) > 0
    # Проверяем, что рекомендации связаны с выявленными проблемами
    assert any("python" in rec["description"].lower() for rec in recommendations)
```

### 1.3. Тестирование MetricsEvaluator

#### 1.3.1. Тестирование оценки качества ответа
- **ID теста:** ME-EVALUATE-001
- **Цель:** Проверить корректность оценки качества ответа
- **Входные данные:** Запрос и ответ агента
- **Ожидаемый результат:** Корректный расчет метрик качества

```python
def test_evaluate_response_quality():
    evaluator = MetricsEvaluator()
    
    # Тестовые данные
    request = "Какая погода в Москве сегодня?"
    good_response = "Сегодня в Москве пасмурно, температура около 15 градусов Цельсия. Возможны небольшие осадки во второй половине дня."
    bad_response = "Извините, я не понимаю вопрос."
    
    # Оцениваем хороший ответ
    good_metrics = evaluator.evaluate_response_quality(request, good_response)
    
    # Оцениваем плохой ответ
    bad_metrics = evaluator.evaluate_response_quality(request, bad_response)
    
    # Проверяем результаты
    assert good_metrics["overall_quality"] > bad_metrics["overall_quality"]
    assert good_metrics["relevance"] > bad_metrics["relevance"]
    assert good_metrics["coherence"] > 0.5
```

#### 1.3.2. Тестирование оценки улучшений
- **ID теста:** ME-IMPROVEMENT-001
- **Цель:** Проверить корректность оценки улучшений между версиями агента
- **Входные данные:** Наборы старых и новых ответов агента
- **Ожидаемый результат:** Корректная оценка наличия и масштаба улучшений

```python
def test_evaluate_agent_improvement():
    evaluator = MetricsEvaluator()
    
    # Тестовые данные
    old_responses = [
        {"request": "Как запустить сервер?", "response": "Используйте команду start.", "metrics": {"relevance": 0.5, "coherence": 0.6}},
        {"request": "Как остановить сервер?", "response": "Используйте команду stop.", "metrics": {"relevance": 0.5, "coherence": 0.6}}
    ]
    
    new_responses = [
        {"request": "Как запустить сервер?", "response": "Для запуска сервера используйте команду `server start` в терминале.", "metrics": {"relevance": 0.8, "coherence": 0.7}},
        {"request": "Как остановить сервер?", "response": "Чтобы остановить сервер, выполните команду `server stop` в терминале.", "metrics": {"relevance": 0.8, "coherence": 0.7}}
    ]
    
    # Оцениваем улучшения
    improvement = evaluator.evaluate_agent_improvement(old_responses, new_responses)
    
    # Проверяем результаты
    assert improvement["overall_improvement"] > 0
    assert improvement["metrics_changes"]["relevance"] > 0
    assert improvement["metrics_changes"]["coherence"] > 0
    assert len(improvement["improvement_summary"]) > 0
```

## 2. Интеграционное тестирование

### 2.1. Интеграция модулей аналитики

#### 2.1.1. Полный цикл сбора данных, анализа и оценки метрик
- **ID теста:** INT-CYCLE-001
- **Цель:** Проверить корректность взаимодействия модулей аналитики
- **Входные данные:** Набор тестовых взаимодействий с агентами
- **Ожидаемый результат:** Корректная работа всей цепочки аналитики

```python
def test_full_analytics_cycle():
    # Инициализируем компоненты
    collector = DataCollector(storage_path="test/integration/data")
    analyzer = PerformanceAnalyzer(data_collector_instance=collector, results_dir="test/integration/results")
    evaluator = MetricsEvaluator()
    
    # Добавляем тестовые данные
    for i in range(20):
        success = i % 3 != 0  # 2/3 успешных взаимодействий
        interaction = {
            "user_id": f"user_{i % 5}",
            "agent_name": "test_agent",
            "request": f"test request {i}",
            "response": f"test response {i}" if success else "Извините, не могу ответить",
            "timestamp": f"2025-01-{(i % 30) + 1:02d}T12:00:00",
            "success": success,
            "processing_time": 0.5 + (i % 5) * 0.1
        }
        collector.store_interaction(interaction)
    
    # Проводим анализ
    result = analyzer.analyze_agent_performance("test_agent")
    
    # Проверяем результаты
    assert result["success_rate"] == pytest.approx(2/3, 0.1)
    assert len(result["recommendations"]) > 0
    
    # Оцениваем качество ответов
    for i in range(5):
        metrics = evaluator.evaluate_response_quality(f"test request {i}", f"test response {i}")
        assert "overall_quality" in metrics
```

### 2.2. Интеграция с LangChain

#### 2.2.1. Тестирование взаимодействия с модулями LangChain
- **ID теста:** INT-LANGCHAIN-001
- **Цель:** Проверить корректность взаимодействия системы аналитики с LangChain
- **Входные данные:** Тестовые агенты LangChain и запросы к ним
- **Ожидаемый результат:** Корректный сбор и анализ данных о работе агентов LangChain

```python
def test_langchain_agents_integration():
    # Создаем тестовый экземпляр DataCollector
    collector = DataCollector(storage_path="test/integration/langchain_data")
    
    # Создаем тестового агента LangChain
    # Предполагается наличие модуля create_test_langchain_agent
    agent = create_test_langchain_agent("test_agent")
    
    # Выполняем запросы к агенту
    for i in range(10):
        request = f"Test request {i}"
        response = agent.run(request)
        
        # Сохраняем данные о взаимодействии
        interaction = {
            "user_id": "test_user",
            "agent_name": "test_agent",
            "request": request,
            "response": response,
            "timestamp": f"2025-01-{(i % 30) + 1:02d}T12:00:00",
            "success": True,
            "processing_time": 0.5
        }
        collector.store_interaction(interaction)
    
    # Анализируем эффективность
    analyzer = PerformanceAnalyzer(data_collector_instance=collector)
    analysis = analyzer.analyze_agent_performance("test_agent")
    
    # Проверяем результаты
    assert analysis["success_rate"] > 0
```

## 3. Нагрузочное тестирование

### 3.1. Тестирование производительности DataCollector

#### 3.1.1. Тестирование с большим объемом данных
- **ID теста:** PERF-DC-001
- **Цель:** Проверить производительность DataCollector при работе с большим объемом данных
- **Входные данные:** Большое количество (1000+) записей о взаимодействиях
- **Ожидаемый результат:** Приемлемая скорость работы и использование ресурсов

```python
def test_data_collector_large_dataset():
    import time
    
    # Создаем экземпляр DataCollector
    collector = DataCollector(storage_path="test/performance/data")
    
    # Генерируем большой набор тестовых данных
    interactions = []
    for i in range(1000):
        interaction = {
            "user_id": f"user_{i % 50}",
            "agent_name": f"agent_{i % 5}",
            "request": f"request {i}",
            "response": f"response {i}",
            "timestamp": f"2025-01-{(i % 30) + 1:02d}T12:00:00",
            "success": i % 10 != 0,
            "processing_time": 0.5 + (i % 5) * 0.1
        }
        interactions.append(interaction)
    
    # Измеряем время сохранения данных
    start_time = time.time()
    for interaction in interactions:
        collector.store_interaction(interaction)
    save_time = time.time() - start_time
    
    # Измеряем время получения данных
    start_time = time.time()
    result = collector.get_agent_interactions("agent_0")
    retrieval_time = time.time() - start_time
    
    # Проверяем результаты
    print(f"Save time for 1000 interactions: {save_time:.2f} seconds")
    print(f"Retrieval time for agent_0 interactions: {retrieval_time:.2f} seconds")
    
    # Проверяем, что получили правильное количество записей
    assert len(result) == 200  # Для agent_0 должно быть 200 записей
    
    # Проверяем время выполнения (настроить пороги в соответствии с ожиданиями)
    assert save_time < 5.0  # Сохранение 1000 записей должно занимать менее 5 секунд
    assert retrieval_time < 1.0  # Получение данных должно занимать менее 1 секунды
```

### 3.2. Тестирование производительности PerformanceAnalyzer

#### 3.2.1. Тестирование анализа большого объема данных
- **ID теста:** PERF-PA-001
- **Цель:** Проверить производительность PerformanceAnalyzer при анализе большого объема данных
- **Входные данные:** Большое количество (1000+) записей о взаимодействиях
- **Ожидаемый результат:** Приемлемая скорость работы и использование ресурсов

```python
def test_performance_analyzer_large_dataset():
    import time
    
    # Создаем тестовые данные в DataCollector
    collector = DataCollector(storage_path="test/performance/data")
    # Очищаем данные для чистоты эксперимента
    collector._clear_data()
    
    # Генерируем большой набор тестовых данных
    for i in range(1000):
        interaction = {
            "user_id": f"user_{i % 50}",
            "agent_name": "test_agent",
            "request": f"request {i}",
            "response": f"response {i}",
            "timestamp": f"2025-01-{(i % 30) + 1:02d}T12:00:00",
            "success": i % 10 != 0,  # 90% успешных взаимодействий
            "processing_time": 0.5 + (i % 5) * 0.1,
            "error": None if i % 10 != 0 else f"error {i % 5}"
        }
        collector.store_interaction(interaction)
    
    # Создаем анализатор
    analyzer = PerformanceAnalyzer(data_collector_instance=collector)
    
    # Измеряем время анализа
    start_time = time.time()
    analysis = analyzer.analyze_agent_performance("test_agent")
    analysis_time = time.time() - start_time
    
    # Проверяем результаты
    print(f"Analysis time for 1000 interactions: {analysis_time:.2f} seconds")
    
    # Проверка корректности результатов
    assert analysis["success_rate"] == pytest.approx(0.9, 0.05)
    assert len(analysis["problematic_patterns"]) > 0
    
    # Проверка времени выполнения
    assert analysis_time < 10.0  # Анализ должен занимать менее 10 секунд
```

### 3.3. Тестирование производительности MetricsEvaluator

#### 3.3.1. Тестирование оценки большого количества ответов
- **ID теста:** PERF-ME-001
- **Цель:** Проверить производительность MetricsEvaluator при оценке большого количества ответов
- **Входные данные:** Большое количество (100+) пар запрос-ответ
- **Ожидаемый результат:** Приемлемая скорость работы и использование ресурсов

```python
def test_metrics_evaluator_large_dataset():
    import time
    
    # Создаем тестовый экземпляр
    evaluator = MetricsEvaluator()
    
    # Генерируем тестовые данные
    test_data = []
    for i in range(100):
        data = {
            "request": f"Test request {i} with sufficient context to evaluate the relevance and coherence of the response.",
            "response": f"Test response {i} with detailed information addressing the request. This response is designed to be coherent and relevant to the query, providing sufficient detail for meaningful evaluation."
        }
        test_data.append(data)
    
    # Измеряем время оценки
    start_time = time.time()
    metrics_list = []
    for data in test_data:
        metrics = evaluator.evaluate_response_quality(data["request"], data["response"])
        metrics_list.append(metrics)
    evaluation_time = time.time() - start_time
    
    # Проверяем результаты
    print(f"Evaluation time for 100 responses: {evaluation_time:.2f} seconds")
    
    # Проверка корректности результатов
    assert len(metrics_list) == 100
    assert all("overall_quality" in metrics for metrics in metrics_list)
    
    # Проверка времени выполнения
    assert evaluation_time < 30.0  # Оценка должна занимать менее 30 секунд
```

## 4. Тестирование устойчивости к ошибкам

### 4.1. Тестирование обработки некорректных входных данных

#### 4.1.1. Тестирование DataCollector с некорректными данными
- **ID теста:** ERR-DC-001
- **Цель:** Проверить обработку некорректных входных данных в DataCollector
- **Входные данные:** Различные варианты некорректных данных
- **Ожидаемый результат:** Корректная обработка ошибок без критических сбоев

```python
def test_data_collector_invalid_data():
    collector = DataCollector()
    
    # Тест с пустым словарем
    try:
        collector.store_interaction({})
        assert False, "Должно быть выброшено исключение для пустого словаря"
    except ValueError:
        # Ожидаемое поведение
        pass
    
    # Тест с отсутствующими обязательными полями
    try:
        collector.store_interaction({"user_id": "test_user"})
        assert False, "Должно быть выброшено исключение для неполных данных"
    except ValueError:
        # Ожидаемое поведение
        pass
    
    # Тест с некорректными типами данных
    try:
        collector.store_interaction({
            "user_id": 123,  # Должна быть строка
            "agent_name": "test_agent",
            "request": "test",
            "response": "test",
            "timestamp": "2025-01-01T12:00:00",
            "success": "yes"  # Должен быть булев тип
        })
        assert False, "Должно быть выброшено исключение для некорректных типов данных"
    except TypeError:
        # Ожидаемое поведение
        pass
```

#### 4.1.2. Тестирование PerformanceAnalyzer с некорректными данными
- **ID теста:** ERR-PA-001
- **Цель:** Проверить обработку некорректных входных данных в PerformanceAnalyzer
- **Входные данные:** Различные варианты некорректных данных
- **Ожидаемый результат:** Корректная обработка ошибок без критических сбоев

```python
def test_performance_analyzer_invalid_data():
    analyzer = PerformanceAnalyzer()
    
    # Тест с несуществующим агентом
    result = analyzer.analyze_agent_performance("nonexistent_agent")
    # Ожидаем, что результат будет содержать информацию об отсутствии данных
    assert result["success_rate"] == 0
    assert "No data available" in result["error"]
    
    # Тест с недостаточным количеством взаимодействий
    collector = DataCollector()
    # Добавляем всего 5 взаимодействий
    for i in range(5):
        interaction = {
            "user_id": "test_user",
            "agent_name": "test_agent",
            "request": f"request {i}",
            "response": f"response {i}",
            "timestamp": "2025-01-01T12:00:00",
            "success": True
        }
        collector.store_interaction(interaction)
    
    analyzer = PerformanceAnalyzer(data_collector_instance=collector)
    # Устанавливаем min_interactions=10
    result = analyzer.analyze_agent_performance("test_agent", min_interactions=10)
    # Ожидаем, что результат будет содержать информацию о недостаточном количестве данных
    assert "Insufficient data" in result["error"]
```

## 5. Тестирование интеграции с API сервером

### 5.1. Тестирование API эндпоинтов для аналитики

#### 5.1.1. Тестирование эндпоинта анализа производительности агента
- **ID теста:** API-PERF-001
- **Цель:** Проверить корректность работы API эндпоинта для анализа производительности агента
- **Входные данные:** Запрос к API эндпоинту с параметрами агента
- **Ожидаемый результат:** Корректный ответ с результатами анализа

```python
def test_api_performance_analysis():
    import requests
    
    # Предполагается, что API-сервер запущен на localhost:8000
    response = requests.get("http://localhost:8000/api/analytics/performance/test_agent")
    
    # Проверяем статус ответа
    assert response.status_code == 200
    
    # Проверяем структуру ответа
    data = response.json()
    assert "success_rate" in data
    assert "avg_processing_time" in data
    assert "problematic_patterns" in data
    assert "recommendations" in data
```

#### 5.1.2. Тестирование эндпоинта оценки качества ответа
- **ID теста:** API-QUALITY-001
- **Цель:** Проверить корректность работы API эндпоинта для оценки качества ответа
- **Входные данные:** Запрос к API эндпоинту с запросом и ответом для оценки
- **Ожидаемый результат:** Корректный ответ с результатами оценки

```python
def test_api_quality_evaluation():
    import requests
    import json
    
    # Тестовые данные
    payload = {
        "request": "Как настроить сервер?",
        "response": "Для настройки сервера следуйте инструкциям в документации."
    }
    
    # Отправляем запрос
    response = requests.post(
        "http://localhost:8000/api/analytics/evaluate_quality",
        json=payload
    )
    
    # Проверяем статус ответа
    assert response.status_code == 200
    
    # Проверяем структуру ответа
    data = response.json()
    assert "overall_quality" in data
    assert "relevance" in data
    assert "coherence" in data
```

## 6. Авто-тесты для CI/CD

### 6.1. Комплексный тест для CI

#### 6.1.1. Тест для проверки всей функциональности аналитики
- **ID теста:** CI-ALL-001
- **Цель:** Проверить всю функциональность аналитики агентов в едином тесте для CI/CD
- **Входные данные:** Тестовые данные о взаимодействиях с агентами
- **Ожидаемый результат:** Успешное выполнение всех операций

```python
def test_ci_analytics():
    # Создаем экземпляры всех модулей
    collector = DataCollector(storage_path="test/ci/data")
    analyzer = PerformanceAnalyzer(data_collector_instance=collector, results_dir="test/ci/results")
    evaluator = MetricsEvaluator()
    
    # Генерируем тестовые данные
    for i in range(50):
        success = i % 5 != 0  # 80% успешных взаимодействий
        interaction = {
            "user_id": f"user_{i % 10}",
            "agent_name": f"agent_{i % 2}",
            "request": f"request {i}",
            "response": f"response {i}" if success else "Ошибка",
            "timestamp": f"2025-01-{(i % 30) + 1:02d}T12:00:00",
            "success": success,
            "processing_time": 0.5 + (i % 5) * 0.1
        }
        collector.store_interaction(interaction)
    
    # Проверяем все основные функции
    
    # 1. Получение данных
    interactions = collector.get_agent_interactions("agent_0")
    assert len(interactions) == 25
    
    # 2. Анализ производительности
    analysis = analyzer.analyze_agent_performance("agent_0", min_interactions=10)
    assert "success_rate" in analysis
    assert "recommendations" in analysis
    
    # 3. Оценка качества
    metrics = evaluator.evaluate_response_quality("request 1", "response 1")
    assert "overall_quality" in metrics
    
    # 4. Оценка улучшений
    old_responses = [
        {"request": "r1", "response": "old response 1", "metrics": {"relevance": 0.5}},
        {"request": "r2", "response": "old response 2", "metrics": {"relevance": 0.6}}
    ]
    new_responses = [
        {"request": "r1", "response": "new response 1", "metrics": {"relevance": 0.7}},
        {"request": "r2", "response": "new response 2", "metrics": {"relevance": 0.8}}
    ]
    improvement = evaluator.evaluate_agent_improvement(old_responses, new_responses)
    assert improvement["overall_improvement"] > 0
```

## 7. Тестирование совместимости с различными средами

### 7.1. Тестирование с различными версиями Python

#### 7.1.1. Тест совместимости с Python 3.8, 3.9, 3.10, 3.11
- **ID теста:** COMPAT-PY-001
- **Цель:** Проверить совместимость с различными версиями Python
- **Входные данные:** Тестовые запросы в различных средах Python
- **Ожидаемый результат:** Корректная работа во всех поддерживаемых версиях Python

```python
# Тесты выполняются в CI с различными версиями Python
def test_python_compatibility():
    import sys
    
    # Проверка версии Python
    print(f"Running on Python {sys.version}")
    
    # Создаем экземпляры всех модулей
    collector = DataCollector()
    analyzer = PerformanceAnalyzer()
    evaluator = MetricsEvaluator()
    
    # Тестовые данные
    interaction = {
        "user_id": "test_user",
        "agent_name": "test_agent",
        "request": "test request",
        "response": "test response",
        "timestamp": "2025-01-01T12:00:00",
        "success": True
    }
    
    # Проверяем базовые функции
    collector.store_interaction(interaction)
    interactions = collector.get_agent_interactions("test_agent")
    assert len(interactions) == 1
    
    # Тестируем метрики
    metrics = evaluator.evaluate_response_quality("test request", "test response")
    assert "overall_quality" in metrics
```

### 7.2. Тестирование с различными ОС

#### 7.2.1. Тест совместимости с Linux, macOS, Windows
- **ID теста:** COMPAT-OS-001
- **Цель:** Проверить совместимость с различными операционными системами
- **Входные данные:** Тестовые запросы в различных ОС
- **Ожидаемый результат:** Корректная работа во всех поддерживаемых ОС

```python
# Тесты выполняются в CI на различных ОС
def test_os_compatibility():
    import platform
    
    # Проверка ОС
    print(f"Running on {platform.system()} {platform.release()}")
    
    # Создаем экземпляры всех модулей
    collector = DataCollector()
    
    # Проверяем создание и доступ к файлам
    collector.store_interaction({
        "user_id": "test_user",
        "agent_name": "test_agent",
        "request": "test request",
        "response": "test response",
        "timestamp": "2025-01-01T12:00:00",
        "success": True
    })
    
    # Проверяем чтение данных
    interactions = collector.get_agent_interactions("test_agent")
    assert len(interactions) == 1
``` 