## Проблемы и их решения

### Актуальная конфигурация портов и сервисов

**Важно:** Этот раздел содержит актуальную информацию о конфигурации портов и сервисов. При любых изменениях в архитектуре системы необходимо обновлять эту информацию.

#### Основные сервисы и их конфигурация

1. **Mistral API (llama.cpp сервер)**
   - **Адрес:** `139.59.241.176:8080`
   - **Основной эндпоинт:** `/v1/chat/completions`
   - **Health эндпоинт:** `/health`
   - **Модель:** `TheBloke/Mistral-7B-Instruct-v0.3-GPTQ`
   - **Конфигурационные файлы:**
     ```bash
     # Проверка статуса сервера
     ssh root@139.59.241.176 "systemctl status llama-server.service"
     # Конфигурация запуска
     ./llama-server -m /opt/models/mistral/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf --port 8080 --host 0.0.0.0
     ```

2. **Файлы конфигурации, использующие Mistral API:**
   - `telegram_bot/config.py`: 
     ```python
     MISTRAL_API_URL = "http://139.59.241.176:8080"
     ```
   - `src/model_service/model_adapter/mistral_adapter.py`:
     ```python
     base_url = "http://139.59.241.176:8080"
     ```
   - `telegram_bot/model_service_client.py`:
     ```python
     base_url = "http://139.59.241.176:8080"
     ```
   - `src/utils/monitoring_script.py`:
     ```python
     api_url = "http://139.59.241.176:8080"
     ```

#### Проверка конфигурации

При возникновении проблем с подключением к API, проверьте:
1. Правильность портов во всех конфигурационных файлах (должен быть `8080`)
2. Доступность сервера через health endpoint
3. Статус сервера llama.cpp через systemctl
4. Логи в `logs/telegram_bot.log` и `logs/monitoring.log`

#### История изменений

- **2024-03-XX:** Стандартизация использования порта 8080 во всех сервисах
- Предыдущие версии использовали порт 8000, что приводило к ошибкам

### Блокировка хранилища Qdrant

**Проблема:**
При одновременном запуске нескольких процессов, использующих Qdrant в локальном режиме (API сервер и Telegram-бот), может возникать ошибка:
```
Storage folder data/memory/long_term/qdrant is already accessed by another instance of Qdrant client. If you require concurrent access, use Qdrant server instead.
```

**Решение:**
1. **Краткосрочное решение:** Удаление файла блокировки `.lock` из директории Qdrant и перезапуск сервисов:
   ```bash
   rm -f data/memory/long_term/qdrant/.lock
   ```

2. **Долгосрочное решение:** Модификация `memory_manager.py` для обработки ошибок блокировки:
   - Добавлена автоматическая очистка файлов блокировки
   - Добавлен механизм отказоустойчивости с переключением на in-memory режим при ошибках

3. **Рекомендуемое решение:** Использование Qdrant в серверном режиме вместо локального клиента:
   - Установить Qdrant Server (через Docker или pip)
   - Изменить конфигурацию подключения на использование серверного API
   - Подробная документация: `docs/qdrant_server_setup.md`

**Причины проблемы:**
- Локальный режим Qdrant не поддерживает конкурентный доступ
- Несколько процессов пытаются получить доступ к одному хранилищу
- Файл блокировки остается после аварийного завершения процесса 

### Проблема с отсутствующим методом add_ai_message

**Проблема:**
При взаимодействии через LangChain Router может возникать ошибка:
```
'MemoryManager' object has no attribute 'add_ai_message'
```

**Причина:**
В модуле `multi_agent_system/memory/conversation_memory.py` класс `MemoryManager` из `src/core/memory_system/memory_manager.py` переименован в `ConversationMemoryManager` через импорт-алиас, но в `langchain_router.py` используется метод `add_ai_message`, который отсутствует в исходном классе `MemoryManager`.

**Решение:**
Добавлен метод-алиас `add_ai_message` в класс `MemoryManager`, который вызывает существующий метод `add_assistant_message`, но с изменённым именем параметра (`agent_name` вместо `agent_id`) для совместимости с интерфейсом LangChain Router.

```python
def add_ai_message(
    self,
    user_id: str,
    content: str,
    agent_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Алиас для метода add_assistant_message для совместимости с интерфейсом langchain_router.
    """
    return self.add_assistant_message(
        user_id=user_id,
        content=content,
        agent_id=agent_name,  # Пересылаем agent_name как agent_id
        metadata=metadata
    )
```

**Примечание:**
В будущем рекомендуется либо стандартизировать интерфейсы между различными компонентами системы, либо использовать адаптеры для преобразования интерфейсов вместо прямых вызовов методов с разными именами. 

### Проблема с запуском Telegram бота

**Проблема:**
Telegram бот не отвечал на команды пользователей. В логах обнаруживалась ошибка:
```
cannot import name 'main' from 'telegram_bot.telegram_bot'
```

**Причина:**
В файле `run_telegram_bot.py` была попытка импортировать функцию `main` из модуля `telegram_bot.telegram_bot`, но такой функции в этом модуле не существовало. В модуле `telegram_bot.telegram_bot` определена функция `main()`, но в файле `telegram_bot/__init__.py` экспортируется только функция `create_application`.

**Решение:**
Модифицирован файл `run_telegram_bot.py` для корректного импорта:
```python
# Было (некорректный импорт)
from telegram_bot.telegram_bot import main
# Затем вызов:
main()

# Стало (корректный импорт и использование)
from telegram_bot import create_application
from telegram_bot.config import config

# Создаем и запускаем приложение
application = asyncio.run(create_application(config))
application.run_polling()
```

**Результат:**
После исправления бот успешно запускается и отвечает на команды пользователей, корректно взаимодействуя с Mistral API, размещенной на сервере по адресу 139.59.241.176:8000.

**Рекомендации:**
1. При модификации интерфейсов модулей необходимо обновлять все места вызова этих интерфейсов
2. Следует согласовывать экспортируемые функции и классы в файлах `__init__.py` с их фактическим использованием
3. При возникновении ошибок импорта рекомендуется анализировать не только фактическое наличие функций в модулях, но и правильность их экспорта 

### Проблема с форматом запросов к Mistral API

**Проблема:**
При отправке запросов к Mistral API возникала ошибка 500 Internal Server Error:
```
Ошибка на сервере: 500, {"detail":""}
```

**Причина:**
1. Неправильное имя модели в конфигурации (использовалось "mistral-small" вместо фактически доступной модели)
2. Несоответствие конфигурации моделей с реально доступными на сервере

**Решение:**
1. Обновлен список доступных моделей через запрос к `/v1/models`:
```bash
curl -X GET http://139.59.241.176:8000/v1/models
```

2. Изменена конфигурация в `mistral_adapter.py`:
```python
MISTRAL_MODELS = {
    "TheBloke/Mistral-7B-Instruct-v0.3-GPTQ": {
        "max_tokens": 8000,
        "description": "Mistral 7B Instruct v0.3 GPTQ",
        "recommended_temperature": 0.7,
        "recommended_top_p": 0.9,
    }
}
```

3. Обновлено значение модели по умолчанию:
```python
model_name: str = "TheBloke/Mistral-7B-Instruct-v0.3-GPTQ"
```

**Результат:**
- Бот успешно подключается к Mistral API
- Запросы обрабатываются корректно
- Система использует актуальную модель, доступную на сервере

**Рекомендации:**
1. Перед настройкой адаптера всегда проверять доступные модели через API эндпоинт `/v1/models`
2. Использовать точные идентификаторы моделей, предоставляемые сервером
3. Регулярно проверять доступность и актуальность используемых моделей
4. Реализовать автоматическое обновление списка доступных моделей при инициализации адаптера 

### Проблема с несоответствием портов Mistral API

**Проблема:**
Телеграм-бот не отвечал на сообщения пользователей. В логах обнаруживалась ошибка:
```
Ошибка сервера Mistral (попытка 3/4): Ошибка на сервере: 500, {"detail":""}
```

**Причина:**
Несоответствие между фактическим портом, на котором работает сервер llama.cpp (8080), и портом, к которому пытался подключиться бот (8000). 

При этом скрипт мониторинга API показывал, что сервер доступен по адресу http://139.59.241.176:8000 через health endpoint (возвращал статус 200), но при попытке выполнения запросов генерации текста возникала ошибка 500.

**Решение:**
1. Выполнена проверка конфигурации сервера llama.cpp с помощью команды:
```bash
ssh root@139.59.241.176 "systemctl status llama-server.service" 
```
которая показала, что сервер запущен на порту 8080:
```
./llama-server -m /opt/models/mistral/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf --port 8080 --host 0.0.0.0
```

2. Обновлены настройки подключения к API во всех конфигурационных файлах:
- `telegram_bot/config.py`: MISTRAL_API_URL изменен с `http://139.59.241.176:8000` на `http://139.59.241.176:8080`
- `src/model_service/model_adapter/mistral_adapter.py`: base_url по умолчанию изменен с порта 8000 на 8080
- `telegram_bot/model_service_client.py`: base_url изменен с порта 8000 на 8080 
- `src/utils/monitoring_script.py`: api_url изменен с порта 8000 на 8080

3. Перезапущены телеграм-бот и скрипт мониторинга с новыми настройками.

**Результат:**
- Бот успешно подключается к Mistral API и отвечает на сообщения пользователей
- Мониторинг API показывает стабильную доступность сервера
- Исчезли ошибки 500 при обработке запросов

**Рекомендации:**
1. При настройке многокомпонентной системы необходимо тщательно согласовывать порты и адреса между всеми компонентами
2. Рекомендуется использовать централизованную конфигурацию для настроек подключения, чтобы избежать рассинхронизации
3. Реализовать автоматическую проверку доступности API не только через health endpoint, но и через тестовый запрос генерации
4. Добавить в скрипт мониторинга проверку соответствия конфигурации с реальными настройками сервера 

### Проблема с форматом запросов к llama.cpp серверу

**Проблема:**
При отправке запросов к Mistral API через llama.cpp сервер возникала ошибка 404 Not Found:
```
Ошибка на сервере: 404, {"detail":""}
```

**Причина:**
1. Несоответствие между форматом запросов OpenAI API и форматом запросов llama.cpp сервера
2. Бот пытался использовать эндпоинт `/v1/chat/completions`, который не поддерживается llama.cpp сервером
3. llama.cpp сервер использует эндпоинт `/completion` с другим форматом запроса и ответа

**Решение:**
1. Изменен эндпоинт в файле `model_service_client.py`:
```python
# Было
url = f"{self.base_url}/v1/chat/completions"
# Стало
url = f"{self.base_url}/completion"
```

2. Изменен формат запроса:
```python
# Было - формат OpenAI API
payload = {
    "model": self.model_name,
    "messages": messages,
    "temperature": temperature,
    "max_tokens": max_tokens
}

# Стало - формат llama.cpp
# Преобразование сообщений чата в текстовый промпт
prompt = ""
for message in messages:
    role = message["role"]
    content = message["content"]
    if role == "user":
        prompt += f"User: {content}\n"
    elif role == "assistant":
        prompt += f"Assistant: {content}\n"
    elif role == "system":
        prompt += f"System: {content}\n"

# Добавляем префикс для ответа ассистента
prompt += "Assistant: "

payload = {
    "prompt": prompt,
    "model": self.model_name,
    "temperature": temperature,
    "max_tokens": max_tokens
}
```

3. Изменена обработка ответа:
```python
# Было - обработка ответа OpenAI API
response_data = await response.json()
assistant_message = response_data["choices"][0]["message"]["content"]

# Стало - обработка ответа llama.cpp
response_data = await response.json()
assistant_message = response_data.get("content", "")
```

**Результат:**
- Бот успешно отправляет запросы к llama.cpp серверу
- Ответы генерируются корректно
- Система использует правильный формат запросов и обработки ответов

**Рекомендации:**
1. При использовании llama.cpp сервера необходимо учитывать его уникальный API формат
2. Использовать адаптеры для преобразования между различными форматами API
3. Проверять документацию llama.cpp для конкретной версии сервера
4. Тестировать запросы напрямую через curl для проверки правильности форматирования:
```bash
curl -X POST http://139.59.241.176:8080/completion -H "Content-Type: application/json" -d '{"prompt": "User: Привет\nAssistant: ", "temperature": 0.7, "max_tokens": 1000}'
```

### Конфигурация микросервисов

**Актуальная конфигурация портов и URL:**

| Сервис | URL | Порт | Эндпоинт | Формат запроса |
|--------|-----|------|----------|----------------|
| llama.cpp (Mistral API) | http://139.59.241.176 | 8080 | /completion | llama.cpp формат |
| Telegram Bot | - | - | - | - |
| Orchestrator API | localhost | 8000 | /api/v1/... | REST API |
| Vector DB (Qdrant) | localhost | 6333 | - | Qdrant Python API |

**Важно:** При настройке системы всегда проверяйте актуальность этой таблицы и соответствие конфигурационных файлов.
