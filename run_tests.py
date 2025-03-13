#!/usr/bin/env python
"""
Скрипт для запуска всех тестов системы.
"""

import asyncio
import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Создаем директорию для логов
os.makedirs('logs', exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_run.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_test_module(module_path, verbose=True):
    """
    Запуск тестов из указанного модуля
    
    Args:
        module_path: Путь к модулю с тестами
        verbose: Флаг вывода детальной информации
    
    Returns:
        bool: True, если тесты успешно пройдены, иначе False
    """
    try:
        logger.info(f"Запуск тестов из модуля: {module_path}")
        
        cmd = [sys.executable, "-m", "pytest", module_path]
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Тесты в модуле {module_path} успешно пройдены")
            return True
        else:
            logger.error(f"Тесты в модуле {module_path} завершились с ошибками:")
            logger.error(result.stderr)
            return False
    except Exception as e:
        logger.error(f"Ошибка при запуске тестов из модуля {module_path}: {str(e)}")
        return False

def run_all_tests(test_type=None, verbose=True):
    """
    Запуск всех тестов или тестов указанного типа
    
    Args:
        test_type: Тип тестов (unit, integration, functional, performance)
        verbose: Флаг вывода детальной информации
    
    Returns:
        dict: Результаты выполнения тестов по категориям
    """
    test_root = Path("tests")
    results = {
        "unit": None,
        "integration": None,
        "functional": None,
        "performance": None,
        "root": None
    }
    
    # Запуск тестов из корневой директории тестов
    if test_type is None or test_type == "root":
        root_tests = [str(f) for f in test_root.glob("*.py") if f.is_file() and f.name.startswith("test_")]
        root_success = all(run_test_module(test, verbose) for test in root_tests)
        results["root"] = root_success
        logger.info(f"Тесты из корневой директории {'успешно пройдены' if root_success else 'завершились с ошибками'}")
    
    # Запуск юнит-тестов
    if test_type is None or test_type == "unit":
        unit_test_dir = test_root / "unit"
        if unit_test_dir.exists():
            unit_success = run_test_module(str(unit_test_dir), verbose)
            results["unit"] = unit_success
            logger.info(f"Юнит-тесты {'успешно пройдены' if unit_success else 'завершились с ошибками'}")
    
    # Запуск интеграционных тестов
    if test_type is None or test_type == "integration":
        integration_test_dir = test_root / "integration"
        if integration_test_dir.exists():
            integration_success = run_test_module(str(integration_test_dir), verbose)
            results["integration"] = integration_success
            logger.info(f"Интеграционные тесты {'успешно пройдены' if integration_success else 'завершились с ошибками'}")
    
    # Запуск функциональных тестов
    if test_type is None or test_type == "functional":
        functional_test_dir = test_root / "functional"
        if functional_test_dir.exists():
            functional_success = run_test_module(str(functional_test_dir), verbose)
            results["functional"] = functional_success
            logger.info(f"Функциональные тесты {'успешно пройдены' if functional_success else 'завершились с ошибками'}")
    
    # Запуск тестов производительности
    if test_type is None or test_type == "performance":
        performance_test_dir = test_root / "performance"
        if performance_test_dir.exists():
            performance_success = run_test_module(str(performance_test_dir), verbose)
            results["performance"] = performance_success
            logger.info(f"Тесты производительности {'успешно пройдены' if performance_success else 'завершились с ошибками'}")
    
    return results

def display_test_summary(results):
    """
    Вывод сводки результатов тестирования
    
    Args:
        results: Словарь с результатами тестов по категориям
    """
    print("\n=== Сводка результатов тестирования ===")
    
    all_success = True
    for test_type, result in results.items():
        if result is not None:
            status = "УСПЕШНО" if result else "ОШИБКА"
            if not result:
                all_success = False
            print(f"{test_type.upper()}: {status}")
    
    overall = "УСПЕШНО" if all_success else "ЕСТЬ ОШИБКИ"
    print(f"\nОБЩИЙ РЕЗУЛЬТАТ: {overall}")
    print("=======================================")

async def run_telegram_bot_test():
    """
    Асинхронный запуск тестов Telegram-бота
    """
    try:
        logger.info("Запуск тестов Telegram-бота")
        from tests.test_bot import main as bot_test_main
        await bot_test_main()
        logger.info("Тесты Telegram-бота успешно пройдены")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске тестов Telegram-бота: {str(e)}")
        return False

async def run_memory_integration_test():
    """
    Асинхронный запуск тестов интеграции с системой памяти
    """
    try:
        logger.info("Запуск тестов интеграции с системой памяти")
        from tests.memory_integration_test import run_tests as memory_test_main
        result = await memory_test_main()
        logger.info("Тесты интеграции с системой памяти успешно пройдены" if result else "Тесты интеграции с системой памяти завершились с ошибками")
        return result
    except Exception as e:
        logger.error(f"Ошибка при запуске тестов интеграции с системой памяти: {str(e)}")
        return False

async def run_model_service_test():
    """
    Асинхронный запуск тестов сервиса моделей
    """
    try:
        logger.info("Запуск тестов сервиса моделей")
        # Импортируем тесты напрямую
        from tests.unit.test_model_service import run_async_tests as model_test_main
        await model_test_main()
        logger.info("Тесты сервиса моделей успешно пройдены")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске тестов сервиса моделей: {str(e)}")
        return False

async def run_special_tests():
    """
    Запуск специальных асинхронных тестов, не включенных в pytest
    """
    results = {
        "telegram_bot": await run_telegram_bot_test(),
        "memory_integration": await run_memory_integration_test(),
        "model_service": await run_model_service_test()
    }
    
    all_success = all(results.values())
    
    print("\n=== Сводка специальных тестов ===")
    for test_name, result in results.items():
        status = "УСПЕШНО" if result else "ОШИБКА"
        print(f"{test_name.upper()}: {status}")
    
    overall = "УСПЕШНО" if all_success else "ЕСТЬ ОШИБКИ"
    print(f"\nОБЩИЙ РЕЗУЛЬТАТ СПЕЦИАЛЬНЫХ ТЕСТОВ: {overall}")
    print("=======================================")
    
    return all_success

def main():
    """
    Основная функция для запуска тестов
    """
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description="Запуск тестов мульти-агентной системы")
    parser.add_argument("--type", choices=["unit", "integration", "functional", "performance", "special", "all"],
                      default="all", help="Тип тестов для запуска")
    parser.add_argument("--verbose", "-v", action="store_true", default=True,
                      help="Выводить подробную информацию о тестах")
    args = parser.parse_args()
    
    logger.info(f"Запуск тестов типа: {args.type}")
    
    all_success = True
    
    # Запускаем тесты на основе pytest
    if args.type in ["unit", "integration", "functional", "performance", "all"]:
        test_type = None if args.type == "all" else args.type
        results = run_all_tests(test_type, args.verbose)
        display_test_summary(results)
        all_success = all_success and all(r for r in results.values() if r is not None)
    
    # Запускаем специальные тесты, не использующие pytest
    if args.type in ["special", "all"]:
        special_success = asyncio.run(run_special_tests())
        all_success = all_success and special_success
    
    # Возвращаем успешность выполнения тестов
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main()) 