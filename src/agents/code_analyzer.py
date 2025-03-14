"""
Модуль для анализа кода.
Данный модуль предоставляет класс CodeAnalyzer, который
выполняет анализ кода на различных языках программирования.
"""

import re
from typing import Dict, List, Any, Optional, Tuple


class CodeAnalyzer:
    """
    Анализатор кода для различных языков программирования.
    Выявляет потенциальные проблемы, сложность и предлагает улучшения.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация анализатора кода.
        
        Args:
            config (Dict[str, Any], optional): Конфигурация анализатора.
        """
        self.config = config or {}
        
        # Поддерживаемые языки и их специфичные анализаторы
        self.language_analyzers = {
            "python": self._analyze_python,
            "javascript": self._analyze_javascript,
            "java": self._analyze_java,
            # Можно добавить другие языки по мере необходимости
        }
    
    def analyze(self, code: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Анализирует предоставленный код.
        
        Args:
            code (str): Исходный код для анализа.
            language (str, optional): Язык программирования. 
                                     Если не указан, определяется автоматически.
        
        Returns:
            Dict[str, Any]: Результаты анализа, включая проблемы, метрики и предложения.
        """
        # Определение языка, если не указан
        if language is None:
            language = self._detect_language(code)
        
        # Базовый анализ, применимый ко всем языкам
        result = self._perform_common_analysis(code)
        
        # Специфичный для языка анализ
        if language.lower() in self.language_analyzers:
            language_specific_result = self.language_analyzers[language.lower()](code)
            # Объединение результатов
            result = self._merge_analysis_results(result, language_specific_result)
        
        return result
    
    def _detect_language(self, code: str) -> str:
        """
        Определяет язык программирования на основе содержимого кода.
        
        Args:
            code (str): Исходный код для анализа.
        
        Returns:
            str: Предполагаемый язык программирования.
        """
        # Простая эвристика для определения языка
        if "def " in code and ":" in code:
            return "python"
        elif "function " in code and "{" in code:
            return "javascript"
        elif "public class " in code or "private class " in code:
            return "java"
        else:
            # По умолчанию используем Python
            return "python"
    
    def _perform_common_analysis(self, code: str) -> Dict[str, Any]:
        """
        Выполняет общий анализ, применимый ко всем языкам.
        
        Args:
            code (str): Исходный код для анализа.
        
        Returns:
            Dict[str, Any]: Базовые результаты анализа.
        """
        lines = code.strip().split("\n")
        line_count = len(lines)
        
        # Расчет базовых метрик
        complexity_score = self._calculate_complexity(code)
        maintainability_index = self._calculate_maintainability(code)
        
        # Выявление общих проблем
        issues = []
        suggestions = []
        
        # Проверка длины строк
        for i, line in enumerate(lines):
            if len(line) > 100:
                issues.append({
                    "type": "long_line",
                    "line": i + 1,
                    "message": f"Строка {i + 1} превышает рекомендуемую длину в 100 символов."
                })
                suggestions.append({
                    "type": "refactor_long_line",
                    "line": i + 1,
                    "message": "Разбейте длинную строку на несколько строк для улучшения читаемости."
                })
        
        # Результаты анализа
        result = {
            "issues": issues,
            "suggestions": suggestions,
            "metrics": {
                "line_count": line_count,
                "complexity_score": complexity_score,
                "maintainability_index": maintainability_index
            }
        }
        
        return result
    
    def _calculate_complexity(self, code: str) -> float:
        """
        Рассчитывает примерную цикломатическую сложность кода.
        
        Args:
            code (str): Исходный код для анализа.
        
        Returns:
            float: Оценка сложности.
        """
        # Простой подсчет ключевых слов, увеличивающих сложность
        complexity_keywords = ["if ", "else ", "for ", "while ", "try ", "catch ", "case "]
        complexity = 1.0  # Базовая сложность
        
        for keyword in complexity_keywords:
            complexity += code.count(keyword) * 0.5
        
        return round(complexity, 2)
    
    def _calculate_maintainability(self, code: str) -> float:
        """
        Рассчитывает индекс обслуживаемости кода.
        
        Args:
            code (str): Исходный код для анализа.
        
        Returns:
            float: Индекс обслуживаемости.
        """
        # Упрощенная формула для индекса обслуживаемости
        line_count = len(code.strip().split("\n"))
        avg_line_length = len(code) / max(line_count, 1)
        complexity = self._calculate_complexity(code)
        
        # Формула основана на метриках:
        # - Количество строк
        # - Средняя длина строки
        # - Сложность
        maintainability = 100.0 - (line_count * 0.1) - (avg_line_length * 0.1) - (complexity * 2.0)
        
        # Ограничиваем индекс обслуживаемости значениями от 0 до 100
        maintainability = max(0.0, min(100.0, maintainability))
        
        return round(maintainability, 2)
    
    def _analyze_python(self, code: str) -> Dict[str, Any]:
        """
        Выполняет анализ для Python-кода.
        
        Args:
            code (str): Исходный код Python для анализа.
        
        Returns:
            Dict[str, Any]: Результаты анализа, специфичные для Python.
        """
        issues = []
        suggestions = []
        
        # Проверка наличия документации
        functions = re.findall(r"def\s+(\w+)\s*\([^)]*\)\s*:", code)
        for func_name in functions:
            docstring_pattern = f"def\\s+{func_name}\\s*\\([^)]*\\)\\s*:\\s*(\"\"\"|''')"
            if not re.search(docstring_pattern, code):
                issues.append({
                    "type": "missing_docstring",
                    "message": f"Функция '{func_name}' не имеет документации."
                })
                suggestions.append({
                    "type": "add_docstring",
                    "message": f"Добавьте документацию для функции '{func_name}'."
                })
        
        # Проверка стиля именования
        if re.search(r"class\s+[a-z]", code):
            issues.append({
                "type": "naming_convention",
                "message": "Имена классов должны начинаться с заглавной буквы."
            })
            suggestions.append({
                "type": "rename_class",
                "message": "Переименуйте классы, начинающиеся со строчной буквы, в соответствии с PEP 8."
            })
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "metrics": {
                "function_count": len(functions)
            }
        }
    
    def _analyze_javascript(self, code: str) -> Dict[str, Any]:
        """
        Выполняет анализ для JavaScript-кода.
        
        Args:
            code (str): Исходный код JavaScript для анализа.
        
        Returns:
            Dict[str, Any]: Результаты анализа, специфичные для JavaScript.
        """
        # Заглушка для JavaScript-анализатора
        return {
            "issues": [],
            "suggestions": [],
            "metrics": {}
        }
    
    def _analyze_java(self, code: str) -> Dict[str, Any]:
        """
        Выполняет анализ для Java-кода.
        
        Args:
            code (str): Исходный код Java для анализа.
        
        Returns:
            Dict[str, Any]: Результаты анализа, специфичные для Java.
        """
        # Заглушка для Java-анализатора
        return {
            "issues": [],
            "suggestions": [],
            "metrics": {}
        }
    
    def _merge_analysis_results(self, result1: Dict[str, Any], result2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Объединяет результаты анализа из разных источников.
        
        Args:
            result1 (Dict[str, Any]): Первый результат анализа.
            result2 (Dict[str, Any]): Второй результат анализа.
        
        Returns:
            Dict[str, Any]: Объединенные результаты анализа.
        """
        merged_result = {
            "issues": result1.get("issues", []) + result2.get("issues", []),
            "suggestions": result1.get("suggestions", []) + result2.get("suggestions", []),
            "metrics": {**result1.get("metrics", {}), **result2.get("metrics", {})}
        }
        
        return merged_result 