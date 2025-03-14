import os
import sys
import pytest

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Фикстура для установки переменной окружения MISTRAL_SERVER_URL
@pytest.fixture(scope="session", autouse=True)
def set_mistral_server_url():
    """Устанавливает переменную окружения MISTRAL_SERVER_URL для тестов."""
    os.environ["MISTRAL_SERVER_URL"] = "http://139.59.241.176:8080"
    yield
    # Очистка после тестов (опционально)
    if "MISTRAL_SERVER_URL" in os.environ:
        del os.environ["MISTRAL_SERVER_URL"] 