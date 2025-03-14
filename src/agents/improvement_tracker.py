#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для отслеживания и оценки предложенных и примененных улучшений кода.

Предоставляет функционал для хранения истории изменений, сравнения версий кода
и оценки эффективности улучшений.
"""

import os
import json
import logging
import difflib
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union, Set, Tuple
import uuid

from src.agents.code_analyzer import CodeAnalyzer
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class CodeVersion:
    """Представление версии кода."""
    code: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    language: str = "python"
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def get_hash(self) -> str:
        """Получает хеш кода для проверки изменений."""
        return hashlib.md5(self.code.encode('utf-8')).hexdigest()

@dataclass
class ImprovementSuggestion:
    """Предложение по улучшению кода."""
    type: str  # Тип улучшения (refactor, documentation, performance, etc.)
    message: str  # Описание предложения
    location: Dict[str, Any] = field(default_factory=dict)  # Расположение в коде (line, column)
    suggestion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    applied: bool = False  # Было ли применено это улучшение
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует предложение в словарь для сериализации."""
        return asdict(self)

@dataclass
class ImprovementResult:
    """Результат применения улучшений к коду."""
    original_version: CodeVersion
    improved_version: CodeVersion
    suggestions: List[ImprovementSuggestion]
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metrics_changes: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует результат в словарь для сериализации."""
        return {
            "result_id": self.result_id,
            "timestamp": self.timestamp,
            "original_version": asdict(self.original_version),
            "improved_version": asdict(self.improved_version),
            "suggestions": [s.to_dict() for s in self.suggestions],
            "metrics_changes": self.metrics_changes
        }

class ImprovementTracker:
    """
    Класс для отслеживания и оценки улучшений кода.
    
    Предоставляет функционал для хранения истории изменений, сравнения версий кода
    и оценки эффективности улучшений.
    """
    
    def __init__(self, storage_dir: str = "data/improvements"):
        """
        Инициализация трекера улучшений.
        
        Args:
            storage_dir: Директория для хранения данных об улучшениях
        """
        self.storage_dir = storage_dir
        self.code_analyzer = CodeAnalyzer()
        
        # Создаем директорию для хранения данных, если её нет
        os.makedirs(storage_dir, exist_ok=True)
        
        # Словари для хранения улучшений и версий кода
        self.versions: Dict[str, CodeVersion] = {}
        self.suggestions: Dict[str, List[ImprovementSuggestion]] = {}
        self.results: Dict[str, ImprovementResult] = {}
        
        # Словарь для хранения улучшений по пользователям
        self.user_improvements: Dict[str, List[str]] = {}
        
        # Загружаем данные, если они существуют
        self._load_data()
    
    async def track_code(self, code: str, user_id: str, language: str = "python") -> str:
        """
        Отслеживает новую версию кода.
        
        Args:
            code: Исходный код
            user_id: Идентификатор пользователя
            language: Язык программирования
            
        Returns:
            str: Идентификатор версии
        """
        # Анализируем код для получения метрик
        analysis = self.code_analyzer.analyze(code, language)
        
        # Создаем новую версию кода
        version = CodeVersion(
            code=code,
            language=language,
            metrics=analysis.get("metrics", {})
        )
        
        # Сохраняем версию
        self.versions[version.version_id] = version
        
        # Добавляем версию в список улучшений пользователя
        if user_id not in self.user_improvements:
            self.user_improvements[user_id] = []
        
        # Проверяем, есть ли уже такой код у пользователя (по хешу)
        version_hash = version.get_hash()
        duplicate = False
        
        for v_id in self.user_improvements[user_id]:
            if self.versions.get(v_id) and self.versions[v_id].get_hash() == version_hash:
                duplicate = True
                break
        
        if not duplicate:
            self.user_improvements[user_id].append(version.version_id)
        
        # Сохраняем данные
        self._save_data()
        
        return version.version_id
    
    async def add_improvement_suggestions(
        self,
        version_id: str,
        suggestions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Добавляет предложения по улучшению для указанной версии кода.
        
        Args:
            version_id: Идентификатор версии кода
            suggestions: Список предложений по улучшению
            
        Returns:
            List[str]: Список идентификаторов предложений
        """
        if version_id not in self.versions:
            raise ValueError(f"Версия с ID {version_id} не найдена")
        
        # Преобразуем предложения в объекты ImprovementSuggestion
        suggestion_objects = []
        for suggestion in suggestions:
            suggestion_obj = ImprovementSuggestion(
                type=suggestion.get("type", "unknown"),
                message=suggestion.get("message", ""),
                location=suggestion.get("location", {})
            )
            suggestion_objects.append(suggestion_obj)
        
        # Сохраняем предложения
        self.suggestions[version_id] = suggestion_objects
        
        # Сохраняем данные
        self._save_data()
        
        return [s.suggestion_id for s in suggestion_objects]
    
    async def record_improvement_result(
        self,
        original_version_id: str,
        improved_code: str,
        applied_suggestions: List[str] = None
    ) -> str:
        """
        Записывает результат применения улучшений.
        
        Args:
            original_version_id: Идентификатор исходной версии кода
            improved_code: Улучшенный код
            applied_suggestions: Список идентификаторов примененных предложений
            
        Returns:
            str: Идентификатор результата
        """
        if original_version_id not in self.versions:
            raise ValueError(f"Версия с ID {original_version_id} не найдена")
        
        original_version = self.versions[original_version_id]
        
        # Анализируем улучшенный код
        analysis = self.code_analyzer.analyze(improved_code, original_version.language)
        
        # Создаем новую версию для улучшенного кода
        improved_version = CodeVersion(
            code=improved_code,
            language=original_version.language,
            metrics=analysis.get("metrics", {})
        )
        
        # Сохраняем улучшенную версию
        self.versions[improved_version.version_id] = improved_version
        
        # Получаем список предложений по улучшению для исходной версии
        suggestions = self.suggestions.get(original_version_id, [])
        
        # Помечаем примененные предложения
        if applied_suggestions:
            for suggestion in suggestions:
                if suggestion.suggestion_id in applied_suggestions:
                    suggestion.applied = True
        
        # Рассчитываем изменения метрик
        metrics_changes = self._calculate_metrics_changes(
            original_version.metrics,
            improved_version.metrics
        )
        
        # Создаем результат улучшения
        result = ImprovementResult(
            original_version=original_version,
            improved_version=improved_version,
            suggestions=suggestions,
            metrics_changes=metrics_changes
        )
        
        # Сохраняем результат
        self.results[result.result_id] = result
        
        # Сохраняем данные
        self._save_data()
        
        return result.result_id
    
    def get_improvement_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает историю улучшений для указанного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            List[Dict[str, Any]]: Список результатов улучшений
        """
        history = []
        
        if user_id not in self.user_improvements:
            return history
        
        for version_id in self.user_improvements[user_id]:
            # Ищем результаты, где эта версия является исходной
            for result_id, result in self.results.items():
                if result.original_version.version_id == version_id:
                    history.append(result.to_dict())
        
        # Сортируем по времени (от новых к старым)
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return history
    
    def get_code_diff(self, original_id: str, improved_id: str) -> List[str]:
        """
        Получает разницу между двумя версиями кода.
        
        Args:
            original_id: Идентификатор исходной версии
            improved_id: Идентификатор улучшенной версии
            
        Returns:
            List[str]: Список строк разницы в формате unidiff
        """
        if original_id not in self.versions:
            raise ValueError(f"Версия с ID {original_id} не найдена")
        
        if improved_id not in self.versions:
            raise ValueError(f"Версия с ID {improved_id} не найдена")
        
        original = self.versions[original_id].code.splitlines()
        improved = self.versions[improved_id].code.splitlines()
        
        diff = difflib.unified_diff(
            original,
            improved,
            fromfile='original',
            tofile='improved',
            lineterm=''
        )
        
        return list(diff)
    
    def get_improvement_effectiveness(self, result_id: str) -> Dict[str, Any]:
        """
        Оценивает эффективность примененных улучшений.
        
        Args:
            result_id: Идентификатор результата улучшения
            
        Returns:
            Dict[str, Any]: Оценка эффективности улучшений
        """
        if result_id not in self.results:
            raise ValueError(f"Результат с ID {result_id} не найден")
        
        result = self.results[result_id]
        
        # Рассчитываем метрики эффективности
        effectiveness = {
            "complexity_change": result.metrics_changes.get("complexity_score", 0),
            "maintainability_change": result.metrics_changes.get("maintainability_index", 0),
            "applied_suggestions": sum(1 for s in result.suggestions if s.applied),
            "total_suggestions": len(result.suggestions)
        }
        
        # Определяем общую оценку эффективности (от 0 до 100)
        if effectiveness["total_suggestions"] > 0:
            suggestion_score = (effectiveness["applied_suggestions"] / effectiveness["total_suggestions"]) * 100
        else:
            suggestion_score = 0
        
        # Нормализуем изменение сложности (уменьшение сложности - хорошо)
        complexity_score = min(100, max(0, -effectiveness["complexity_change"] * 10 + 50))
        
        # Нормализуем изменение поддерживаемости (увеличение поддерживаемости - хорошо)
        maintainability_score = min(100, max(0, effectiveness["maintainability_change"] + 50))
        
        # Средняя оценка
        effectiveness["score"] = (suggestion_score + complexity_score + maintainability_score) / 3
        
        return effectiveness
    
    def _calculate_metrics_changes(self, original: Dict[str, Any], improved: Dict[str, Any]) -> Dict[str, float]:
        """
        Рассчитывает изменения метрик между исходной и улучшенной версиями.
        
        Args:
            original: Метрики исходной версии
            improved: Метрики улучшенной версии
            
        Returns:
            Dict[str, float]: Изменения метрик
        """
        changes = {}
        
        for key in original:
            if key in improved:
                changes[key] = improved[key] - original[key]
        
        return changes
    
    def _save_data(self):
        """Сохраняет данные об улучшениях."""
        try:
            # Сохранение версий кода
            versions_path = os.path.join(self.storage_dir, "versions.json")
            versions_data = {k: asdict(v) for k, v in self.versions.items()}
            
            with open(versions_path, "w", encoding="utf-8") as f:
                json.dump(versions_data, f, ensure_ascii=False, indent=2)
            
            # Сохранение предложений по улучшению
            suggestions_path = os.path.join(self.storage_dir, "suggestions.json")
            suggestions_data = {k: [asdict(s) for s in v] for k, v in self.suggestions.items()}
            
            with open(suggestions_path, "w", encoding="utf-8") as f:
                json.dump(suggestions_data, f, ensure_ascii=False, indent=2)
            
            # Сохранение результатов улучшений
            results_path = os.path.join(self.storage_dir, "results.json")
            results_data = {k: result.to_dict() for k, result in self.results.items()}
            
            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            # Сохранение связей пользователей и улучшений
            users_path = os.path.join(self.storage_dir, "users.json")
            
            with open(users_path, "w", encoding="utf-8") as f:
                json.dump(self.user_improvements, f, ensure_ascii=False, indent=2)
            
            logger.debug("Данные об улучшениях успешно сохранены")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных об улучшениях: {e}")
    
    def _load_data(self):
        """Загружает данные об улучшениях."""
        try:
            # Загрузка версий кода
            versions_path = os.path.join(self.storage_dir, "versions.json")
            if os.path.exists(versions_path):
                with open(versions_path, "r", encoding="utf-8") as f:
                    versions_data = json.load(f)
                    for k, v in versions_data.items():
                        self.versions[k] = CodeVersion(**v)
            
            # Загрузка предложений по улучшению
            suggestions_path = os.path.join(self.storage_dir, "suggestions.json")
            if os.path.exists(suggestions_path):
                with open(suggestions_path, "r", encoding="utf-8") as f:
                    suggestions_data = json.load(f)
                    for k, v in suggestions_data.items():
                        self.suggestions[k] = [ImprovementSuggestion(**s) for s in v]
            
            # Загрузка результатов улучшений
            results_path = os.path.join(self.storage_dir, "results.json")
            if os.path.exists(results_path):
                with open(results_path, "r", encoding="utf-8") as f:
                    results_data = json.load(f)
                    for k, v in results_data.items():
                        original_version = CodeVersion(**v["original_version"])
                        improved_version = CodeVersion(**v["improved_version"])
                        suggestions = [ImprovementSuggestion(**s) for s in v["suggestions"]]
                        
                        result = ImprovementResult(
                            original_version=original_version,
                            improved_version=improved_version,
                            suggestions=suggestions,
                            result_id=v["result_id"],
                            timestamp=v["timestamp"],
                            metrics_changes=v["metrics_changes"]
                        )
                        
                        self.results[k] = result
            
            # Загрузка связей пользователей и улучшений
            users_path = os.path.join(self.storage_dir, "users.json")
            if os.path.exists(users_path):
                with open(users_path, "r", encoding="utf-8") as f:
                    self.user_improvements = json.load(f)
            
            logger.debug("Данные об улучшениях успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных об улучшениях: {e}") 