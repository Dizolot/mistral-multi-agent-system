## Проблемы и их решения

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