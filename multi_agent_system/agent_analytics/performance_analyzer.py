"""
Модуль для анализа эффективности агентов на основе собранных данных.
Анализирует метрики и предоставляет рекомендации по улучшению.
"""
import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Локальные импорты
from multi_agent_system.logger import get_logger
from multi_agent_system.agent_analytics.data_collector import data_collector

# Настройка логгера
logger = get_logger(__name__)

class PerformanceAnalyzer:
    """
    Класс для анализа эффективности агентов.
    Анализирует данные о взаимодействии пользователей с агентами,
    выявляет проблемные области и предоставляет рекомендации по улучшению.
    """
    
    def __init__(
        self,
        data_collector_instance = None,
        results_dir: str = "agent_analytics/results"
    ):
        """
        Инициализация анализатора эффективности.
        
        Args:
            data_collector_instance: Экземпляр коллектора данных
            results_dir: Директория для сохранения результатов анализа
        """
        self.data_collector = data_collector_instance or data_collector
        self.results_dir = results_dir
        
        # Создаем директорию для результатов, если её нет
        os.makedirs(self.results_dir, exist_ok=True)
        
        logger.info("PerformanceAnalyzer инициализирован")
    
    def analyze_agent_performance(
        self,
        agent_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_interactions: int = 10
    ) -> Dict[str, Any]:
        """
        Анализирует производительность конкретного агента.
        
        Args:
            agent_name: Имя агента для анализа
            start_date: Начальная дата анализа в формате YYYY-MM-DD
            end_date: Конечная дата анализа в формате YYYY-MM-DD
            min_interactions: Минимальное количество взаимодействий для анализа
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        # Получаем взаимодействия с агентом за указанный период
        interactions = self.data_collector.get_agent_interactions(
            agent_name=agent_name,
            start_date=start_date,
            end_date=end_date,
            limit=1000  # Увеличиваем лимит для более точного анализа
        )
        
        # Если взаимодействий недостаточно, возвращаем соответствующее сообщение
        if len(interactions) < min_interactions:
            logger.warning(f"Недостаточно данных для анализа агента {agent_name}: {len(interactions)} < {min_interactions}")
            return {
                "agent_name": agent_name,
                "status": "insufficient_data",
                "message": f"Недостаточно данных для анализа (найдено {len(interactions)}, требуется не менее {min_interactions})",
                "recommendations": []
            }
        
        # Анализируем взаимодействия
        successful_interactions = [i for i in interactions if i.get("is_successful", True)]
        failed_interactions = [i for i in interactions if not i.get("is_successful", True)]
        
        success_rate = len(successful_interactions) / len(interactions) if interactions else 0
        
        # Собираем метрики производительности
        avg_processing_time = sum(float(i.get("processing_time", 0)) for i in interactions) / len(interactions) if interactions else 0
        
        # Анализируем паттерны в запросах, с которыми агент не справляется
        problematic_patterns = self.identify_problematic_patterns(failed_interactions)
        
        # Формируем рекомендации по улучшению
        recommendations = self.generate_recommendations(
            agent_name=agent_name,
            success_rate=success_rate,
            avg_processing_time=avg_processing_time,
            problematic_patterns=problematic_patterns
        )
        
        # Формируем результат анализа
        result = {
            "agent_name": agent_name,
            "status": "success",
            "analysis_date": datetime.datetime.now().isoformat(),
            "period": {
                "start_date": start_date or "all_time",
                "end_date": end_date or "current"
            },
            "total_interactions": len(interactions),
            "metrics": {
                "success_rate": success_rate,
                "avg_processing_time": avg_processing_time,
                "failed_interactions": len(failed_interactions)
            },
            "problematic_patterns": problematic_patterns,
            "recommendations": recommendations
        }
        
        # Сохраняем результат анализа
        self._save_analysis_result(result)
        
        logger.info(f"Анализ агента {agent_name} завершен, сформировано {len(recommendations)} рекомендаций")
        
        return result
    
    def identify_problematic_patterns(self, failed_interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Выявляет паттерны в запросах, с которыми агент не справляется.
        
        Args:
            failed_interactions: Список неудачных взаимодействий
            
        Returns:
            List[Dict[str, Any]]: Список проблемных паттернов
        """
        if not failed_interactions:
            return []
        
        # Простая реализация: группируем запросы по общим словам/фразам
        patterns = []
        
        # Группируем взаимодействия по общим словам в запросах
        words_count = {}
        
        for interaction in failed_interactions:
            request = interaction.get("request", "")
            words = request.lower().split()
            
            # Подсчитываем частоту слов
            for word in words:
                if len(word) > 3:  # Игнорируем короткие слова
                    words_count[word] = words_count.get(word, 0) + 1
        
        # Находим наиболее частые слова
        common_words = sorted(words_count.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Формируем паттерны на основе частых слов
        for word, count in common_words:
            if count > 1:  # Если слово встречается более одного раза
                examples = []
                
                # Находим примеры запросов с этим словом
                for interaction in failed_interactions:
                    request = interaction.get("request", "")
                    if word in request.lower():
                        examples.append(request)
                        if len(examples) >= 3:  # Ограничиваем количество примеров
                            break
                
                patterns.append({
                    "keyword": word,
                    "frequency": count,
                    "percentage": count / len(failed_interactions) * 100,
                    "examples": examples
                })
        
        return patterns
    
    def generate_recommendations(
        self,
        agent_name: str,
        success_rate: float,
        avg_processing_time: float,
        problematic_patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Генерирует рекомендации по улучшению агента.
        
        Args:
            agent_name: Имя агента
            success_rate: Доля успешных взаимодействий
            avg_processing_time: Среднее время обработки запроса
            problematic_patterns: Список проблемных паттернов
            
        Returns:
            List[Dict[str, Any]]: Список рекомендаций
        """
        recommendations = []
        
        # Рекомендации на основе успешности взаимодействий
        if success_rate < 0.9:
            recommendations.append({
                "type": "improve_success_rate",
                "priority": "high" if success_rate < 0.7 else "medium",
                "description": f"Повысить долю успешных взаимодействий (текущая: {success_rate:.2%})",
                "details": "Агент показывает недостаточную успешность при обработке запросов. Необходимо улучшить его способность правильно интерпретировать и отвечать на запросы пользователей."
            })
        
        # Рекомендации на основе времени обработки
        if avg_processing_time > 5.0:
            recommendations.append({
                "type": "optimize_processing_time",
                "priority": "high" if avg_processing_time > 10.0 else "medium",
                "description": f"Оптимизировать время обработки запросов (текущее: {avg_processing_time:.2f} сек)",
                "details": "Агент слишком долго обрабатывает запросы, что может негативно влиять на пользовательский опыт. Необходимо оптимизировать алгоритм обработки запросов."
            })
        
        # Рекомендации на основе проблемных паттернов
        for pattern in problematic_patterns:
            if pattern["percentage"] > 20:
                recommendations.append({
                    "type": "improve_pattern_handling",
                    "priority": "high",
                    "description": f"Улучшить обработку запросов с ключевым словом '{pattern['keyword']}' (частота: {pattern['percentage']:.1f}%)",
                    "details": f"Агент часто не справляется с запросами, содержащими слово '{pattern['keyword']}'. Примеры запросов: " + ", ".join(f"'{ex}'" for ex in pattern["examples"][:2])
                })
        
        return recommendations
    
    def _save_analysis_result(self, result: Dict[str, Any]) -> None:
        """
        Сохраняет результат анализа в файл.
        
        Args:
            result: Результат анализа
        """
        try:
            # Формируем имя файла на основе имени агента и даты анализа
            agent_name = result["agent_name"]
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            file_path = os.path.join(self.results_dir, f"analysis_{agent_name}_{date_str}.json")
            
            # Сохраняем результат в файл
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Результат анализа сохранен в файл: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата анализа: {str(e)}")
    
    def compare_agents(
        self,
        agent_names: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Сравнивает эффективность нескольких агентов.
        
        Args:
            agent_names: Список имен агентов для сравнения
            start_date: Начальная дата анализа в формате YYYY-MM-DD
            end_date: Конечная дата анализа в формате YYYY-MM-DD
            
        Returns:
            Dict[str, Any]: Результаты сравнения
        """
        results = {}
        
        for agent_name in agent_names:
            results[agent_name] = self.analyze_agent_performance(
                agent_name=agent_name,
                start_date=start_date,
                end_date=end_date,
                min_interactions=5  # Снижаем порог для сравнения
            )
        
        # Выполняем сравнительный анализ
        comparison = {
            "analysis_date": datetime.datetime.now().isoformat(),
            "period": {
                "start_date": start_date or "all_time",
                "end_date": end_date or "current"
            },
            "agents": agent_names,
            "metrics_comparison": {}
        }
        
        # Сравниваем метрики
        for metric in ["success_rate", "avg_processing_time"]:
            comparison["metrics_comparison"][metric] = {}
            for agent_name in agent_names:
                if results[agent_name]["status"] == "success":
                    comparison["metrics_comparison"][metric][agent_name] = results[agent_name]["metrics"].get(metric, 0)
        
        # Определяем лучшего агента по каждой метрике
        best_agents = {}
        for metric, values in comparison["metrics_comparison"].items():
            if values:
                if metric == "success_rate":
                    best_agent = max(values.items(), key=lambda x: x[1])
                else:  # Для времени обработки лучший - с минимальным значением
                    best_agent = min(values.items(), key=lambda x: x[1])
                
                best_agents[metric] = {
                    "agent_name": best_agent[0],
                    "value": best_agent[1]
                }
        
        comparison["best_agents"] = best_agents
        
        return comparison

# Создаем экземпляр анализатора эффективности для использования в других модулях
performance_analyzer = PerformanceAnalyzer() 