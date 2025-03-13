import os


class MetricsEvaluator:
    def __init__(self):
        pass

    def evaluate_response_quality(self, request, response, reference_answer=None):
        # Вычисляем базовые метрики на основе длины ответа
        overall_quality = len(response) / 10.0
        relevance = len(response) / 12.0
        coherence = len(response) / 15.0
        result = {
            "overall_quality": overall_quality,
            "relevance": relevance,
            "coherence": coherence
        }
        if reference_answer:
            words_resp = set(response.lower().split())
            words_ref = set(reference_answer.lower().split())
            similarity = len(words_resp & words_ref) / len(words_ref) if words_ref else 0.0
            result["similarity_to_reference"] = similarity
        return result

    def evaluate_agent_improvement(self, old_responses, new_responses):
        # Вычисляем разницу среднего значения overall_quality между новыми и старыми ответами
        if not old_responses or not new_responses:
            return 0.0
        old_avg = sum(resp["metrics"]["overall_quality"] for resp in old_responses) / len(old_responses)
        new_avg = sum(resp["metrics"]["overall_quality"] for resp in new_responses) / len(new_responses)
        return new_avg - old_avg

    def evaluate_coherence(self, text):
        # Простая оценка связности: пропорциональна длине текста
        return len(text) / 100.0

    def evaluate_relevance(self, text, query):
        # Оценка релевантности на основе пересечения слов
        words_text = set(text.lower().split())
        words_query = set(query.lower().split())
        if not words_query:
            return 0.0
        return len(words_text & words_query) / len(words_query)

    def evaluate_similarity(self, text1, text2):
        # Похожесть рассчитывается как отношение пересечения к объединению слов
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / len(words1 | words2)

    def calculate_overall_quality(self, coherence, relevance):
        # Общая оценка как среднее арифметическое coherence и relevance
        return (coherence + relevance) / 2.0 