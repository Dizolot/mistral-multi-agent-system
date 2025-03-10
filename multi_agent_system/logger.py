"""
Модуль централизованной настройки логирования для мульти-агентной системы.

Обеспечивает единый интерфейс логирования для всех компонентов системы,
а также настраивает форматы, уровни и обработчики логов.
"""

import os
import sys
from pathlib import Path
import logging
from loguru import logger

# Определяем корневую директорию проекта
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Создаем директорию для логов, если она не существует
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Настройки логирования по умолчанию
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"

def configure_logger(name: str, log_level: str = None, log_file: str = None):
    """
    Настраивает и возвращает логгер для конкретного модуля.
    
    Args:
        name: Имя модуля или компонента для логгера
        log_level: Уровень логирования (INFO, DEBUG, ERROR и т.д.)
        log_file: Имя файла для записи логов
        
    Returns:
        Настроенный логгер
    """
    # Используем уровень по умолчанию, если не указан явно
    if log_level is None:
        log_level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    
    # Создаем новый логгер
    module_logger = logger.bind(name=name)
    
    # Очищаем обработчики, если есть
    logger.remove()
    
    # Добавляем обработчик для вывода в консоль
    logger.add(
        sys.stdout,
        format=DEFAULT_LOG_FORMAT,
        level=log_level,
        filter=lambda record: record["extra"].get("name") == name
    )
    
    # Если указан файл, добавляем обработчик для записи в файл
    if log_file:
        log_path = os.path.join(LOGS_DIR, log_file)
        logger.add(
            log_path,
            format=DEFAULT_LOG_FORMAT,
            level=log_level,
            rotation="500 MB",
            retention="10 days",
            filter=lambda record: record["extra"].get("name") == name
        )
    
    return module_logger

def get_logger(name: str, log_file: str = None):
    """
    Возвращает настроенный логгер для указанного модуля.
    
    Args:
        name: Имя модуля или компонента
        log_file: Имя файла для записи логов (если None, используется только консоль)
        
    Returns:
        Настроенный логгер
    """
    # Если файл не указан, создаем имя файла на основе имени модуля
    if log_file is None:
        module_name = name.split(".")[-1]
        log_file = f"{module_name}.log"
    
    return configure_logger(name, log_file=log_file)

# Настраиваем перехват логов из стандартной библиотеки logging
class InterceptHandler(logging.Handler):
    """
    Перехватчик логов из стандартной библиотеки logging для направления их в loguru.
    """
    
    def emit(self, record):
        # Получаем соответствующий уровень логирования в loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
            
        # Находим вызывающий код
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
            
        # Перенаправляем лог в loguru
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

# Настраиваем перехват логов для всех модулей, использующих стандартную библиотеку logging
def setup_logging_intercept():
    """
    Настраивает перехват логов из стандартной библиотеки logging.
    """
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # Перехватываем логи из известных библиотек
    for lib_logger in ["uvicorn", "uvicorn.error", "fastapi", "aiohttp"]:
        logging.getLogger(lib_logger).handlers = [InterceptHandler()]
        
# Настраиваем перехват при импорте модуля
setup_logging_intercept()

# Создаем дефолтный логгер для корневого уровня
default_logger = get_logger("multi_agent_system", "system.log") 