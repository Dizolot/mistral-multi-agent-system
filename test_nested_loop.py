#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки работы вложенных циклов событий
"""

import asyncio
import logging
from telegram_bot.mistral_client import MistralClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_nested_loop')

async def main_async():
    """Основная асинхронная функция для теста"""
    base_url = 'http://139.59.241.176:8080'
    client = MistralClient(base_url=base_url)
    
    logger.info("Создан клиент Mistral")
    
    # Тестовый запрос внутри асинхронной функции (цикл уже запущен)
    context = [
        {"role": "system", "content": "Ты - полезный ассистент, который отвечает кратко и по существу."},
        {"role": "user", "content": "Привет! Дай короткий ответ о том, как ты себя чувствуешь?"}
    ]
    
    logger.info("Делаем синхронный вызов generate_text внутри асинхронной функции...")
    response = client.generate_text(context=context, temperature=0.7, max_tokens=300)
    logger.info(f"Ответ получен: {response}")
    
    # Тестовый запрос с прямым вызовом асинхронного метода
    logger.info("Делаем прямой асинхронный вызов generate_chat_response...")
    response_async = await client.generate_chat_response(
        messages=context,
        temperature=0.7,
        max_tokens=300
    )
    logger.info(f"Ответ получен через await: {response_async}")
    
    return "Тест завершен успешно"

if __name__ == '__main__':
    logger.info("Начало теста вложенных циклов событий")
    result = asyncio.run(main_async())
    logger.info(f"Результат: {result}") 