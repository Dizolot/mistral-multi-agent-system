"""
Модуль тестирования агентов для оценки качества оптимизированных версий.

Этот модуль предоставляет функциональность для автоматического тестирования агентов 
на основе набора тестовых сценариев и эталонных ответов. Он позволяет оценить
производительность улучшенных версий агентов по сравнению с их базовыми версиями
перед внедрением изменений в производственную среду.
"""

import os
import json
import logging
import uuid
import datetime
from typing import Dict, List, Any, Optional, Tuple
import csv
import time

from langchain_core.language_models import BaseLLM
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from multi_agent_system.agent_analytics.data_collector import AgentDataCollector
from multi_agent_system.agent_analytics.performance_analyzer import PerformanceAnalyzer
from multi_agent_system.agent_analytics.metrics_evaluator import MetricsEvaluator

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentTester:
    """
    Класс для тестирования агентов и оценки эффективности их оптимизации.
    
    Этот класс предоставляет методы для:
    1. Создания и управления тестовыми наборами для агентов
    2. Проведения A/B тестирования между различными версиями агентов
    3. Оценки и сравнения производительности агентов на стандартных задачах
    4. Определения готовности агента к продуктивному использованию
    """
    
    def __init__(
        self,
        llm: Optional[BaseLLM] = None,
        data_collector: Optional[AgentDataCollector] = None,
        performance_analyzer: Optional[PerformanceAnalyzer] = None,
        metrics_evaluator: Optional[MetricsEvaluator] = None,
        test_datasets_dir: str = "agent_developer/test_datasets",
        test_results_dir: str = "agent_developer/test_results"
    ):
        """
        Инициализирует тестировщик агентов.
        
        Args:
            llm: Языковая модель для оценки ответов агентов
            data_collector: Сборщик данных для хранения результатов тестирования
            performance_analyzer: Анализатор производительности для обработки результатов
            metrics_evaluator: Оценщик метрик для сравнения версий агентов
            test_datasets_dir: Директория для хранения тестовых наборов данных
            test_results_dir: Директория для хранения результатов тестирования
        """
        self.llm = llm or ChatMistralAI(
            model="mistral-medium",
            mistral_api_url="http://localhost:8080/completion"
        )
        
        self.data_collector = data_collector or AgentDataCollector()
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer()
        self.metrics_evaluator = metrics_evaluator or MetricsEvaluator()
        
        # Создаем директории, если они не существуют
        self.test_datasets_dir = test_datasets_dir
        os.makedirs(self.test_datasets_dir, exist_ok=True)
        
        self.test_results_dir = test_results_dir
        os.makedirs(self.test_results_dir, exist_ok=True)
        
        # Загружаем базовые промпты для оценки
        self._create_evaluation_prompts()
    
    def _create_evaluation_prompts(self):
        """Создает промпты для оценки результатов тестирования."""
        self.comparison_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Ты - объективный оценщик ответов AI-агентов. 
            Твоя задача - сравнить два ответа на один и тот же вопрос: исходный ответ агента и ответ улучшенной версии.
            Оцени каждый из ответов по шкале от 1 до 10 по следующим критериям:
            - Точность (соответствие вопросу, фактическая корректность)
            - Полнота (охват всех аспектов вопроса)
            - Ясность (понятность, структурированность)
            - Эффективность (лаконичность, отсутствие лишней информации)
            
            В итоге определи, является ли улучшенная версия действительно лучше исходной.
            """),
            HumanMessage(content="""
            Вопрос: {question}
            
            Ответ исходного агента: {original_answer}
            
            Ответ улучшенной версии: {improved_answer}
            
            Проведи подробный анализ обоих ответов по указанным критериям и определи:
            1. Оценки по каждому критерию для обоих ответов
            2. Общий итог - какой ответ лучше и почему
            3. Итоговое решение в формате "ЛУЧШЕ" (если улучшенная версия превосходит исходную),
               "ХУЖЕ" (если улучшенная версия уступает исходной) или
               "ОДИНАКОВО" (если обе версии примерно равноценны)
            """)
        ])
        
        self.feedback_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Ты - эксперт по оценке ответов AI-агентов.
            Твоя задача - проанализировать ответ агента на конкретный вопрос и предоставить
            подробную обратную связь о том, как этот ответ можно улучшить.
            """),
            HumanMessage(content="""
            Вопрос: {question}
            Эталонный ответ (если доступен): {reference_answer}
            Ответ агента: {agent_answer}
            
            Пожалуйста, предоставь:
            1. Оценку ответа по шкале от 1 до 10
            2. Подробный анализ сильных и слабых сторон ответа
            3. Конкретные рекомендации по улучшению
            """)
        ])
    
    def create_test_dataset(
        self,
        agent_name: str,
        test_cases: List[Dict[str, Any]],
        dataset_name: Optional[str] = None
    ) -> str:
        """
        Создает новый тестовый набор данных для агента.
        
        Args:
            agent_name: Имя агента, для которого создается набор
            test_cases: Список тестовых случаев в формате [{"question": "...", "reference_answer": "..."}]
            dataset_name: Имя набора данных (по умолчанию генерируется автоматически)
            
        Returns:
            Идентификатор созданного тестового набора
        """
        dataset_id = dataset_name or f"{agent_name}_dataset_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        dataset = {
            "dataset_id": dataset_id,
            "agent_name": agent_name,
            "created_at": datetime.datetime.now().isoformat(),
            "test_cases": test_cases
        }
        
        file_path = os.path.join(self.test_datasets_dir, f"{dataset_id}.json")
        with open(file_path, 'w') as f:
            json.dump(dataset, f, indent=2)
        
        logger.info(f"Создан тестовый набор данных: {dataset_id} для агента {agent_name}")
        return dataset_id
    
    def get_test_datasets(self, agent_name: Optional[str] = None) -> List[str]:
        """
        Получает список доступных тестовых наборов.
        
        Args:
            agent_name: Если указано, возвращает только наборы для конкретного агента
            
        Returns:
            Список идентификаторов тестовых наборов
        """
        datasets = []
        for filename in os.listdir(self.test_datasets_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.test_datasets_dir, filename)
                with open(file_path, 'r') as f:
                    dataset = json.load(f)
                
                if not agent_name or dataset.get('agent_name') == agent_name:
                    datasets.append(dataset['dataset_id'])
        
        return datasets
    
    def run_single_test(
        self,
        agent_system_prompt: str,
        question: str,
        reference_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Запускает один тестовый случай для агента.
        
        Args:
            agent_system_prompt: Системный промпт агента
            question: Вопрос для тестирования
            reference_answer: Эталонный ответ (если доступен)
            
        Returns:
            Результат тестирования с ответом агента и оценкой
        """
        start_time = time.time()
        
        # Создаем временный агент с указанным системным промптом
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=agent_system_prompt),
            HumanMessage(content=question)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            # Запускаем агента
            agent_answer = chain.invoke({})
            processing_time = time.time() - start_time
            
            # Если есть эталонный ответ, оцениваем ответ агента
            evaluation = None
            if reference_answer:
                evaluation_chain = self.feedback_prompt | self.llm | StrOutputParser()
                evaluation = evaluation_chain.invoke({
                    "question": question,
                    "reference_answer": reference_answer,
                    "agent_answer": agent_answer
                })
            
            return {
                "question": question,
                "reference_answer": reference_answer,
                "agent_answer": agent_answer,
                "processing_time": processing_time,
                "evaluation": evaluation,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Ошибка при тестировании: {str(e)}")
            return {
                "question": question,
                "reference_answer": reference_answer,
                "agent_answer": None,
                "processing_time": time.time() - start_time,
                "evaluation": None,
                "status": "error",
                "error_message": str(e)
            }
    
    def test_agent(
        self,
        agent_name: str,
        agent_system_prompt: str,
        dataset_id: str
    ) -> Dict[str, Any]:
        """
        Тестирует агента на указанном наборе данных.
        
        Args:
            agent_name: Имя агента
            agent_system_prompt: Системный промпт агента
            dataset_id: Идентификатор тестового набора
            
        Returns:
            Результаты тестирования агента
        """
        # Загружаем тестовый набор
        dataset_path = os.path.join(self.test_datasets_dir, f"{dataset_id}.json")
        if not os.path.exists(dataset_path):
            logger.error(f"Тестовый набор {dataset_id} не найден")
            return {"error": f"Тестовый набор {dataset_id} не найден"}
        
        with open(dataset_path, 'r') as f:
            dataset = json.load(f)
        
        # Запускаем тесты
        test_results = []
        success_count = 0
        total_tests = len(dataset['test_cases'])
        total_time = 0
        
        for idx, test_case in enumerate(dataset['test_cases']):
            logger.info(f"Запуск теста {idx+1}/{total_tests} для агента {agent_name}")
            result = self.run_single_test(
                agent_system_prompt=agent_system_prompt,
                question=test_case['question'],
                reference_answer=test_case.get('reference_answer')
            )
            
            test_results.append(result)
            if result['status'] == 'success':
                success_count += 1
                total_time += result['processing_time']
        
        # Формируем итоговый отчет
        avg_time = total_time / success_count if success_count > 0 else 0
        test_id = f"{agent_name}_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        test_summary = {
            "test_id": test_id,
            "agent_name": agent_name,
            "dataset_id": dataset_id,
            "executed_at": datetime.datetime.now().isoformat(),
            "success_rate": success_count / total_tests if total_tests > 0 else 0,
            "total_tests": total_tests,
            "success_count": success_count,
            "average_processing_time": avg_time,
            "test_results": test_results
        }
        
        # Сохраняем результаты
        result_path = os.path.join(self.test_results_dir, f"{test_id}.json")
        with open(result_path, 'w') as f:
            json.dump(test_summary, f, indent=2)
        
        logger.info(f"Тестирование агента {agent_name} завершено. Успешных тестов: {success_count}/{total_tests}")
        return test_summary
    
    def compare_agents(
        self,
        original_agent_name: str,
        original_system_prompt: str,
        improved_agent_name: str,
        improved_system_prompt: str,
        dataset_id: str
    ) -> Dict[str, Any]:
        """
        Сравнивает две версии агента на одном наборе данных.
        
        Args:
            original_agent_name: Имя оригинального агента
            original_system_prompt: Системный промпт оригинального агента
            improved_agent_name: Имя улучшенного агента
            improved_system_prompt: Системный промпт улучшенного агента
            dataset_id: Идентификатор тестового набора
            
        Returns:
            Результаты сравнения двух версий агента
        """
        # Тестируем обе версии агента
        original_results = self.test_agent(
            agent_name=original_agent_name,
            agent_system_prompt=original_system_prompt,
            dataset_id=dataset_id
        )
        
        improved_results = self.test_agent(
            agent_name=improved_agent_name,
            agent_system_prompt=improved_system_prompt,
            dataset_id=dataset_id
        )
        
        # Проводим детальное сравнение ответов
        comparison_results = []
        better_count = 0
        worse_count = 0
        equal_count = 0
        
        for i in range(len(original_results["test_results"])):
            original_result = original_results["test_results"][i]
            improved_result = improved_results["test_results"][i]
            
            if original_result["status"] == "success" and improved_result["status"] == "success":
                comparison_chain = self.comparison_prompt | self.llm | StrOutputParser()
                
                comparison = comparison_chain.invoke({
                    "question": original_result["question"],
                    "original_answer": original_result["agent_answer"],
                    "improved_answer": improved_result["agent_answer"]
                })
                
                # Определяем итоговый результат сравнения
                if "ЛУЧШЕ" in comparison:
                    comparison_outcome = "better"
                    better_count += 1
                elif "ХУЖЕ" in comparison:
                    comparison_outcome = "worse"
                    worse_count += 1
                else:
                    comparison_outcome = "equal"
                    equal_count += 1
            else:
                comparison = "Не удалось провести сравнение из-за ошибки в одном из агентов"
                comparison_outcome = "error"
            
            comparison_results.append({
                "question": original_result["question"],
                "original_answer": original_result.get("agent_answer"),
                "improved_answer": improved_result.get("agent_answer"),
                "comparison": comparison,
                "outcome": comparison_outcome
            })
        
        total_comparisons = better_count + worse_count + equal_count
        
        # Формируем итоговый отчет сравнения
        comparison_id = f"comparison_{original_agent_name}_vs_{improved_agent_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        comparison_summary = {
            "comparison_id": comparison_id,
            "original_agent": original_agent_name,
            "improved_agent": improved_agent_name,
            "dataset_id": dataset_id,
            "executed_at": datetime.datetime.now().isoformat(),
            "improvement_rate": better_count / total_comparisons if total_comparisons > 0 else 0,
            "better_count": better_count,
            "worse_count": worse_count,
            "equal_count": equal_count,
            "total_comparisons": total_comparisons,
            "original_success_rate": original_results["success_rate"],
            "improved_success_rate": improved_results["success_rate"],
            "original_avg_time": original_results["average_processing_time"],
            "improved_avg_time": improved_results["average_processing_time"],
            "comparison_results": comparison_results
        }
        
        # Определяем, стоит ли внедрять улучшенную версию
        recommendation = "accept" if better_count > worse_count else "reject"
        comparison_summary["recommendation"] = recommendation
        
        # Сохраняем результаты сравнения
        result_path = os.path.join(self.test_results_dir, f"{comparison_id}.json")
        with open(result_path, 'w') as f:
            json.dump(comparison_summary, f, indent=2)
        
        logger.info(f"Сравнение агентов завершено. Результат: {better_count} лучше, {worse_count} хуже, {equal_count} равно")
        return comparison_summary
    
    def export_results_to_csv(self, test_id: str, output_path: Optional[str] = None) -> str:
        """
        Экспортирует результаты тестирования в CSV-формат для удобного анализа.
        
        Args:
            test_id: Идентификатор теста
            output_path: Путь для сохранения CSV-файла (по умолчанию генерируется автоматически)
            
        Returns:
            Путь к созданному CSV-файлу
        """
        result_path = os.path.join(self.test_results_dir, f"{test_id}.json")
        if not os.path.exists(result_path):
            logger.error(f"Результат теста {test_id} не найден")
            return f"Ошибка: Результат теста {test_id} не найден"
        
        with open(result_path, 'r') as f:
            test_results = json.load(f)
        
        output_path = output_path or os.path.join(self.test_results_dir, f"{test_id}.csv")
        
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = ['question', 'status', 'processing_time', 'has_evaluation']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in test_results['test_results']:
                writer.writerow({
                    'question': result['question'],
                    'status': result['status'],
                    'processing_time': result.get('processing_time', ''),
                    'has_evaluation': 'Yes' if result.get('evaluation') else 'No'
                })
        
        logger.info(f"Результаты теста {test_id} экспортированы в {output_path}")
        return output_path
    
    def generate_benchmark_questions(
        self,
        agent_name: str,
        agent_description: str,
        categories: List[str],
        questions_per_category: int = 5
    ) -> str:
        """
        Автоматически генерирует тестовые вопросы для агента на основе его описания.
        
        Args:
            agent_name: Имя агента
            agent_description: Описание агента и его специализации
            categories: Категории вопросов (например, ["базовые", "сложные", "edge cases"])
            questions_per_category: Количество вопросов для каждой категории
            
        Returns:
            Идентификатор созданного тестового набора
        """
        benchmark_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Ты - эксперт по созданию тестовых сценариев для AI-агентов.
            Твоя задача - создать набор разнообразных и содержательных вопросов для тестирования
            специализированного агента на основе его описания.
            """),
            HumanMessage(content="""
            Мне нужно создать тестовый набор для агента со следующими характеристиками:
            
            Имя агента: {agent_name}
            Описание и специализация: {agent_description}
            
            Пожалуйста, создай {questions_per_category} вопросов для каждой из следующих категорий:
            {categories}
            
            Для каждого вопроса также предоставь:
            1. Краткое описание, почему этот вопрос важен для тестирования
            2. Если возможно, эталонный ответ или ключевые моменты, которые должны быть в хорошем ответе
            
            Верни результат в JSON формате с массивом объектов, где каждый объект содержит:
            - question: текст вопроса
            - category: категория вопроса
            - description: описание важности вопроса
            - reference_answer: эталонный ответ (если возможно)
            """)
        ])
        
        try:
            generation_chain = benchmark_prompt | self.llm | StrOutputParser()
            
            result = generation_chain.invoke({
                "agent_name": agent_name,
                "agent_description": agent_description,
                "categories": ", ".join(categories),
                "questions_per_category": questions_per_category
            })
            
            # Извлекаем JSON из результата
            json_start = result.find('[')
            json_end = result.rfind(']') + 1
            if json_start == -1 or json_end == 0:
                logger.error("Не удалось найти JSON в результате генерации")
                # Попробуем сформировать базовый набор вручную
                test_cases = []
                for category in categories:
                    for i in range(questions_per_category):
                        test_cases.append({
                            "question": f"Тестовый вопрос {i+1} для категории {category}",
                            "category": category,
                            "description": "Автоматически сгенерированный тестовый вопрос",
                            "reference_answer": None
                        })
            else:
                json_str = result[json_start:json_end]
                test_cases = json.loads(json_str)
            
            # Создаем тестовый набор
            dataset_id = self.create_test_dataset(
                agent_name=agent_name,
                test_cases=test_cases,
                dataset_name=f"{agent_name}_benchmark_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            return dataset_id
            
        except Exception as e:
            logger.error(f"Ошибка при генерации тестового набора: {str(e)}")
            return f"Ошибка: {str(e)}"

# Если файл запущен как скрипт, выполняем базовую демонстрацию
if __name__ == "__main__":
    # Создаем директорию для тестовых данных, если не существует
    os.makedirs("agent_developer/test_datasets", exist_ok=True)
    
    # Инициализируем тестировщик
    tester = AgentTester()
    
    # Создаем простой тестовый набор
    test_cases = [
        {
            "question": "Что такое Python?",
            "reference_answer": "Python - это высокоуровневый интерпретируемый язык программирования общего назначения с акцентом на читаемость кода."
        },
        {
            "question": "Как создать список в Python?",
            "reference_answer": "Список в Python можно создать несколькими способами: используя квадратные скобки [], функцию list() или списковое включение [x for x in range(10)]."
        }
    ]
    
    dataset_id = tester.create_test_dataset(
        agent_name="python_agent",
        test_cases=test_cases
    )
    
    print(f"Создан тестовый набор: {dataset_id}") 