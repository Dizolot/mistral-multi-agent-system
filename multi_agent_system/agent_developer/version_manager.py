"""
Модуль управления версиями агентов.

Этот модуль обеспечивает функциональность для версионирования агентов, сохранения и загрузки
различных версий, отслеживания изменений и управления процессом внедрения улучшений.
"""

import os
import json
import logging
import datetime
import uuid
import shutil
import re
import difflib
from typing import Dict, List, Any, Optional, Union, Tuple

from multi_agent_system.agents.base_agent import BaseAgent
from multi_agent_system.agent_developer.agent_tester import AgentTester

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VersionManager:
    """
    Менеджер версий для агентов.
    
    Этот класс отвечает за:
    1. Сохранение версий агентов
    2. Загрузку версий агентов
    3. Отслеживание истории изменений
    4. Управление процессом внедрения улучшений
    5. Создание резервных копий перед обновлением
    """
    
    def __init__(
        self,
        versions_dir: str = "multi_agent_system/agents/versions",
        backups_dir: str = "multi_agent_system/agents/backups",
        agent_tester: Optional[AgentTester] = None
    ):
        """
        Инициализирует менеджер версий.
        
        Args:
            versions_dir: Директория для хранения версий агентов
            backups_dir: Директория для хранения резервных копий
            agent_tester: Тестировщик агентов для проверки улучшений
        """
        self.versions_dir = versions_dir
        self.backups_dir = backups_dir
        self.agent_tester = agent_tester or AgentTester()
        
        # Создаем директории, если они не существуют
        os.makedirs(self.versions_dir, exist_ok=True)
        os.makedirs(self.backups_dir, exist_ok=True)
        
        logger.info(f"Менеджер версий инициализирован. Директория версий: {self.versions_dir}")
    
    def save_agent_version(
        self, 
        agent: Union[BaseAgent, Dict[str, Any]],
        version_name: Optional[str] = None,
        version_notes: Optional[str] = None,
        is_production: bool = False
    ) -> str:
        """
        Сохраняет версию агента.
        
        Args:
            agent: Агент или его конфигурация
            version_name: Название версии (по умолчанию генерируется автоматически)
            version_notes: Примечания к версии
            is_production: Флаг, указывающий, что версия является продакшн-версией
            
        Returns:
            Идентификатор сохраненной версии
        """
        # Если передан агент, получаем его конфигурацию
        if isinstance(agent, BaseAgent):
            agent_config = agent.get_config()
            agent_name = agent.name
        else:
            agent_config = agent
            agent_name = agent.get("name", "unknown_agent")
        
        # Генерируем название версии, если не указано
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        version_id = version_name or f"{agent_name}_v_{timestamp}"
        
        # Создаем директорию для агента, если она не существует
        agent_dir = os.path.join(self.versions_dir, agent_name)
        os.makedirs(agent_dir, exist_ok=True)
        
        # Создаем метаданные версии
        version_metadata = {
            "version_id": version_id,
            "agent_name": agent_name,
            "created_at": datetime.datetime.now().isoformat(),
            "is_production": is_production,
            "version_notes": version_notes or "Версия создана без примечаний",
            "created_by": "version_manager"
        }
        
        # Сохраняем версию агента и метаданные
        version_path = os.path.join(agent_dir, f"{version_id}.json")
        with open(version_path, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": version_metadata,
                "config": agent_config
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Сохранена версия агента {agent_name}: {version_id}")
        
        # Если это продакшн-версия, обновляем ссылку на текущую продакшн-версию
        if is_production:
            self.set_production_version(agent_name, version_id)
        
        return version_id
    
    def get_agent_versions(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Получает список всех версий агента.
        
        Args:
            agent_name: Имя агента
            
        Returns:
            Список метаданных версий агента, отсортированный по дате создания (новые вначале)
        """
        agent_dir = os.path.join(self.versions_dir, agent_name)
        
        if not os.path.exists(agent_dir):
            logger.warning(f"Директория версий агента {agent_name} не найдена")
            return []
        
        versions = []
        for filename in os.listdir(agent_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(agent_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    versions.append(data["metadata"])
                except Exception as e:
                    logger.error(f"Ошибка при чтении версии {filename}: {str(e)}")
        
        # Сортируем версии по дате создания (новые вначале)
        versions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return versions
    
    def load_agent_version(self, agent_name: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Загружает указанную версию агента.
        
        Args:
            agent_name: Имя агента
            version_id: Идентификатор версии (если None, загружается последняя продакшн-версия)
            
        Returns:
            Конфигурация агента
            
        Raises:
            FileNotFoundError: Если версия не найдена
        """
        agent_dir = os.path.join(self.versions_dir, agent_name)
        
        # Если версия не указана, пытаемся загрузить текущую продакшн-версию
        if version_id is None:
            production_version = self.get_production_version(agent_name)
            if production_version:
                version_id = production_version
            else:
                # Если продакшн-версия не найдена, пытаемся загрузить самую новую версию
                versions = self.get_agent_versions(agent_name)
                if versions:
                    version_id = versions[0]["version_id"]
                else:
                    raise FileNotFoundError(f"Версии агента {agent_name} не найдены")
        
        # Загружаем указанную версию
        version_path = os.path.join(agent_dir, f"{version_id}.json")
        if not os.path.exists(version_path):
            raise FileNotFoundError(f"Версия {version_id} агента {agent_name} не найдена")
        
        with open(version_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Загружена версия {version_id} агента {agent_name}")
        
        return data["config"]
    
    def set_production_version(self, agent_name: str, version_id: str) -> bool:
        """
        Устанавливает указанную версию как текущую продакшн-версию.
        
        Args:
            agent_name: Имя агента
            version_id: Идентификатор версии
            
        Returns:
            True, если версия успешно установлена как продакшн, False в противном случае
        """
        agent_dir = os.path.join(self.versions_dir, agent_name)
        production_marker_path = os.path.join(agent_dir, "production_version.txt")
        
        # Проверяем, существует ли указанная версия
        version_path = os.path.join(agent_dir, f"{version_id}.json")
        if not os.path.exists(version_path):
            logger.error(f"Версия {version_id} агента {agent_name} не найдена")
            return False
        
        # Обновляем ссылку на продакшн-версию
        with open(production_marker_path, 'w', encoding='utf-8') as f:
            f.write(version_id)
        
        # Обновляем метаданные версии
        try:
            with open(version_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data["metadata"]["is_production"] = True
            
            with open(version_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка при обновлении метаданных версии: {str(e)}")
        
        logger.info(f"Версия {version_id} установлена как продакшн для агента {agent_name}")
        
        return True
    
    def get_production_version(self, agent_name: str) -> Optional[str]:
        """
        Получает текущую продакшн-версию агента.
        
        Args:
            agent_name: Имя агента
            
        Returns:
            Идентификатор продакшн-версии или None, если она не установлена
        """
        agent_dir = os.path.join(self.versions_dir, agent_name)
        production_marker_path = os.path.join(agent_dir, "production_version.txt")
        
        if not os.path.exists(production_marker_path):
            logger.warning(f"Продакшн-версия для агента {agent_name} не установлена")
            return None
        
        with open(production_marker_path, 'r', encoding='utf-8') as f:
            version_id = f.read().strip()
        
        return version_id
    
    def create_backup(self, agent_name: str, version_id: Optional[str] = None) -> str:
        """
        Создает резервную копию указанной версии агента.
        
        Args:
            agent_name: Имя агента
            version_id: Идентификатор версии (если None, создается копия текущей продакшн-версии)
            
        Returns:
            Путь к созданной резервной копии
        """
        # Загружаем указанную версию
        agent_config = self.load_agent_version(agent_name, version_id)
        
        # Создаем директорию для резервных копий агента
        backup_dir = os.path.join(self.backups_dir, agent_name)
        os.makedirs(backup_dir, exist_ok=True)
        
        # Генерируем имя резервной копии
        backup_id = f"backup_{agent_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join(backup_dir, f"{backup_id}.json")
        
        # Сохраняем резервную копию
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "backup_id": backup_id,
                    "agent_name": agent_name,
                    "original_version": version_id,
                    "created_at": datetime.datetime.now().isoformat()
                },
                "config": agent_config
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Создана резервная копия {backup_id} для агента {agent_name}")
        
        return backup_path
    
    def restore_from_backup(self, backup_path: str, set_as_production: bool = False) -> Dict[str, Any]:
        """
        Восстанавливает агента из резервной копии.
        
        Args:
            backup_path: Путь к резервной копии
            set_as_production: Установить восстановленную версию как продакшн
            
        Returns:
            Конфигурация восстановленного агента
        """
        # Загружаем резервную копию
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        agent_name = backup_data["metadata"]["agent_name"]
        agent_config = backup_data["config"]
        
        # Создаем новую версию из резервной копии
        version_id = self.save_agent_version(
            agent=agent_config,
            version_name=f"{agent_name}_restored_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            version_notes=f"Восстановлено из резервной копии {os.path.basename(backup_path)}",
            is_production=set_as_production
        )
        
        logger.info(f"Агент {agent_name} восстановлен из резервной копии и сохранен как версия {version_id}")
        
        return agent_config
    
    def compare_versions(self, agent_name: str, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        Сравнивает две версии агента и возвращает их различия.
        
        Args:
            agent_name: Имя агента
            version_id1: Идентификатор первой версии
            version_id2: Идентификатор второй версии
            
        Returns:
            Словарь с результатами сравнения
        """
        # Загружаем обе версии
        config1 = self.load_agent_version(agent_name, version_id1)
        config2 = self.load_agent_version(agent_name, version_id2)
        
        # Сравниваем системные промпты
        prompt1 = config1.get("system_prompt", "")
        prompt2 = config2.get("system_prompt", "")
        
        prompt_diff = list(difflib.unified_diff(
            prompt1.splitlines(),
            prompt2.splitlines(),
            lineterm='',
            n=3
        ))
        
        # Сравниваем другие поля конфигурации
        changed_fields = []
        for key in set(config1.keys()) | set(config2.keys()):
            if key == "system_prompt":
                continue
            
            if key not in config1:
                changed_fields.append({
                    "field": key,
                    "change_type": "added",
                    "old_value": None,
                    "new_value": config2[key]
                })
            elif key not in config2:
                changed_fields.append({
                    "field": key,
                    "change_type": "removed",
                    "old_value": config1[key],
                    "new_value": None
                })
            elif config1[key] != config2[key]:
                changed_fields.append({
                    "field": key,
                    "change_type": "modified",
                    "old_value": config1[key],
                    "new_value": config2[key]
                })
        
        return {
            "agent_name": agent_name,
            "version1": version_id1,
            "version2": version_id2,
            "prompt_diff": prompt_diff,
            "changed_fields": changed_fields,
            "are_identical": len(prompt_diff) == 0 and len(changed_fields) == 0
        }
    
    def evaluate_improvement(
        self, 
        agent_name: str, 
        original_version_id: str, 
        improved_version_id: str, 
        test_dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Оценивает улучшение агента, сравнивая производительность двух версий.
        
        Args:
            agent_name: Имя агента
            original_version_id: Идентификатор исходной версии
            improved_version_id: Идентификатор улучшенной версии
            test_dataset_id: Идентификатор тестового набора данных (если None, будет использован наиболее подходящий)
            
        Returns:
            Результаты сравнения версий
        """
        # Загружаем обе версии
        original_config = self.load_agent_version(agent_name, original_version_id)
        improved_config = self.load_agent_version(agent_name, improved_version_id)
        
        # Получаем системные промпты
        original_system_prompt = original_config.get("system_prompt", "")
        improved_system_prompt = improved_config.get("system_prompt", "")
        
        # Если тестовый набор не указан, используем существующий или создаем новый
        if not test_dataset_id:
            # Получаем список тестовых наборов для агента
            datasets = self.agent_tester.get_test_datasets(agent_name)
            
            if datasets:
                test_dataset_id = datasets[0]  # Используем первый доступный набор
                logger.info(f"Используем существующий тестовый набор: {test_dataset_id}")
            else:
                # Создаем новый тестовый набор на основе описания агента
                test_dataset_id = self.agent_tester.generate_benchmark_questions(
                    agent_name=agent_name,
                    agent_description=original_config.get("description", ""),
                    categories=["базовые", "сложные", "edge_cases"],
                    questions_per_category=3
                )
                logger.info(f"Создан новый тестовый набор: {test_dataset_id}")
        
        # Проводим сравнение версий
        comparison_results = self.agent_tester.compare_agents(
            original_agent_name=f"{agent_name}_original",
            original_system_prompt=original_system_prompt,
            improved_agent_name=f"{agent_name}_improved",
            improved_system_prompt=improved_system_prompt,
            dataset_id=test_dataset_id
        )
        
        # Формируем отчет об улучшении
        improvement_report = {
            "agent_name": agent_name,
            "original_version": original_version_id,
            "improved_version": improved_version_id,
            "test_dataset_id": test_dataset_id,
            "evaluation_date": datetime.datetime.now().isoformat(),
            "better_count": comparison_results.get("better_count", 0),
            "worse_count": comparison_results.get("worse_count", 0),
            "equal_count": comparison_results.get("equal_count", 0),
            "improvement_rate": comparison_results.get("improvement_rate", 0),
            "is_improvement": comparison_results.get("recommendation") == "accept",
            "details": comparison_results
        }
        
        # Сохраняем отчет
        report_dir = os.path.join(self.versions_dir, agent_name, "improvement_reports")
        os.makedirs(report_dir, exist_ok=True)
        
        report_path = os.path.join(
            report_dir, 
            f"improvement_{original_version_id}_to_{improved_version_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(improvement_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Оценка улучшения агента {agent_name} завершена. Рекомендация: {comparison_results.get('recommendation', 'unknown')}")
        
        return improvement_report
    
    def deploy_improvement(self, agent_name: str, version_id: str, force: bool = False) -> bool:
        """
        Внедряет улучшение агента, устанавливая указанную версию как продакшн.
        
        Args:
            agent_name: Имя агента
            version_id: Идентификатор версии для внедрения
            force: Принудительное внедрение без дополнительной проверки
            
        Returns:
            True, если улучшение успешно внедрено, False в противном случае
        """
        # Получаем текущую продакшн-версию
        current_production_id = self.get_production_version(agent_name)
        
        # Если версия уже является продакшн-версией, ничего не делаем
        if current_production_id == version_id:
            logger.info(f"Версия {version_id} уже является продакшн-версией для агента {agent_name}")
            return True
        
        # Если не принудительное внедрение, проводим оценку улучшения
        if not force and current_production_id:
            evaluation_results = self.evaluate_improvement(
                agent_name=agent_name,
                original_version_id=current_production_id,
                improved_version_id=version_id
            )
            
            # Если оценка показала, что это не улучшение, возвращаем False
            if not evaluation_results.get("is_improvement", False):
                logger.warning(f"Версия {version_id} не показала улучшений по сравнению с текущей продакшн-версией {current_production_id}")
                return False
        
        # Создаем резервную копию текущей продакшн-версии, если она существует
        if current_production_id:
            self.create_backup(agent_name, current_production_id)
        
        # Устанавливаем новую версию как продакшн
        success = self.set_production_version(agent_name, version_id)
        
        if success:
            logger.info(f"Версия {version_id} успешно внедрена как продакшн для агента {agent_name}")
        else:
            logger.error(f"Не удалось внедрить версию {version_id} для агента {agent_name}")
        
        return success
    
    def get_agent_history(self, agent_name: str) -> Dict[str, Any]:
        """
        Получает историю версий агента с метриками и статистикой.
        
        Args:
            agent_name: Имя агента
            
        Returns:
            Словарь с историей версий агента
        """
        versions = self.get_agent_versions(agent_name)
        
        # Получаем текущую продакшн-версию
        current_production_id = self.get_production_version(agent_name)
        
        # Формируем историю версий
        history = {
            "agent_name": agent_name,
            "total_versions": len(versions),
            "current_production": current_production_id,
            "first_version_date": versions[-1]["created_at"] if versions else None,
            "latest_version_date": versions[0]["created_at"] if versions else None,
            "versions": versions
        }
        
        return history
    
    def get_all_agents(self) -> List[str]:
        """
        Получает список всех агентов в системе.
        
        Returns:
            Список имен агентов
        """
        agents = []
        
        if os.path.exists(self.versions_dir):
            for item in os.listdir(self.versions_dir):
                agent_dir = os.path.join(self.versions_dir, item)
                if os.path.isdir(agent_dir) and any(f.endswith('.json') for f in os.listdir(agent_dir)):
                    agents.append(item)
        
        return agents
    
    def init_agent_versioning(self, agent: Union[BaseAgent, Dict[str, Any]]) -> str:
        """
        Инициализирует версионирование агента, создавая первую версию.
        
        Args:
            agent: Агент или его конфигурация
            
        Returns:
            Идентификатор созданной версии
        """
        # Если передан агент, получаем его конфигурацию и имя
        if isinstance(agent, BaseAgent):
            agent_config = agent.get_config()
            agent_name = agent.name
        else:
            agent_config = agent
            agent_name = agent.get("name", "unknown_agent")
        
        # Создаем первую версию агента
        version_id = self.save_agent_version(
            agent=agent_config,
            version_name=f"{agent_name}_v1",
            version_notes="Начальная версия агента",
            is_production=True
        )
        
        logger.info(f"Инициализировано версионирование агента {agent_name}, создана версия {version_id}")
        
        return version_id
    
    def rollback_to_version(self, agent_name: str, version_id: str) -> bool:
        """
        Откатывает агента к указанной версии.
        
        Args:
            agent_name: Имя агента
            version_id: Идентификатор версии, к которой нужно откатиться
            
        Returns:
            True, если откат успешен, False в противном случае
        """
        # Проверяем существование версии
        agent_dir = os.path.join(self.versions_dir, agent_name)
        version_path = os.path.join(agent_dir, f"{version_id}.json")
        
        if not os.path.exists(version_path):
            logger.error(f"Версия {version_id} агента {agent_name} не найдена")
            return False
        
        # Создаем резервную копию текущей продакшн-версии
        current_production_id = self.get_production_version(agent_name)
        if current_production_id:
            self.create_backup(agent_name, current_production_id)
        
        # Устанавливаем указанную версию как продакшн
        success = self.set_production_version(agent_name, version_id)
        
        if success:
            logger.info(f"Выполнен откат агента {agent_name} к версии {version_id}")
        else:
            logger.error(f"Не удалось выполнить откат агента {agent_name} к версии {version_id}")
        
        return success


# Если файл запущен как скрипт, выполняем демонстрационный пример
if __name__ == "__main__":
    from multi_agent_system.agents.agent_configs import GENERAL_AGENT_CONFIG
    from multi_agent_system.agents.base_agent import BaseAgent, AgentFactory
    
    # Создаем менеджер версий
    version_manager = VersionManager()
    
    # Создаем агента из конфигурации
    agent = AgentFactory.create_agent(GENERAL_AGENT_CONFIG)
    
    # Инициализируем версионирование агента
    version_id = version_manager.init_agent_versioning(agent)
    
    print(f"Инициализировано версионирование агента {agent.name}, создана версия {version_id}")
    
    # Печатаем список всех агентов
    agents = version_manager.get_all_agents()
    print(f"Список всех агентов в системе: {agents}") 