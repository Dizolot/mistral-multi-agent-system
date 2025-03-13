import os
import json
from datetime import datetime


class PerformanceAnalyzer:
    def __init__(self, data_collector_instance=None, results_dir=None):
        self.data_collector_instance = data_collector_instance
        if results_dir is None:
            self.results_dir = os.path.join("multi_agent_system", "agent_analytics", "results")
        else:
            self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)

    def analyze_agent_performance(self, agent_name):
        if self.data_collector_instance:
            interactions = self.data_collector_instance.get_interactions(agent_name=agent_name)
        else:
            interactions = []
        total = len(interactions)
        if total == 0:
            success_rate = 0.0
            avg_processing_time = 0.0
        else:
            successes = sum(1 for i in interactions if i.get("is_successful") == True)
            success_rate = successes / total
            total_time = sum(i.get("processing_time", 0) for i in interactions)
            avg_processing_time = total_time / total

        # Выделяем неуспешные взаимодействия
        failed_interactions = [i for i in interactions if not i.get("is_successful", True)]
        problematic_patterns = self.identify_problematic_patterns(failed_interactions)
        recommendations = self.generate_recommendations(problematic_patterns)

        result = {
            "agent_name": agent_name,
            "metrics": {
                "success_rate": success_rate,
                "avg_processing_time": avg_processing_time
            },
            "problematic_patterns": problematic_patterns,
            "recommendations": recommendations
        }
        return result

    def identify_problematic_patterns(self, interactions):
        error_counts = {}
        for interaction in interactions:
            # Ищем ошибку сначала в корневых полях, затем в metadata
            error = interaction.get("error")
            if error is None and "metadata" in interaction and isinstance(interaction["metadata"], dict):
                error = interaction["metadata"].get("error")
            if error:
                error_counts[error] = error_counts.get(error, 0) + 1
        # Возвращаем ошибки, встречающиеся минимум 2 раза
        return [err for err, count in error_counts.items() if count >= 2]

    def generate_recommendations(self, problematic_patterns):
        recommendations = []
        for pattern in problematic_patterns:
            if "не найден интерпретатор" in pattern.lower():
                recommendations.append("Убедитесь, что Python интерпретатор установлен и доступен.")
            elif "недостаточно информации" in pattern.lower():
                recommendations.append("Проверьте полноту входных данных для агента.")
            else:
                recommendations.append(f"Рекомендация по устранению проблемы: {pattern}")
        return recommendations

    def save_analysis_result(self, result):
        filename = os.path.join(self.results_dir, "analysis_result.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2) 