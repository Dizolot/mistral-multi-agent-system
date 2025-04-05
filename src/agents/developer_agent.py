"""
Агент-разработчик для создания и улучшения кода.
"""

import logging
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path
import os
import time

from src.agents.base_agent import BaseAgent
from src.reporting.telegram_reporter import TelegramReporter
from src.agents.code_analyzer import CodeAnalyzer
from src.utils.git_manager import GitManager

from src.core.memory_system.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class DeveloperAgent(BaseAgent):
    """Агент для разработки и улучшения кода."""
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        config: Dict[str, Any],
        code_analyzer: Optional[CodeAnalyzer] = None,
        git_manager: Optional[GitManager] = None
    ):
        """
        Инициализация агента-разработчика.
        
        Args:
            memory_manager: Менеджер памяти для хранения контекста
            config: Конфигурация агента
            code_analyzer: Анализатор кода
            git_manager: Менеджер Git для работы с репозиторием
        """
        super().__init__(memory_manager, config)
        self.agent_role = "developer"
        
        # Инициализируем или используем переданный CodeAnalyzer
        if code_analyzer is None:
            self.code_analyzer = CodeAnalyzer(config)
        else:
            self.code_analyzer = code_analyzer
            
        # Инициализируем или используем переданный GitManager
        if git_manager is None:
            self.git_manager = GitManager()
        else:
            self.git_manager = git_manager
        
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка задачи по улучшению кода.
        
        Args:
            task: Данные задачи
            
        Returns:
            Результат выполнения задачи
        """
        task_result = {
            'status': 'success',
            'improvements': [],
            'branch': None,
            'files_changed': [],
            'metrics': {}
        }
        
        try:
            logger.info(f"Начало обработки задачи разработчиком: {task.get('type', 'Неизвестная задача')}")
            
            # Анализируем текущий код
            analysis = await self._analyze_code(task)
            
            # Если анализ обнаружил ошибку, возвращаем её
            if 'error' in analysis:
                task_result['status'] = 'error'
                task_result['error'] = analysis['error']
                return task_result
            
            # Отправляем сообщение о результатах анализа
            target_file = task.get('file_path', 'неизвестный файл')
            task_type = task.get('type', 'улучшение')
            task_priority = task.get('priority', 'средний')
            
            message = (
                f"🔍 Анализ кода в файле {target_file}:\n"
                f"- Тип задачи: {task_type}\n"
                f"- Приоритет: {task_priority}\n"
            )
            
            # Генерируем улучшения на основе анализа
            improvements = await self._generate_improvements(analysis)
            task_result['improvements'] = improvements
            
            if not improvements:
                task_result['status'] = 'info'
                task_result['description'] = "Не найдено возможностей для улучшения"
                return task_result
            
            # Применяем улучшения
            result = await self._apply_improvements(improvements, task.get('file_path'))
            
            # Обновляем результат задачи
            task_result.update(result)
            
            return task_result
            
        except Exception as e:
            logger.error(f"Ошибка при обработке задачи разработчиком: {e}")
            task_result['status'] = 'error'
            task_result['error'] = str(e)
            return task_result
        
    async def _analyze_code(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ кода для улучшения.
        
        Args:
            task: Задача с информацией о коде
            
        Returns:
            Результаты анализа
        """
        # Проверяем различные возможные ключи для имени файла
        file_path = None
        
        # Проверяем все возможные ключи, которые могут содержать путь к файлу
        for key in ['file_path', 'target_file', 'target', 'path', 'source_file']:
            if key in task and task[key] is not None:
                file_path = task[key]
                logger.info(f"Найден путь к файлу в ключе '{key}': {file_path}")
                break
        
        if not file_path:
            # Если путь к файлу не найден, возвращаем ошибку в структурированном виде
            error_message = "Путь к файлу не найден в задаче"
            logger.error(error_message)
            return {
                'status': 'error',
                'error': error_message,
                'complexity': 0,
                'test_coverage': 0,
                'code_smells': 0
            }
        
        # Проверяем, существует ли файл
        if not Path(file_path).exists():
            error_message = f"Файл не найден: {file_path}"
            logger.error(error_message)
            
            # Проверяем, возможно, путь относительный
            alternative_paths = [
                os.path.join('src', file_path),
                os.path.join('multi_agent_system', file_path),
                file_path.lstrip('/')
            ]
            
            # Проверяем альтернативные пути
            for alt_path in alternative_paths:
                if Path(alt_path).exists():
                    logger.info(f"Найден альтернативный путь: {alt_path}")
                    file_path = alt_path
                    break
            else:
                # Если файл не найден ни по одному из путей, возвращаем ошибку
                return {
                    'status': 'error',
                    'error': error_message,
                    'complexity': 0,
                    'test_coverage': 0,
                    'code_smells': 0
                }
        
        return await self.code_analyzer.analyze_file(file_path)
        
    async def _generate_improvements(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Генерация предложений по улучшению кода на основе анализа.
        
        Args:
            analysis: Результаты анализа кода
            
        Returns:
            Список предложенных улучшений
        """
        # Проверка, что analysis не None, и если None, устанавливаем пустой словарь
        if analysis is None:
            analysis = {}
        
        # Получаем метрики кода с значениями по умолчанию, если ключи отсутствуют
        metrics = analysis.get('metrics', {})
        if not isinstance(metrics, dict):
            metrics = {}
        
        # Получаем значения метрик с дефолтными значениями
        complexity = metrics.get('complexity', 0)
        if not isinstance(complexity, (int, float)):
            complexity = 0
        
        test_coverage = metrics.get('test_coverage', 0)
        if not isinstance(test_coverage, (int, float)):
            test_coverage = 0
        
        code_smells = metrics.get('code_smells', 0)
        if not isinstance(code_smells, (int, float)):
            code_smells = 0
        
        # Логируем найденные метрики
        logger.info(f"Метрики кода: complexity={complexity}, test_coverage={test_coverage}, code_smells={code_smells}")
        
        improvements = []
        
        # Предлагаем улучшения на основе метрик
        if complexity > 5:
            improvements.append({
                'type': 'refactoring',
                'description': f'Упростить код - текущая сложность: {complexity}',
                'priority': 'high' if complexity > 8 else 'medium'
            })
            
        if test_coverage < 80:
            improvements.append({
                'type': 'testing',
                'description': f'Увеличить покрытие тестами - текущее покрытие: {test_coverage}%',
                'priority': 'high' if test_coverage < 50 else 'medium'
            })
            
        if code_smells > 3:
            improvements.append({
                'type': 'code_quality',
                'description': f'Исправить проблемы с качеством кода - найдено {code_smells} code smells',
                'priority': 'high' if code_smells > 7 else 'medium'
            })
            
        logger.info(f"Сгенерировано {len(improvements)} предложений по улучшению")
        return improvements
        
    async def _apply_improvements(self, 
                               improvements: List[Dict[str, Any]], 
                               file_path: str) -> Dict[str, Any]:
        """
        Применение сгенерированных улучшений к коду.
        
        Args:
            improvements: Список улучшений для применения
            file_path: Путь к файлу
            
        Returns:
            Результаты применения улучшений
        """
        logger.info(f"Применение {len(improvements)} улучшений к файлу {file_path}")
        changed_files = []
        metrics = {'complexity': 0, 'test_coverage': 0, 'code_smells': 0}
        
        try:
            # Создаем ветку для улучшений
            branch_name = f"improvements/{Path(file_path).stem}_{int(time.time())}"
            branch_result = await self.git_manager.create_branch(branch_name)
            
            if branch_result.get('status') != 'success':
                logger.error(f"Не удалось создать ветку: {branch_result.get('error')}")
                return {
                    'status': 'error',
                    'error': f"Не удалось создать ветку: {branch_result.get('error')}",
                    'complexity': 0,
                    'metrics': metrics
                }
            
            # Применяем каждое улучшение
            for i, improvement in enumerate(improvements):
                improvement_type = improvement.get('type', 'general')
                description = improvement.get('description', 'Улучшение кода')
                
                logger.info(f"Применение улучшения {i+1}/{len(improvements)}: {description}")
                
                # Применяем изменения в зависимости от типа улучшения
                if improvement_type == 'refactoring':
                    # Выполняем рефакторинг кода
                    refactoring_result = await self._apply_refactoring(file_path, improvement)
                    if refactoring_result.get('status') == 'success':
                        changed_files.append(file_path)
                        metrics['complexity_improvement'] = refactoring_result.get('metrics', {}).get('complexity_reduction', 0)
                
                elif improvement_type == 'testing':
                    # Создаем или улучшаем тесты
                    test_file = self._get_test_file_path(file_path)
                    testing_result = await self._improve_test_coverage(file_path, test_file, improvement)
                    if testing_result.get('status') == 'success':
                        changed_files.append(test_file)
                        metrics['test_coverage_improvement'] = testing_result.get('metrics', {}).get('coverage_increase', 0)
                
                elif improvement_type == 'code_quality':
                    # Исправляем code smells
                    quality_result = await self._improve_code_quality(file_path, improvement)
                    if quality_result.get('status') == 'success':
                        changed_files.append(file_path)
                        metrics['code_smells_fixed'] = quality_result.get('metrics', {}).get('smells_fixed', 0)
                
                else:
                    # Общее улучшение
                    logger.info(f"Применение общего улучшения: {description}")
                    # Здесь могла бы быть логика для общих улучшений
                    # В данной заглушке просто добавляем комментарий
                    metrics['general_improvements'] = len(improvements)
            
            # Коммитим изменения
            if changed_files:
                commit_message = f"Улучшение кода: {', '.join([Path(f).name for f in set(changed_files)])}"
                commit_result = await self.git_manager.commit_changes(commit_message)
                
                if commit_result.get('status') != 'success':
                    logger.error(f"Не удалось закоммитить изменения: {commit_result.get('error')}")
                    return {
                        'status': 'partial_success',
                        'error': f"Изменения применены, но не закоммичены: {commit_result.get('error')}",
                        'branch': branch_name,
                        'files_changed': changed_files,
                        'metrics': metrics,
                        'complexity': metrics.get('complexity', 0)
                    }
                
                return {
                    'status': 'success',
                    'branch': branch_name,
                    'files_changed': changed_files,
                    'metrics': metrics,
                    'complexity': metrics.get('complexity', 0)
                }
            else:
                logger.warning("Не было применено ни одного улучшения")
                return {
                    'status': 'warning',
                    'message': "Не было применено ни одного улучшения",
                    'branch': branch_name,
                    'files_changed': [],
                    'metrics': metrics,
                    'complexity': metrics.get('complexity', 0)
                }
                
        except Exception as e:
            logger.error(f"Ошибка при применении улучшений: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'files_changed': changed_files,
                'metrics': metrics,
                'complexity': metrics.get('complexity', 0)
            }
            
    async def _apply_refactoring(self, file_path: str, improvement: Dict[str, Any]) -> Dict[str, Any]:
        """Заглушка для метода рефакторинга кода"""
        logger.info(f"Заглушка рефакторинга для {file_path}: {improvement.get('description')}")
        return {
            'status': 'success',
            'metrics': {
                'complexity_reduction': 2  # Симуляция уменьшения сложности
            }
        }
        
    async def _improve_test_coverage(self, source_file: str, test_file: str, improvement: Dict[str, Any]) -> Dict[str, Any]:
        """Заглушка для метода улучшения тестового покрытия"""
        logger.info(f"Заглушка улучшения тестов для {source_file} -> {test_file}: {improvement.get('description')}")
        return {
            'status': 'success',
            'metrics': {
                'coverage_increase': 15  # Симуляция увеличения покрытия на 15%
            }
        }
        
    async def _improve_code_quality(self, file_path: str, improvement: Dict[str, Any]) -> Dict[str, Any]:
        """Заглушка для метода исправления проблем с качеством кода"""
        logger.info(f"Заглушка улучшения качества для {file_path}: {improvement.get('description')}")
        return {
            'status': 'success',
            'metrics': {
                'smells_fixed': 3  # Симуляция исправления 3 code smells
            }
        }
        
    def _get_test_file_path(self, source_file: str) -> str:
        """Получает путь к тестовому файлу на основе исходного файла"""
        path = Path(source_file)
        if 'test_' in path.name:
            return str(path)  # Уже тестовый файл
            
        filename = f"test_{path.name}"
        parent = path.parent
        
        # Поиск директории с тестами
        if 'tests' in str(parent):
            return str(parent / filename)
        elif (parent / 'tests').exists():
            return str(parent / 'tests' / filename)
        else:
            # Если директория с тестами не найдена, создаем файл в той же директории
            return str(parent / filename) 