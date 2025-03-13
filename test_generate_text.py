#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для проверки работы метода generate_text в MistralClient
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_generate_text')

# Загружаем переменные окружения из .env файла
load_dotenv()

# Импортируем MistralClient
from telegram_bot.mistral_client import MistralClient

def main():
    # Получаем базовый URL из переменных окружения или используем значение по умолчанию
    base_url = os.getenv('MISTRAL_API_URL', 'http://139.59.241.176:8080')
    logger.info(f"Используем Mistral API URL: {base_url}")
    
    # Создаем экземпляр клиента
    client = MistralClient(base_url=base_url)
    logger.info("Клиент Mistral создан")
    
    # Тестовый запрос с использованием метода generate_text
    context = [
        {"role": "system", "content": "Ты - полезный ассистент, который отвечает кратко и по существу."},
        {"role": "user", "content": "Привет! Расскажи, что ты умеешь?"}
    ]
    
    logger.info("Отправка запроса к модели...")
    
    start_time = time.time()
    response = client.generate_text(context=context, temperature=0.7, max_tokens=500)
    end_time = time.time()
    
    logger.info(f"Ответ получен за {end_time - start_time:.2f} секунд")
    logger.info(f"Ответ модели: {response}")
    
    # Тестовый запрос с обработкой ошибок
    try:
        # Намеренно вызываем ошибку, передавая неправильный контекст
        invalid_context = "Неправильный контекст"
        logger.info("Отправка неправильного запроса для проверки обработки ошибок...")
        response = client.generate_text(context=invalid_context)
        logger.info(f"Результат: {response}")
    except Exception as e:
        logger.error(f"Произошла ошибка (как и ожидалось): {str(e)}")
    
    logger.info("Тестирование завершено")

if __name__ == "__main__":
    main() 