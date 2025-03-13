#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для валидации конфигурации системы

Этот скрипт:
1. Проверяет соответствие настроек в .env и фактических файлах конфигурации
2. Тестирует доступность всех сервисов на указанных портах
3. Проверяет соответствие моделей в конфигурации и на сервере
4. Генерирует отчет о найденных проблемах и несоответствиях
"""

import os
import sys
import json
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv
import re
import subprocess

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Создаем директорию для логов, если она не существует
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "config_validator.log")),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('config_validator')

# Загружаем переменные окружения
load_dotenv()

def validate_env_config():
    """Проверяет настройки в .env файле"""
    logger.info("Проверка настроек в .env файле")
    
    issues = []
    
    # Проверяем обязательные переменные
    required_vars = [
        "TELEGRAM_TOKEN",
        "MISTRAL_API_URL"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Отсутствует обязательная переменная: {var}")
    
    # Проверяем правильность URL API Mistral
    mistral_api_url = os.getenv("MISTRAL_API_URL", "")
    if "139.59.241.176:8080" not in mistral_api_url:
        issues.append(f"Некорректный URL Mistral API: {mistral_api_url}. Ожидается адрес с портом 8080")
    
    # Проверяем корректность модели по умолчанию
    default_model = os.getenv("DEFAULT_MODEL", "")
    expected_model = "TheBloke/Mistral-7B-Instruct-v0.3-GPTQ"
    if default_model != expected_model:
        issues.append(f"Некорректная модель по умолчанию: {default_model}. Ожидается: {expected_model}")
    
    return issues

def validate_config_files():
    """Проверяет настройки в файлах конфигурации"""
    logger.info("Проверка настроек в файлах конфигурации")
    
    issues = []
    
    # Файлы для проверки
    files_to_check = [
        "telegram_bot/config.py",
        "src/model_service/model_adapter/mistral_adapter.py",
        "telegram_bot/model_service_client.py",
        "src/utils/monitoring_script.py"
    ]
    
    for file_path in files_to_check:
        full_path = os.path.join(project_root, file_path)
        try:
            if not os.path.exists(full_path):
                issues.append(f"Файл не найден: {file_path}")
                continue
                
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Проверяем URL Mistral API
                if "139.59.241.176:8000" in content:
                    issues.append(f"Найден некорректный порт 8000 в файле {file_path}")
                
                # Проверяем модель
                model_patterns = [
                    r"model_name\s*=\s*['\"](?!TheBloke\/Mistral-7B-Instruct-v0\.3-GPTQ)[^'\"]+['\"]",
                    r"DEFAULT_MODEL\s*=\s*['\"](?!TheBloke\/Mistral-7B-Instruct-v0\.3-GPTQ)[^'\"]+['\"]"
                ]
                
                for pattern in model_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        issues.append(f"Найдена некорректная модель в файле {file_path}: {matches[0]}")
                        
        except Exception as e:
            issues.append(f"Ошибка при проверке файла {file_path}: {str(e)}")
    
    return issues

def validate_services_availability():
    """Проверяет доступность сервисов"""
    logger.info("Проверка доступности сервисов")
    
    issues = []
    
    # Проверяем Mistral API
    mistral_api_url = os.getenv("MISTRAL_API_URL", "http://139.59.241.176:8080")
    health_endpoint = f"{mistral_api_url}/health"
    
    try:
        response = requests.get(health_endpoint, timeout=10)
        if response.status_code != 200:
            issues.append(f"Сервер Mistral API недоступен. Код статуса: {response.status_code}")
    except Exception as e:
        issues.append(f"Ошибка при проверке доступности Mistral API: {str(e)}")
    
    # Проверяем фактический порт на сервере
    try:
        result = subprocess.run(
            "ssh root@139.59.241.176 \"systemctl status llama-server.service | grep port\"",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            output = result.stdout
            
            # Ищем информацию о порте
            port_match = re.search(r"--port\s+(\d+)", output)
            if port_match and port_match.group(1) != "8080":
                issues.append(f"Порт сервера llama.cpp на сервере ({port_match.group(1)}) не соответствует настройкам (8080)")
    except Exception as e:
        issues.append(f"Не удалось проверить порт сервера llama.cpp: {str(e)}")
    
    return issues

def validate_models():
    """Проверяет доступность моделей"""
    logger.info("Проверка моделей на сервере")
    
    issues = []
    
    # Проверяем доступные модели через API
    mistral_api_url = os.getenv("MISTRAL_API_URL", "http://139.59.241.176:8080")
    models_endpoint = f"{mistral_api_url}/v1/models"
    
    try:
        response = requests.get(models_endpoint, timeout=10)
        if response.status_code == 200:
            models_data = response.json()
            
            # Ищем нашу модель
            model_found = False
            for model in models_data.get("data", []):
                if "Mistral-7B-Instruct-v0.3" in model.get("id", ""):
                    model_found = True
                    break
            
            if not model_found:
                issues.append("Модель Mistral-7B-Instruct-v0.3 не найдена в списке доступных моделей")
        else:
            issues.append(f"Не удалось получить список моделей. Код статуса: {response.status_code}")
    except Exception as e:
        issues.append(f"Ошибка при проверке доступных моделей: {str(e)}")
    
    return issues

def run_validation():
    """Основная функция для запуска проверки"""
    logger.info("Запуск проверки конфигурации системы")
    
    all_issues = []
    
    # Проверка .env файла
    env_issues = validate_env_config()
    all_issues.extend(env_issues)
    
    # Проверка файлов конфигурации
    config_issues = validate_config_files()
    all_issues.extend(config_issues)
    
    # Проверка доступности сервисов
    service_issues = validate_services_availability()
    all_issues.extend(service_issues)
    
    # Проверка моделей
    model_issues = validate_models()
    all_issues.extend(model_issues)
    
    # Выводим результаты
    if all_issues:
        logger.error(f"Найдены проблемы в конфигурации ({len(all_issues)}):")
        for i, issue in enumerate(all_issues):
            logger.error(f"{i+1}. {issue}")
            
        logger.error("Необходимо устранить найденные проблемы перед запуском системы!")
        return False
    else:
        logger.info("Проверка конфигурации завершена успешно. Проблем не обнаружено.")
        return True

if __name__ == "__main__":
    try:
        success = run_validation()
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.critical(f"Критическая ошибка при проверке конфигурации: {e}")
        sys.exit(1) 