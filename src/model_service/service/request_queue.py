"""
Модуль для асинхронной очереди запросов к языковым моделям.
Обеспечивает контроль нагрузки и приоритизацию запросов.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Awaitable, TypeVar, Generic, Tuple
from dataclasses import dataclass, field
import uuid
import threading
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# Тип результата запроса
T = TypeVar('T')


class RequestPriority(Enum):
    """Приоритеты запросов в очереди"""
    LOW = 0      # Низкий приоритет (фоновые задачи)
    NORMAL = 1   # Обычный приоритет (стандартные запросы)
    HIGH = 2     # Высокий приоритет (важные запросы)
    CRITICAL = 3 # Критический приоритет (системные запросы)


@dataclass(order=True)
class QueueItem(Generic[T]):
    """
    Элемент очереди запросов с упорядочиванием по приоритету.
    """
    # Поля для сортировки (в порядке значимости)
    priority: int = field(compare=True)
    timestamp: float = field(compare=True)
    
    # Остальные поля (не участвуют в сортировке)
    request_id: str = field(compare=False)
    task: Callable[..., Awaitable[T]] = field(compare=False)
    args: Tuple = field(default_factory=tuple, compare=False)
    kwargs: Dict[str, Any] = field(default_factory=dict, compare=False)
    future: asyncio.Future = field(default_factory=asyncio.Future, compare=False)


class RequestQueue:
    """
    Асинхронная очередь запросов с поддержкой приоритизации и ограничения нагрузки.
    """
    def __init__(
        self,
        max_workers: int = 5,            # Максимальное количество параллельных выполнений
        max_queue_size: int = 100,       # Максимальное количество запросов в очереди
        timeout: int = 60,               # Таймаут выполнения запроса (в секундах)
        shutdown_timeout: int = 30,      # Таймаут при остановке (в секундах)
        stats_interval: int = 60         # Интервал вывода статистики (в секундах)
    ):
        """
        Инициализирует очередь запросов.

        Args:
            max_workers: Максимальное количество параллельных запросов
            max_queue_size: Максимальное количество запросов в очереди
            timeout: Таймаут выполнения запроса (в секундах)
            shutdown_timeout: Таймаут ожидания завершения запросов при остановке
            stats_interval: Интервал вывода статистики (в секундах)
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.timeout = timeout
        self.shutdown_timeout = shutdown_timeout
        self.stats_interval = stats_interval
        
        # Приоритетная очередь
        self.queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        
        # Семафор для ограничения параллельных запросов
        self.semaphore = asyncio.Semaphore(max_workers)
        
        # Словарь активных запросов для отслеживания
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
        # Событие для остановки очереди
        self.shutdown_event = asyncio.Event()
        
        # Задачи обработки
        self.worker_tasks: List[asyncio.Task] = []
        self.stats_task: Optional[asyncio.Task] = None
        
        # Метрики
        self.stats = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "timed_out_requests": 0,
            "avg_processing_time": 0,
            "max_processing_time": 0,
            "queue_full_rejections": 0,
            "processing_time_sum": 0,
            "start_time": time.time()
        }
        
        logger.info(f"Инициализирована очередь запросов с max_workers={max_workers}, max_queue_size={max_queue_size}")
    
    async def start(self, worker_count: int = None) -> None:
        """
        Запускает обработчики очереди запросов.

        Args:
            worker_count: Количество обработчиков (если None, используется max_workers)
        """
        if worker_count is None:
            worker_count = self.max_workers
        
        logger.info(f"Запуск {worker_count} обработчиков очереди запросов")
        
        # Создаем задачи обработчиков
        for i in range(worker_count):
            task = asyncio.create_task(self._worker(i))
            self.worker_tasks.append(task)
        
        # Запускаем задачу сбора статистики
        self.stats_task = asyncio.create_task(self._stats_reporter())
        
        logger.info("Очередь запросов запущена")
    
    async def stop(self) -> None:
        """
        Останавливает очередь запросов, ожидая завершения текущих запросов.
        """
        logger.info("Остановка очереди запросов...")
        
        # Устанавливаем событие остановки
        self.shutdown_event.set()
        
        # Ожидаем завершения всех активных запросов с таймаутом
        try:
            # Ждем завершения всех обработчиков
            if self.worker_tasks:
                await asyncio.wait(self.worker_tasks, timeout=self.shutdown_timeout)
                
            # Отменяем задачу статистики
            if self.stats_task:
                self.stats_task.cancel()
                try:
                    await self.stats_task
                except asyncio.CancelledError:
                    pass
            
            # Отмена оставшихся активных запросов
            active_count = len(self.active_requests)
            if active_count > 0:
                logger.warning(f"Осталось {active_count} незавершенных запросов, отменяем их")
                for request_id, request_info in list(self.active_requests.items()):
                    if 'future' in request_info and not request_info['future'].done():
                        request_info['future'].set_exception(
                            asyncio.CancelledError("Очередь запросов остановлена")
                        )
        except asyncio.TimeoutError:
            logger.error(f"Превышено время ожидания ({self.shutdown_timeout}с) при остановке очереди запросов")
        
        # Очищаем список задач
        self.worker_tasks.clear()
        self.stats_task = None
        
        logger.info("Очередь запросов остановлена")
    
    async def enqueue(
        self,
        task: Callable[..., Awaitable[T]],
        *args,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: Optional[int] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> Awaitable[T]:
        """
        Добавляет запрос в очередь.

        Args:
            task: Асинхронная функция для выполнения
            *args: Позиционные аргументы для функции
            priority: Приоритет запроса
            timeout: Таймаут выполнения (если None, используется timeout экземпляра)
            request_id: Идентификатор запроса (если None, генерируется)
            **kwargs: Именованные аргументы для функции

        Returns:
            Future с результатом выполнения запроса

        Raises:
            QueueFullError: Если очередь заполнена и нельзя добавить новый запрос
            asyncio.TimeoutError: Если выполнение запроса превысило таймаут
        """
        # Проверяем, запущена ли очередь
        if not self.worker_tasks:
            raise RuntimeError("Очередь запросов не запущена")
        
        # Проверяем, не находится ли очередь в процессе остановки
        if self.shutdown_event.is_set():
            raise RuntimeError("Очередь запросов останавливается")
        
        # Если очередь заполнена, отклоняем запрос
        if self.queue.full():
            self.stats["queue_full_rejections"] += 1
            raise QueueFullError("Очередь запросов заполнена")
        
        # Генерируем ID запроса, если он не предоставлен
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        # Создаем Future для результата
        future = asyncio.Future()
        
        # Создаем элемент очереди
        timestamp = time.time()
        item = QueueItem(
            priority=priority.value,  # Меньшие значения имеют более высокий приоритет
            timestamp=timestamp,      # Время добавления (для запросов с одинаковым приоритетом)
            request_id=request_id,
            task=task,
            args=args,
            kwargs=kwargs,
            future=future
        )
        
        # Добавляем информацию о запросе в активные запросы
        self.active_requests[request_id] = {
            'timestamp': timestamp,
            'priority': priority,
            'future': future,
            'timeout': timeout or self.timeout,
            'args': args,
            'kwargs': kwargs
        }
        
        # Обновляем статистику
        self.stats["total_requests"] += 1
        
        # Добавляем запрос в очередь
        await self.queue.put(item)
        logger.debug(f"Запрос {request_id} добавлен в очередь с приоритетом {priority.name}")
        
        return future
    
    async def _worker(self, worker_id: int) -> None:
        """
        Обработчик запросов из очереди.

        Args:
            worker_id: Идентификатор обработчика
        """
        logger.info(f"Запущен обработчик запросов #{worker_id}")
        
        while not self.shutdown_event.is_set():
            # Ожидаем доступный слот для выполнения запроса
            async with self.semaphore:
                try:
                    # Получаем запрос из очереди
                    item = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0  # Позволяет проверять shutdown_event каждую секунду
                    )
                    
                    # Если очередь остановлена, завершаем работу
                    if self.shutdown_event.is_set():
                        self.queue.task_done()
                        break
                    
                    request_id = item.request_id
                    logger.debug(f"Обработчик #{worker_id} начал выполнение запроса {request_id}")
                    
                    # Получаем информацию о запросе
                    request_info = self.active_requests.get(request_id)
                    if not request_info:
                        logger.warning(f"Запрос {request_id} не найден в активных запросах")
                        self.queue.task_done()
                        continue
                    
                    # Отмечаем время начала выполнения
                    start_time = time.time()
                    request_info['start_time'] = start_time
                    
                    # Выполняем запрос с таймаутом
                    try:
                        timeout_val = request_info.get('timeout', self.timeout)
                        result = await asyncio.wait_for(
                            item.task(*item.args, **item.kwargs),
                            timeout=timeout_val
                        )
                        
                        # Устанавливаем результат в Future
                        if not item.future.done():
                            item.future.set_result(result)
                        
                        # Обновляем статистику
                        processing_time = time.time() - start_time
                        self.stats["completed_requests"] += 1
                        self.stats["processing_time_sum"] += processing_time
                        
                        # Обновляем среднее время выполнения
                        if self.stats["completed_requests"] > 0:
                            self.stats["avg_processing_time"] = (
                                self.stats["processing_time_sum"] / self.stats["completed_requests"]
                            )
                        
                        # Обновляем максимальное время выполнения
                        if processing_time > self.stats["max_processing_time"]:
                            self.stats["max_processing_time"] = processing_time
                        
                        logger.debug(
                            f"Запрос {request_id} выполнен за {processing_time:.3f}с "
                            f"обработчиком #{worker_id}"
                        )
                    
                    except asyncio.TimeoutError:
                        self.stats["timed_out_requests"] += 1
                        
                        if not item.future.done():
                            item.future.set_exception(
                                asyncio.TimeoutError(
                                    f"Превышено время выполнения запроса {request_id} ({timeout_val}с)"
                                )
                            )
                        
                        logger.warning(
                            f"Превышено время выполнения запроса {request_id} "
                            f"({timeout_val}с) обработчиком #{worker_id}"
                        )
                    
                    except Exception as e:
                        self.stats["failed_requests"] += 1
                        
                        if not item.future.done():
                            item.future.set_exception(e)
                        
                        logger.error(
                            f"Ошибка при выполнении запроса {request_id} "
                            f"обработчиком #{worker_id}: {str(e)}"
                        )
                    
                    finally:
                        # Удаляем запрос из активных запросов
                        if request_id in self.active_requests:
                            del self.active_requests[request_id]
                        
                        # Отмечаем задачу как выполненную
                        self.queue.task_done()
                
                except asyncio.TimeoutError:
                    # Таймаут при ожидании запроса из очереди (для проверки shutdown_event)
                    continue
                
                except Exception as e:
                    logger.error(f"Ошибка в обработчике #{worker_id}: {str(e)}")
        
        logger.info(f"Обработчик #{worker_id} остановлен")
    
    async def _stats_reporter(self) -> None:
        """
        Периодически выводит статистику очереди запросов.
        """
        logger.info("Запущен механизм отчетности статистики очереди запросов")
        
        while not self.shutdown_event.is_set():
            try:
                # Ждем указанный интервал
                await asyncio.sleep(self.stats_interval)
                
                # Собираем статистику
                stats = self.get_stats()
                
                # Выводим в лог
                logger.info(
                    f"Статистика очереди запросов: "
                    f"выполнено {stats['completed_requests']}/{stats['total_requests']}, "
                    f"ошибок: {stats['failed_requests']}, "
                    f"таймаутов: {stats['timed_out_requests']}, "
                    f"в очереди: {stats['queue_size']}, "
                    f"активных: {stats['active_requests']}, "
                    f"средн. время: {stats['avg_processing_time']:.3f}с"
                )
            
            except asyncio.CancelledError:
                logger.info("Задача сбора статистики отменена")
                break
            
            except Exception as e:
                logger.error(f"Ошибка при сборе статистики: {str(e)}")
                await asyncio.sleep(10)  # Короткая пауза перед повторной попыткой
        
        logger.info("Механизм отчетности статистики остановлен")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает текущую статистику очереди запросов.

        Returns:
            Dict с метриками очереди
        """
        # Рассчитываем дополнительные метрики
        uptime = time.time() - self.stats["start_time"]
        
        # Копируем данные, чтобы избежать гонки при доступе
        stats = dict(self.stats)
        
        # Добавляем метрики, которые не хранятся постоянно
        stats.update({
            "uptime": uptime,
            "uptime_formatted": self._format_duration(uptime),
            "queue_size": self.queue.qsize(),
            "active_requests": len(self.active_requests),
            "avg_processing_time_formatted": self._format_duration(stats["avg_processing_time"]),
            "max_processing_time_formatted": self._format_duration(stats["max_processing_time"]),
            "timestamp": datetime.now().isoformat(),
            "request_rate": stats["total_requests"] / uptime if uptime > 0 else 0
        })
        
        return stats
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """
        Форматирует продолжительность в удобочитаемом виде.

        Args:
            seconds: Количество секунд

        Returns:
            Отформатированная строка
        """
        if seconds < 0.001:
            return f"{seconds * 1000000:.2f}мкс"
        elif seconds < 1:
            return f"{seconds * 1000:.2f}мс"
        elif seconds < 60:
            return f"{seconds:.2f}с"
        else:
            minutes = int(seconds // 60)
            seconds = seconds % 60
            return f"{minutes}м {seconds:.2f}с"


class QueueFullError(Exception):
    """
    Исключение, возникающее когда очередь запросов заполнена.
    """
    pass 