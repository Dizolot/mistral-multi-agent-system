"""
Тесты для модуля очереди запросов.
"""

import time
import asyncio
import pytest
from unittest.mock import Mock, patch

from src.model_service.service.request_queue import (
    RequestQueue, 
    RequestPriority, 
    QueueFullError,
    QueueItem
)


class TestRequestQueue:
    """Тесты для класса RequestQueue."""

    @pytest.fixture
    def queue(self):
        """Создает экземпляр очереди запросов для тестов."""
        queue = RequestQueue(
            max_workers=2,
            max_queue_size=10,
            request_timeout=5
        )
        return queue

    @pytest.mark.asyncio
    async def test_queue_initialization(self, queue):
        """Тест инициализации очереди запросов."""
        assert queue.max_workers == 2
        assert queue.max_queue_size == 10
        assert queue.request_timeout == 5
        assert queue._queue.qsize() == 0
        assert not queue._workers
        assert not queue._running

    @pytest.mark.asyncio
    async def test_start_stop(self, queue):
        """Тест запуска и остановки очереди запросов."""
        # Запускаем очередь
        await queue.start()
        assert queue._running
        assert len(queue._workers) == 2  # max_workers = 2
        
        # Останавливаем очередь
        await queue.stop()
        assert not queue._running
        assert not queue._workers

    @pytest.mark.asyncio
    async def test_enqueue_normal_priority(self, queue):
        """Тест добавления запроса с нормальным приоритетом."""
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию
        async def test_func(x, y):
            return x + y
        
        # Добавляем запрос в очередь
        future = await queue.enqueue(
            test_func,
            x=1,
            y=2,
            priority=RequestPriority.NORMAL,
            request_id="test_request"
        )
        
        # Ожидаем результат
        result = await future
        assert result == 3
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_enqueue_high_priority(self, queue):
        """Тест добавления запроса с высоким приоритетом."""
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию
        async def test_func(x, y):
            return x + y
        
        # Добавляем запрос в очередь
        future = await queue.enqueue(
            test_func,
            x=1,
            y=2,
            priority=RequestPriority.HIGH,
            request_id="test_request"
        )
        
        # Ожидаем результат
        result = await future
        assert result == 3
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_enqueue_critical_priority(self, queue):
        """Тест добавления запроса с критическим приоритетом."""
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию
        async def test_func(x, y):
            return x + y
        
        # Добавляем запрос в очередь
        future = await queue.enqueue(
            test_func,
            x=1,
            y=2,
            priority=RequestPriority.CRITICAL,
            request_id="test_request"
        )
        
        # Ожидаем результат
        result = await future
        assert result == 3
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_enqueue_low_priority(self, queue):
        """Тест добавления запроса с низким приоритетом."""
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию
        async def test_func(x, y):
            return x + y
        
        # Добавляем запрос в очередь
        future = await queue.enqueue(
            test_func,
            x=1,
            y=2,
            priority=RequestPriority.LOW,
            request_id="test_request"
        )
        
        # Ожидаем результат
        result = await future
        assert result == 3
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_queue_full_error(self):
        """Тест ошибки переполнения очереди."""
        # Создаем очередь с маленьким размером
        queue = RequestQueue(
            max_workers=1,
            max_queue_size=1,
            request_timeout=5
        )
        
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию, которая будет выполняться долго
        async def slow_func():
            await asyncio.sleep(2)
            return True
        
        # Добавляем первый запрос в очередь
        future1 = await queue.enqueue(
            slow_func,
            priority=RequestPriority.NORMAL,
            request_id="test_request_1"
        )
        
        # Добавляем второй запрос в очередь, должен быть добавлен
        future2 = await queue.enqueue(
            slow_func,
            priority=RequestPriority.NORMAL,
            request_id="test_request_2"
        )
        
        # Пытаемся добавить третий запрос, должна возникнуть ошибка
        with pytest.raises(QueueFullError):
            await queue.enqueue(
                slow_func,
                priority=RequestPriority.NORMAL,
                request_id="test_request_3"
            )
        
        # Ожидаем завершения запросов
        await future1
        await future2
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_request_timeout(self):
        """Тест таймаута запроса."""
        # Создаем очередь с маленьким таймаутом
        queue = RequestQueue(
            max_workers=1,
            max_queue_size=10,
            request_timeout=1  # 1 секунда
        )
        
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию, которая будет выполняться дольше таймаута
        async def very_slow_func():
            await asyncio.sleep(3)  # 3 секунды
            return True
        
        # Добавляем запрос в очередь
        future = await queue.enqueue(
            very_slow_func,
            priority=RequestPriority.NORMAL,
            request_id="test_request"
        )
        
        # Ожидаем таймаут
        with pytest.raises(asyncio.TimeoutError):
            await future
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Тест порядка выполнения запросов по приоритету."""
        # Создаем очередь с одним рабочим потоком
        queue = RequestQueue(
            max_workers=1,
            max_queue_size=10,
            request_timeout=5
        )
        
        # Запускаем очередь
        await queue.start()
        
        # Создаем список для отслеживания порядка выполнения
        execution_order = []
        
        # Создаем тестовую функцию
        async def test_func(name):
            execution_order.append(name)
            return name
        
        # Добавляем запросы с разными приоритетами
        # Сначала добавляем запрос с низким приоритетом
        future_low = await queue.enqueue(
            test_func,
            name="low",
            priority=RequestPriority.LOW,
            request_id="low"
        )
        
        # Затем с нормальным приоритетом
        future_normal = await queue.enqueue(
            test_func,
            name="normal",
            priority=RequestPriority.NORMAL,
            request_id="normal"
        )
        
        # Затем с высоким приоритетом
        future_high = await queue.enqueue(
            test_func,
            name="high",
            priority=RequestPriority.HIGH,
            request_id="high"
        )
        
        # И наконец с критическим приоритетом
        future_critical = await queue.enqueue(
            test_func,
            name="critical",
            priority=RequestPriority.CRITICAL,
            request_id="critical"
        )
        
        # Ожидаем завершения всех запросов
        await future_low
        await future_normal
        await future_high
        await future_critical
        
        # Проверяем порядок выполнения
        # Ожидаемый порядок: critical, high, normal, low
        assert execution_order == ["critical", "high", "normal", "low"]
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_exception_handling(self, queue):
        """Тест обработки исключений в задачах."""
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию, которая вызывает исключение
        async def failing_func():
            raise ValueError("Test exception")
        
        # Добавляем запрос в очередь
        future = await queue.enqueue(
            failing_func,
            priority=RequestPriority.NORMAL,
            request_id="test_request"
        )
        
        # Ожидаем исключение
        with pytest.raises(ValueError, match="Test exception"):
            await future
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_stats_reporting(self, queue):
        """Тест сбора и отчетности статистики."""
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию
        async def test_func(sleep_time):
            await asyncio.sleep(sleep_time)
            return sleep_time
        
        # Добавляем несколько запросов
        futures = []
        for i in range(5):
            future = await queue.enqueue(
                test_func,
                sleep_time=0.1,
                priority=RequestPriority.NORMAL,
                request_id=f"test_request_{i}"
            )
            futures.append(future)
        
        # Ожидаем завершения всех запросов
        for future in futures:
            await future
        
        # Проверяем статистику
        assert queue.stats["total_requests"] == 5
        assert queue.stats["completed_requests"] == 5
        assert queue.stats["failed_requests"] == 0
        assert queue.stats["avg_processing_time"] > 0
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_custom_timeout(self, queue):
        """Тест пользовательского таймаута для запроса."""
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию, которая будет выполняться долго
        async def slow_func():
            await asyncio.sleep(2)
            return True
        
        # Добавляем запрос с пользовательским таймаутом (меньше времени выполнения)
        future = await queue.enqueue(
            slow_func,
            priority=RequestPriority.NORMAL,
            request_id="test_request",
            timeout=1  # 1 секунда
        )
        
        # Ожидаем таймаут
        with pytest.raises(asyncio.TimeoutError):
            await future
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_worker_task_handling(self, queue):
        """Тест обработки задач рабочими потоками."""
        # Запускаем очередь
        await queue.start()
        
        # Создаем тестовую функцию с задержкой
        async def delayed_func(delay, result):
            await asyncio.sleep(delay)
            return result
        
        # Добавляем несколько запросов с разными задержками
        future1 = await queue.enqueue(
            delayed_func,
            delay=0.1,
            result="fast",
            priority=RequestPriority.NORMAL,
            request_id="fast_request"
        )
        
        future2 = await queue.enqueue(
            delayed_func,
            delay=0.5,
            result="medium",
            priority=RequestPriority.NORMAL,
            request_id="medium_request"
        )
        
        future3 = await queue.enqueue(
            delayed_func,
            delay=1.0,
            result="slow",
            priority=RequestPriority.NORMAL,
            request_id="slow_request"
        )
        
        # Ожидаем результаты
        result1 = await future1
        result2 = await future2
        result3 = await future3
        
        # Проверяем результаты
        assert result1 == "fast"
        assert result2 == "medium"
        assert result3 == "slow"
        
        # Останавливаем очередь
        await queue.stop()

    @pytest.mark.asyncio
    async def test_queue_item_comparison(self):
        """Тест сравнения элементов очереди по приоритету и времени."""
        # Создаем элементы очереди с разными приоритетами
        item1 = QueueItem(
            priority=RequestPriority.LOW,
            timestamp=time.time(),
            request_id="item1",
            task=None,
            args=(),
            kwargs={},
            future=None
        )
        
        item2 = QueueItem(
            priority=RequestPriority.NORMAL,
            timestamp=time.time(),
            request_id="item2",
            task=None,
            args=(),
            kwargs={},
            future=None
        )
        
        item3 = QueueItem(
            priority=RequestPriority.HIGH,
            timestamp=time.time(),
            request_id="item3",
            task=None,
            args=(),
            kwargs={},
            future=None
        )
        
        item4 = QueueItem(
            priority=RequestPriority.CRITICAL,
            timestamp=time.time(),
            request_id="item4",
            task=None,
            args=(),
            kwargs={},
            future=None
        )
        
        # Проверяем сравнение по приоритету
        assert item1 > item2  # LOW > NORMAL (меньший приоритет)
        assert item2 > item3  # NORMAL > HIGH (меньший приоритет)
        assert item3 > item4  # HIGH > CRITICAL (меньший приоритет)
        
        # Создаем элементы с одинаковым приоритетом, но разным временем
        time_now = time.time()
        item5 = QueueItem(
            priority=RequestPriority.NORMAL,
            timestamp=time_now,
            request_id="item5",
            task=None,
            args=(),
            kwargs={},
            future=None
        )
        
        item6 = QueueItem(
            priority=RequestPriority.NORMAL,
            timestamp=time_now + 1,  # На 1 секунду позже
            request_id="item6",
            task=None,
            args=(),
            kwargs={},
            future=None
        )
        
        # Проверяем сравнение по времени при одинаковом приоритете
        assert item5 < item6  # Раньше созданный элемент имеет больший приоритет 