"""
Модуль для расчета различных метрик качества работы агентов.
Предоставляет функции для оценки точности, релевантности и других параметров ответов.
"""
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union

# Локальные импорты
from multi_agent_system.logger import get_logger

# Настройка логгера
logger = get_logger(__name__)

class MetricsEvaluator:
    """
    Класс для расчета метрик качества работы агентов.
    Оценивает точность, релевантность, грамматическую корректность и другие параметры ответов.
    """
    
    def __init__(self):
        """
        Инициализация оценщика метрик.
        """
        logger.info("MetricsEvaluator инициализирован")
    
    def evaluate_response_quality(
        self, 
        request: str, 
        response: str,
        reference_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Оценивает качество ответа агента.
        
        Args:
            request: Запрос пользователя
            response: Ответ агента
            reference_answer: Эталонный ответ (если есть)
            
        Returns:
            Dict[str, Any]: Результаты оценки качества
        """
        results = {}
        
        # Базовые метрики
        results["length"] = len(response.split())
        results["response_to_request_ratio"] = len(response) / len(request) if len(request) > 0 else 0
        
        # Проверка на пустой ответ
        results["is_empty"] = len(response.strip()) == 0
        
        # Проверка на формальности (приветствие, прощание)
        results["has_greeting"] = bool(re.search(r"(здравствуйте|привет|добрый день|приветствую)", 
                                                response.lower()))
        results["has_farewell"] = bool(re.search(r"(до свидания|всего хорошего|всего доброго|удачи)", 
                                               response.lower()))
        
        # Проверка на наличие информации о неспособности ответить
        results["has_inability_statement"] = bool(re.search(
            r"(не могу|не знаю|затрудняюсь|не имею информации|нет данных)", 
            response.lower()
        ))
        
        # Оценка связности ответа
        results["coherence"] = self._evaluate_coherence(response)
        
        # Оценка релевантности ответа запросу
        results["relevance"] = self._evaluate_relevance(request, response)
        
        # Если есть эталонный ответ, сравниваем с ним
        if reference_answer:
            results["similarity_to_reference"] = self._evaluate_similarity(response, reference_answer)
        
        # Общая оценка качества (взвешенная сумма других метрик)
        results["overall_quality"] = self._calculate_overall_quality(results)
        
        return results
    
    def evaluate_agent_improvement(
        self,
        old_responses: List[Dict[str, Any]],
        new_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Оценивает улучшение работы агента после внесенных изменений.
        
        Args:
            old_responses: Список старых ответов (запрос, ответ, метаданные)
            new_responses: Список новых ответов на те же запросы
            
        Returns:
            Dict[str, Any]: Результаты оценки улучшения
        """
        if len(old_responses) != len(new_responses):
            logger.warning("Количество старых и новых ответов не совпадает. Анализ может быть неточным.")
        
        # Сопоставляем старые и новые ответы по запросам
        paired_responses = []
        
        for old_resp in old_responses:
            old_request = old_resp.get("request", "")
            old_response = old_resp.get("response", "")
            
            # Ищем соответствующий новый ответ
            for new_resp in new_responses:
                if new_resp.get("request", "") == old_request:
                    paired_responses.append({
                        "request": old_request,
                        "old_response": old_response,
                        "new_response": new_resp.get("response", ""),
                        "old_metadata": old_resp.get("metadata", {}),
                        "new_metadata": new_resp.get("metadata", {})
                    })
                    break
        
        # Оцениваем улучшения для каждой пары ответов
        improvements = []
        for pair in paired_responses:
            old_quality = self.evaluate_response_quality(pair["request"], pair["old_response"])
            new_quality = self.evaluate_response_quality(pair["request"], pair["new_response"])
            
            # Рассчитываем разницу в метриках
            diff = {}
            for metric in old_quality:
                if metric in new_quality:
                    diff[metric] = new_quality[metric] - old_quality[metric]
            
            improvements.append({
                "request": pair["request"],
                "old_quality": old_quality,
                "new_quality": new_quality,
                "diff": diff,
                "improved": new_quality["overall_quality"] > old_quality["overall_quality"]
            })
        
        # Общая статистика улучшений
        total_pairs = len(paired_responses)
        improved_count = sum(1 for imp in improvements if imp["improved"])
        
        improvement_summary = {
            "total_examples": total_pairs,
            "improved_count": improved_count,
            "improved_percentage": (improved_count / total_pairs * 100) if total_pairs > 0 else 0,
            "average_quality_change": sum(imp["diff"]["overall_quality"] for imp in improvements) / total_pairs if total_pairs > 0 else 0,
            "detailed_improvements": improvements
        }
        
        return improvement_summary
    
    def _evaluate_coherence(self, text: str) -> float:
        """
        Оценивает связность текста.
        
        Args:
            text: Текст для оценки
            
        Returns:
            float: Оценка связности (от 0 до 1)
        """
        # Простая реализация оценки связности:
        # - Проверяем наличие связующих слов
        # - Проверяем среднюю длину предложений
        # - Проверяем переходы между предложениями
        
        # Разбиваем текст на предложения
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        # Подсчитываем среднюю длину предложений
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Проверяем наличие связующих слов
        connective_words = [
            "поэтому", "таким образом", "следовательно", "в результате", 
            "однако", "тем не менее", "кроме того", "также", "с другой стороны"
        ]
        
        connectives_count = sum(1 for word in connective_words if word in text.lower())
        
        # Рассчитываем базовую оценку связности
        length_score = min(1.0, avg_sentence_length / 15.0)  # Оптимальная длина ~15 слов
        connective_score = min(1.0, connectives_count / 3.0)  # Оптимально ~3 связующих слова
        
        # Финальная оценка связности
        coherence = (length_score * 0.5 + connective_score * 0.5)
        
        return coherence
    
    def _evaluate_relevance(self, request: str, response: str) -> float:
        """
        Оценивает релевантность ответа запросу.
        
        Args:
            request: Запрос пользователя
            response: Ответ агента
            
        Returns:
            float: Оценка релевантности (от 0 до 1)
        """
        # Простая реализация оценки релевантности:
        # - Проверяем пересечение ключевых слов между запросом и ответом
        
        # Приводим тексты к нижнему регистру и удаляем пунктуацию
        request_clean = re.sub(r'[^\w\s]', '', request.lower())
        response_clean = re.sub(r'[^\w\s]', '', response.lower())
        
        # Получаем множества слов
        request_words = set(request_clean.split())
        response_words = set(response_clean.split())
        
        # Исключаем стоп-слова (можно расширить список)
        stop_words = {"и", "в", "на", "с", "по", "у", "к", "о", "из", "за", "для", "что", "как", "или", "это"}
        request_words = request_words - stop_words
        response_words = response_words - stop_words
        
        if not request_words:
            return 0.5  # Нейтральная оценка при отсутствии значимых слов в запросе
        
        # Вычисляем коэффициент Жаккара (отношение пересечения к объединению)
        intersection = len(request_words.intersection(response_words))
        union = len(request_words.union(response_words))
        
        jaccard = intersection / union if union > 0 else 0
        
        # Корректируем оценку с учетом длины ответа
        response_length_factor = min(1.0, len(response_words) / 10.0)  # Поощряем более развернутые ответы
        
        relevance = jaccard * 0.7 + response_length_factor * 0.3
        
        return relevance
    
    def _evaluate_similarity(self, text1: str, text2: str) -> float:
        """
        Оценивает сходство двух текстов.
        
        Args:
            text1: Первый текст
            text2: Второй текст
            
        Returns:
            float: Оценка сходства (от 0 до 1)
        """
        # Простая реализация оценки сходства:
        # - Используем коэффициент Жаккара на уровне слов
        
        # Приводим тексты к нижнему регистру и удаляем пунктуацию
        text1_clean = re.sub(r'[^\w\s]', '', text1.lower())
        text2_clean = re.sub(r'[^\w\s]', '', text2.lower())
        
        # Получаем множества слов
        words1 = set(text1_clean.split())
        words2 = set(text2_clean.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Вычисляем коэффициент Жаккара (отношение пересечения к объединению)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        jaccard = intersection / union if union > 0 else 0
        
        return jaccard
    
    def _calculate_overall_quality(self, metrics: Dict[str, Any]) -> float:
        """
        Рассчитывает общую оценку качества ответа на основе отдельных метрик.
        
        Args:
            metrics: Словарь с различными метриками качества
            
        Returns:
            float: Общая оценка качества (от 0 до 1)
        """
        # Определяем веса для разных метрик
        weights = {
            "coherence": 0.4,
            "relevance": 0.5,
            "has_inability_statement": -0.3,  # Штраф за признание неспособности ответить
            "is_empty": -0.9  # Сильный штраф за пустой ответ
        }
        
        # Базовая оценка
        score = 0.5
        
        # Учитываем метрики с положительными весами
        for metric, weight in weights.items():
            if weight > 0 and metric in metrics:
                score += metrics[metric] * weight
        
        # Учитываем штрафы (метрики с отрицательными весами)
        for metric, weight in weights.items():
            if weight < 0 and metric in metrics:
                # Для бинарных метрик (True/False)
                if isinstance(metrics[metric], bool):
                    if metrics[metric]:
                        score += weight  # Применяем штраф
                else:
                    score += metrics[metric] * weight
        
        # Ограничиваем оценку диапазоном [0, 1]
        return max(0.0, min(1.0, score))

# Создаем экземпляр оценщика метрик для использования в других модулях
metrics_evaluator = MetricsEvaluator() 