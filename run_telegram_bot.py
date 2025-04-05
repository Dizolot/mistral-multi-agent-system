#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль запуска Telegram-бота для системы непрерывного улучшения.

Этот модуль обеспечивает запуск Telegram-бота в качестве отдельного процесса,
устанавливает соединение с основной системой и обрабатывает команды пользователей.
"""

import asyncio
import argparse
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Добавляем путь к корню проекта для импорта модулей
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from src.continuous_improvement.telegram_integration import TelegramIntegration
from src.telegram.telegram_reporter import TelegramReporter

class TelegramBotRunner:
    """Класс для запуска и управления жизненным циклом Telegram-бота."""
    
    def __init__(self, config_path: str):
        """Инициализация запускателя Telegram-бота.
        
        Args:
            config_path: Путь к файлу конфигурации.
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.running = False
        self.telegram_reporter = None
        self.telegram_integration = None
        
        # Настраиваем обработчики сигналов
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации из файла.
        
        Returns:
            Словарь с настройками конфигурации.
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Обогащаем конфигурацию переменными окружения
            config['telegram_token'] = os.environ.get('TELEGRAM_TOKEN', config.get('telegram_token', ''))
            config['admin_chat_id'] = os.environ.get('ADMIN_CHAT_ID', config.get('admin_chat_id', ''))
            
            if not config['telegram_token']:
                logger.error("Не задан TELEGRAM_TOKEN")
                raise ValueError("TELEGRAM_TOKEN не задан в переменных окружения или конфигурации")
                
            return config
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            # Возвращаем базовую конфигурацию по умолчанию
            return {
                'telegram_token': os.environ.get('TELEGRAM_TOKEN', ''),
                'admin_chat_id': os.environ.get('ADMIN_CHAT_ID', ''),
                'reporting_interval': 3600,  # 1 час
                'api_url': 'http://localhost:8080',
                'data_dir': 'data'
            }
    
    async def start(self):
        """Запуск Telegram-бота и его компонентов."""
        if self.running:
            logger.warning("Telegram-бот уже запущен")
            return
        
        try:
            logger.info("Запуск Telegram-бота...")
            
            # Инициализируем TelegramReporter
            self.telegram_reporter = TelegramReporter(
                token=self.config['telegram_token'],
                admin_chat_id=self.config['admin_chat_id']
            )
            await self.telegram_reporter.start()
            
            # Создаем TelegramIntegration в автономном режиме
            self.telegram_integration = TelegramIntegration(
                agent_orchestrator=None,  # В автономном режиме нет оркестратора
                improvement_tracker=None,  # В автономном режиме нет трекера улучшений
                telegram_reporter=self.telegram_reporter,
                admin_chat_id=self.config['admin_chat_id'],
                reporting_interval=self.config.get('reporting_interval', 3600),
                api_url=self.config.get('api_url', 'http://localhost:8080'),
                standalone_mode=True  # Включаем автономный режим
            )
            await self.telegram_integration.start()
            
            self.running = True
            
            # Отправляем уведомление о запуске
            await self.telegram_reporter.send_message(
                chat_id=self.config['admin_chat_id'],
                text=f"🤖 Telegram-бот запущен в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            logger.info("Telegram-бот успешно запущен")
            
            # Держим бота запущенным
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Ошибка при запуске Telegram-бота: {e}", exc_info=True)
            await self.stop()
    
    async def stop(self):
        """Остановка Telegram-бота и освобождение ресурсов."""
        if not self.running:
            return
        
        logger.info("Остановка Telegram-бота...")
        
        try:
            # Отправляем уведомление о остановке, если репортер еще работает
            if self.telegram_reporter and self.config.get('admin_chat_id'):
                try:
                    await self.telegram_reporter.send_message(
                        chat_id=self.config['admin_chat_id'],
                        text=f"🛑 Telegram-бот останавливается в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение о остановке: {e}")
            
            # Останавливаем интеграцию
            if self.telegram_integration:
                await self.telegram_integration.stop()
                
            # Останавливаем репортер
            if self.telegram_reporter:
                await self.telegram_reporter.stop()
                
        except Exception as e:
            logger.error(f"Ошибка при остановке Telegram-бота: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("Telegram-бот остановлен")
    
    def _handle_signal(self, signum, frame):
        """Обработка сигналов завершения.
        
        Args:
            signum: Номер сигнала.
            frame: Текущий стек-фрейм.
        """
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        if self.running:
            asyncio.create_task(self.stop())

async def main():
    """Главная функция для запуска Telegram-бота."""
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description='Запуск Telegram-бота для системы непрерывного улучшения')
    parser.add_argument('--config', type=str, default='config.json', help='Путь к файлу конфигурации')
    args = parser.parse_args()
    
    # Создаем и запускаем бота
    bot_runner = TelegramBotRunner(config_path=args.config)
    try:
        await bot_runner.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания клавиатуры")
    finally:
        await bot_runner.stop()

if __name__ == "__main__":
    asyncio.run(main()) 