#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для запуска всех тестов производительности системы памяти.

Запускает все тесты производительности системы памяти и агрегирует результаты.
Результаты сохраняются в директории results.
"""

import os
import sys
import time
import argparse
import subprocess
import json
import glob
from datetime import datetime

# Добавляем корневую директорию проекта в PATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))


def run_test(test_path, verbose=False):
    """Запускает тест и возвращает результат выполнения."""
    cmd = ['python', test_path]
    if verbose:
        cmd.append('-v')
    
    print(f"Запуск теста: {os.path.basename(test_path)}")
    start_time = time.time()
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    success = result.returncode == 0
    status = "УСПЕШНО" if success else "ОШИБКА"
    
    print(f"Статус: {status}. Время выполнения: {execution_time:.2f} с")
    
    if verbose:
        print("\nВывод теста:")
        print(result.stdout)
        
        if result.stderr:
            print("\nОшибки:")
            print(result.stderr)
    
    return {
        "test_name": os.path.basename(test_path),
        "status": status,
        "success": success,
        "execution_time": execution_time,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "return_code": result.returncode
    }


def collect_test_files():
    """Собирает все файлы тестов производительности."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Собираем тесты из текущей директории
    test_files = glob.glob(os.path.join(current_dir, "test_*.py"))
    
    # Собираем тесты из поддиректорий (benchmarks)
    benchmarks_dir = os.path.join(current_dir, "benchmarks")
    if os.path.exists(benchmarks_dir):
        benchmark_files = glob.glob(os.path.join(benchmarks_dir, "test_*.py"))
        test_files.extend(benchmark_files)
    
    return test_files


def run_all_tests(verbose=False):
    """Запускает все тесты производительности и собирает результаты."""
    test_files = collect_test_files()
    
    if not test_files:
        print("Не найдено тестов производительности.")
        return []
    
    print(f"Найдено {len(test_files)} тестов производительности.")
    
    results = []
    for test_file in test_files:
        results.append(run_test(test_file, verbose))
    
    return results


def save_summary(results, results_dir="results"):
    """Сохраняет сводные результаты тестов."""
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = os.path.join(results_dir, f"performance_summary_{timestamp}.json")
    
    summary = {
        "timestamp": timestamp,
        "total_tests": len(results),
        "successful_tests": sum(1 for r in results if r["success"]),
        "failed_tests": sum(1 for r in results if not r["success"]),
        "total_execution_time": sum(r["execution_time"] for r in results),
        "results": results
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nСводные результаты:")
    print(f"Всего тестов: {summary['total_tests']}")
    print(f"Успешно: {summary['successful_tests']}")
    print(f"С ошибками: {summary['failed_tests']}")
    print(f"Общее время выполнения: {summary['total_execution_time']:.2f} с")
    print(f"Отчет сохранен в: {summary_path}")
    
    return summary_path


def main():
    """Основная функция скрипта."""
    parser = argparse.ArgumentParser(description="Запуск тестов производительности системы памяти")
    parser.add_argument("-v", "--verbose", action="store_true", help="Показывать подробный вывод тестов")
    parser.add_argument("-o", "--output", default="results", help="Директория для сохранения результатов")
    
    args = parser.parse_args()
    
    print("=== Запуск тестов производительности системы памяти ===")
    start_time = time.time()
    
    results = run_all_tests(args.verbose)
    summary_path = save_summary(results, args.output)
    
    end_time = time.time()
    print(f"\nОбщее время запуска: {end_time - start_time:.2f} с")
    
    # Возвращаем код ошибки, если были неудачные тесты
    if any(not r["success"] for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main()) 