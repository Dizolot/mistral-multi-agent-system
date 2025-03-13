"""
Модуль для настройки логирования в мульти-агентной системе.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

def get_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Создает и настраивает логгер с заданным именем.
    
    Args:
        name: Имя логгера
        log_file: Имя файла для записи логов (если None, то логи выводятся только в консоль)
        level: Уровень логирования
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    # Создаем директорию для логов, если она не существует
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Если логгер уже имеет обработчики, не добавляем новые
    if logger.handlers:
        return logger
    
    # Создаем форматтер
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Добавляем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Если указан файл для логов, добавляем обработчик для записи в файл
    if log_file:
        file_path = os.path.join(logs_dir, log_file)
        file_handler = RotatingFileHandler(file_path, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger 