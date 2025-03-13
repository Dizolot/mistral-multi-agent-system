"""
Модуль для балансировки нагрузки между экземплярами моделей.
Обеспечивает распределение запросов между несколькими экземплярами одной модели.
"""

import logging
import random
import time
from typing import Dict, List, Any, Optional, Callable, Tuple, TypeVar
from collections import defaultdict, deque

# Настройка логирования
logger = logging.getLogger(__name__)

# Определяем тип для адаптера модели
ModelAdapterType = TypeVar('ModelAdapterType')


class LoadBalancer:
    """
    Класс для балансировки нагрузки между несколькими экземплярами моделей.
    Поддерживает различные стратегии балансировки, включая round-robin и взвешенное распределение.
    """

    def __init__(self):
        """
        Инициализирует балансировщик нагрузки.
        """
        # Структура для хранения экземпляров моделей
        # {model_name: [(adapter, weight, is_active, last_error), ...]}
        self.instances = defaultdict(list)
        
        # Счетчики для round-robin
        self.counters = defaultdict(int)
        
        # Очередь последних ошибок для определения неактивных экземпляров
        # {adapter_id: deque([время_ошибки, ...], maxlen=5)}
        self.error_history = defaultdict(lambda: deque(maxlen=5))
        
        # Статистика использования
        self.stats = defaultdict(lambda: {"requests": 0, "errors": 0, "latency": []})
        
        logger.info("Инициализирован балансировщик нагрузки")

    def register_instance(
        self, 
        model_name: str, 
        adapter: ModelAdapterType, 
        weight: int = 1
    ) -> None:
        """
        Регистрирует экземпляр модели в балансировщике.

        Args:
            model_name: Имя модели
            adapter: Экземпляр адаптера модели
            weight: Вес экземпляра для взвешенной балансировки (по умолчанию: 1)
        """
        adapter_id = id(adapter)
        self.instances[model_name].append((adapter, weight, True, None))
        logger.info(f"Зарегистрирован новый экземпляр модели {model_name} с весом {weight}")

    def unregister_instance(self, model_name: str, adapter: ModelAdapterType) -> bool:
        """
        Удаляет экземпляр модели из балансировщика.

        Args:
            model_name: Имя модели
            adapter: Экземпляр адаптера модели

        Returns:
            True, если экземпляр был успешно удален, иначе False
        """
        adapter_id = id(adapter)
        instances = self.instances[model_name]
        
        for i, (inst_adapter, weight, is_active, last_error) in enumerate(instances):
            if id(inst_adapter) == adapter_id:
                instances.pop(i)
                logger.info(f"Удален экземпляр модели {model_name}")
                return True
        
        logger.warning(f"Экземпляр модели {model_name} не найден для удаления")
        return False

    def get_active_instances(self, model_name: str) -> List[Tuple[ModelAdapterType, int]]:
        """
        Возвращает список активных экземпляров модели.

        Args:
            model_name: Имя модели

        Returns:
            Список кортежей (адаптер, вес) для активных экземпляров
        """
        active_instances = []
        for adapter, weight, is_active, last_error in self.instances[model_name]:
            if is_active:
                active_instances.append((adapter, weight))
        
        return active_instances

    def mark_instance_error(self, model_name: str, adapter: ModelAdapterType, error: Exception) -> None:
        """
        Отмечает ошибку на экземпляре модели.

        Args:
            model_name: Имя модели
            adapter: Экземпляр адаптера
            error: Исключение, вызвавшее ошибку
        """
        adapter_id = id(adapter)
        current_time = time.time()
        self.error_history[adapter_id].append(current_time)
        
        # Определяем, нужно ли деактивировать экземпляр
        for i, (inst_adapter, weight, is_active, last_error) in enumerate(self.instances[model_name]):
            if id(inst_adapter) == adapter_id:
                # Если было 3+ ошибки за последние 60 секунд, деактивируем
                recent_errors = sum(1 for t in self.error_history[adapter_id] if current_time - t < 60)
                if recent_errors >= 3:
                    self.instances[model_name][i] = (inst_adapter, weight, False, error)
                    logger.warning(f"Экземпляр модели {model_name} деактивирован из-за частых ошибок: {str(error)}")
                else:
                    self.instances[model_name][i] = (inst_adapter, weight, is_active, error)
                    logger.warning(f"Зафиксирована ошибка для экземпляра модели {model_name}: {str(error)}")
                break

    def mark_instance_recovered(self, model_name: str, adapter: ModelAdapterType) -> None:
        """
        Отмечает восстановление экземпляра модели.

        Args:
            model_name: Имя модели
            adapter: Экземпляр адаптера
        """
        adapter_id = id(adapter)
        
        for i, (inst_adapter, weight, is_active, last_error) in enumerate(self.instances[model_name]):
            if id(inst_adapter) == adapter_id:
                self.instances[model_name][i] = (inst_adapter, weight, True, None)
                logger.info(f"Экземпляр модели {model_name} восстановлен после ошибки")
                break
        
        # Очищаем историю ошибок
        if adapter_id in self.error_history:
            self.error_history[adapter_id].clear()

    async def execute(
        self, 
        model_name: str, 
        method_name: str, 
        *args, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Выполняет метод на выбранном экземпляре модели с балансировкой нагрузки.

        Args:
            model_name: Имя модели
            method_name: Имя метода адаптера для вызова
            *args: Позиционные аргументы для метода
            **kwargs: Именованные аргументы для метода

        Returns:
            Результат выполнения метода

        Raises:
            Exception: Если нет доступных экземпляров или все экземпляры вернули ошибки
        """
        active_instances = self.get_active_instances(model_name)
        
        if not active_instances:
            # Если нет активных экземпляров, пробуем восстановить неактивные
            for i, (adapter, weight, is_active, last_error) in enumerate(self.instances[model_name]):
                if not is_active:
                    self.instances[model_name][i] = (adapter, weight, True, None)
                    active_instances.append((adapter, weight))
            
            if not active_instances:
                error_msg = f"Нет доступных экземпляров модели {model_name}"
                logger.error(error_msg)
                return {"error": error_msg}
        
        # Выбираем экземпляр по стратегии round-robin с учетом весов
        adapter = self._select_instance(model_name, active_instances)
        
        # Увеличиваем счетчик запросов
        adapter_id = id(adapter)
        self.stats[adapter_id]["requests"] += 1
        
        start_time = time.time()
        
        try:
            # Вызываем метод на выбранном адаптере
            method = getattr(adapter, method_name)
            result = await method(*args, **kwargs)
            
            # Записываем латентность
            latency = time.time() - start_time
            self.stats[adapter_id]["latency"].append(latency)
            
            # Если запрос успешен и экземпляр ранее имел ошибки, отмечаем восстановление
            for i, (inst_adapter, weight, is_active, last_error) in enumerate(self.instances[model_name]):
                if id(inst_adapter) == adapter_id and last_error is not None:
                    self.mark_instance_recovered(model_name, adapter)
                    break
            
            return result
            
        except Exception as e:
            # Увеличиваем счетчик ошибок
            self.stats[adapter_id]["errors"] += 1
            
            # Отмечаем ошибку
            self.mark_instance_error(model_name, adapter, e)
            
            # Пробуем другой экземпляр, если доступен
            remaining_instances = [(inst, w) for inst, w in active_instances if id(inst) != adapter_id]
            
            if remaining_instances:
                logger.warning(f"Ошибка при выполнении {method_name} на модели {model_name}. Пробуем другой экземпляр.")
                return await self.execute(model_name, method_name, *args, **kwargs)
            else:
                error_msg = f"Ошибка при выполнении {method_name} на модели {model_name}: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg}

    def _select_instance(
        self, 
        model_name: str, 
        active_instances: List[Tuple[ModelAdapterType, int]]
    ) -> ModelAdapterType:
        """
        Выбирает экземпляр модели для выполнения запроса.

        Args:
            model_name: Имя модели
            active_instances: Список активных экземпляров с весами

        Returns:
            Выбранный экземпляр адаптера модели
        """
        if not active_instances:
            raise Exception(f"Нет доступных экземпляров модели {model_name}")
        
        # Используем weighted round-robin
        # Создаем расширенный список, где каждый адаптер повторяется согласно его весу
        weighted_instances = []
        for adapter, weight in active_instances:
            weighted_instances.extend([adapter] * weight)
        
        # Выбираем по счетчику
        idx = self.counters[model_name] % len(weighted_instances)
        self.counters[model_name] += 1
        
        return weighted_instances[idx]

    def get_stats(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Возвращает статистику использования балансировщика.

        Args:
            model_name: Опционально, имя модели для фильтрации статистики

        Returns:
            Словарь со статистикой
        """
        if model_name:
            model_stats = {}
            for i, (adapter, weight, is_active, last_error) in enumerate(self.instances[model_name]):
                adapter_id = id(adapter)
                adapter_stats = self.stats[adapter_id]
                avg_latency = sum(adapter_stats["latency"]) / len(adapter_stats["latency"]) if adapter_stats["latency"] else 0
                
                model_stats[f"instance_{i}"] = {
                    "requests": adapter_stats["requests"],
                    "errors": adapter_stats["errors"],
                    "error_rate": adapter_stats["errors"] / adapter_stats["requests"] if adapter_stats["requests"] > 0 else 0,
                    "avg_latency": avg_latency,
                    "is_active": is_active,
                    "weight": weight
                }
            
            return {model_name: model_stats}
        else:
            # Агрегированная статистика по всем моделям
            all_stats = {}
            for model, instances in self.instances.items():
                model_total_requests = 0
                model_total_errors = 0
                model_active_instances = 0
                
                for adapter, weight, is_active, last_error in instances:
                    adapter_id = id(adapter)
                    adapter_stats = self.stats[adapter_id]
                    model_total_requests += adapter_stats["requests"]
                    model_total_errors += adapter_stats["errors"]
                    if is_active:
                        model_active_instances += 1
                
                all_stats[model] = {
                    "total_requests": model_total_requests,
                    "total_errors": model_total_errors,
                    "error_rate": model_total_errors / model_total_requests if model_total_requests > 0 else 0,
                    "active_instances": model_active_instances,
                    "total_instances": len(instances)
                }
            
            return all_stats 