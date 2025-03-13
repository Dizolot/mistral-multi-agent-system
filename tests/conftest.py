import os
import sys
# Добавляем корневую директорию проекта в sys.path для корректного импорта пакетов
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Добавляем каталог src/core для корректного импорта пакета memory_system
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))) 