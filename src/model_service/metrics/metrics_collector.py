"""
Модуль для сбора метрик производительности моделей.
Обеспечивает мониторинг использования моделей и производительности системы.
"""

import time
import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import asyncio
import threading

# Настройка логирования
logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Класс для сбора и анализа метрик производительности моделей.
    Отслеживает время отклика, использование токенов, успешность запросов и другие метрики.
    """

    def __init__(self, metrics_dir: str = "logs/metrics"):
        """
        Инициализирует коллектор метрик.

        Args:
            metrics_dir: Директория для сохранения метрик
        """
        self.metrics_dir = metrics_dir
        self.metrics = defaultdict(list)
        self.aggregated_metrics = {}
        self.start_time = datetime.now()
        
        # Создаем директорию для метрик, если она не существует
        os.makedirs(metrics_dir, exist_ok=True)
        
        # Запускаем фоновую задачу для периодического сохранения метрик
        self._start_background_task()
        
        logger.info(f"Инициализирован коллектор метрик. Директория для метрик: {metrics_dir}")

    def record_request(
        self, 
        model: str, 
        operation: str, 
        duration: float, 
        tokens: Dict[str, int], 
        success: bool, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Записывает метрики для одного запроса.

        Args:
            model: Название модели
            operation: Тип операции (chat, generate, embeddings)
            duration: Время выполнения запроса в секундах
            tokens: Словарь с использованием токенов (prompt_tokens, completion_tokens)
            success: Флаг успешности запроса
            metadata: Дополнительные метаданные запроса
        """
        timestamp = datetime.now().isoformat()
        
        metric = {
            "timestamp": timestamp,
            "model": model,
            "operation": operation,
            "duration": duration,
            "tokens": tokens,
            "success": success,
            "metadata": metadata or {}
        }
        
        self.metrics[model].append(metric)
        logger.debug(f"Записана метрика для модели {model}: {operation}, {duration:.3f}с, {'успешно' if success else 'с ошибкой'}")

    def get_metrics(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Возвращает собранные метрики.

        Args:
            model: Опционально, название модели для фильтрации метрик

        Returns:
            Словарь с метриками
        """
        if model:
            return {"model": model, "metrics": self.metrics.get(model, [])}
        return {"metrics": {model: metrics for model, metrics in self.metrics.items()}}

    def get_aggregated_metrics(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Возвращает агрегированные метрики.

        Args:
            model: Опционально, название модели для фильтрации метрик

        Returns:
            Словарь с агрегированными метриками
        """
        self._aggregate_metrics()
        
        if model:
            return {"model": model, "metrics": self.aggregated_metrics.get(model, {})}
        return {"metrics": self.aggregated_metrics}

    def save_metrics(self, filename: Optional[str] = None) -> str:
        """
        Сохраняет метрики в файл.

        Args:
            filename: Опционально, имя файла для сохранения

        Returns:
            Путь к сохраненному файлу
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"
        
        filepath = os.path.join(self.metrics_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.get_metrics(), f, indent=2)
        
        logger.info(f"Метрики сохранены в файл: {filepath}")
        return filepath

    def save_aggregated_metrics(self, filename: Optional[str] = None) -> str:
        """
        Сохраняет агрегированные метрики в файл.

        Args:
            filename: Опционально, имя файла для сохранения

        Returns:
            Путь к сохраненному файлу
        """
        self._aggregate_metrics()
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"aggregated_metrics_{timestamp}.json"
        
        filepath = os.path.join(self.metrics_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.get_aggregated_metrics(), f, indent=2)
        
        logger.info(f"Агрегированные метрики сохранены в файл: {filepath}")
        return filepath

    def reset(self) -> None:
        """Сбрасывает все метрики"""
        self.metrics = defaultdict(list)
        self.aggregated_metrics = {}
        self.start_time = datetime.now()
        logger.info("Метрики сброшены")

    def _aggregate_metrics(self) -> None:
        """Агрегирует собранные метрики"""
        aggregated = {}
        
        for model, model_metrics in self.metrics.items():
            total_requests = len(model_metrics)
            
            if total_requests == 0:
                continue
            
            successful_requests = sum(1 for m in model_metrics if m["success"])
            total_duration = sum(m["duration"] for m in model_metrics)
            
            operations = {}
            for m in model_metrics:
                op = m["operation"]
                if op not in operations:
                    operations[op] = {"count": 0, "total_duration": 0, "successful": 0}
                
                operations[op]["count"] += 1
                operations[op]["total_duration"] += m["duration"]
                if m["success"]:
                    operations[op]["successful"] += 1
            
            # Агрегируем по операциям
            for op, op_stats in operations.items():
                operations[op]["avg_duration"] = op_stats["total_duration"] / op_stats["count"]
                operations[op]["success_rate"] = op_stats["successful"] / op_stats["count"]
            
            # Вычисляем общие метрики
            total_prompt_tokens = sum(m["tokens"].get("prompt_tokens", 0) for m in model_metrics)
            total_completion_tokens = sum(m["tokens"].get("completion_tokens", 0) for m in model_metrics)
            
            aggregated[model] = {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": successful_requests / total_requests,
                "avg_duration": total_duration / total_requests,
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "operations": operations,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat()
            }
        
        self.aggregated_metrics = aggregated

    def _start_background_task(self) -> None:
        """Запускает фоновую задачу для периодического сохранения метрик"""
        
        def periodic_save():
            while True:
                try:
                    # Сохраняем метрики каждый час
                    time.sleep(3600)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H")
                    self.save_metrics(f"metrics_{timestamp}.json")
                    self.save_aggregated_metrics(f"aggregated_metrics_{timestamp}.json")
                except Exception as e:
                    logger.error(f"Ошибка при фоновом сохранении метрик: {str(e)}")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=periodic_save, daemon=True)
        thread.start()
        logger.info("Запущена фоновая задача сохранения метрик") 