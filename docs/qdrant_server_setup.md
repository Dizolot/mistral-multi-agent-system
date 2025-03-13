# Настройка Qdrant в серверном режиме

## Проблема

При использовании Qdrant в локальном режиме (встроенный клиент) могут возникать ошибки блокировки хранилища, когда несколько процессов пытаются получить доступ к одной и той же папке хранения данных:

```
Storage folder data/memory/long_term/qdrant is already accessed by another instance of Qdrant client. If you require concurrent access, use Qdrant server instead.
```

Эта ошибка возникает потому, что локальный режим Qdrant не поддерживает конкурентный доступ из нескольких процессов. Для решения этой проблемы необходимо использовать Qdrant в серверном режиме.

## Решение

### 1. Установка Qdrant в серверном режиме

#### Вариант 1: Установка через Docker

```bash
# Запуск Qdrant в Docker
docker run -d -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    --name qdrant qdrant/qdrant
```

#### Вариант 2: Установка через pip

```bash
# Установка Qdrant Server
pip install qdrant-server

# Запуск Qdrant Server
qdrant
```

### 2. Изменение конфигурации клиента в проекте

Необходимо изменить инициализацию клиента Qdrant для подключения к серверу вместо использования локального режима:

```python
# Вместо:
self.client = QdrantClient(path=storage_dir)

# Использовать:
self.client = QdrantClient(host="localhost", port=6333)
```

### 3. Модификация конфигурации MemoryManager

Для корректной работы с Qdrant в серверном режиме, модифицируйте `memory_manager.py`:

```python
def default_vector_store_factory(collection_name: str) -> VectorStore:
    return QdrantVectorStore(
        collection_name=collection_name,
        vector_size=self.embedding_provider.get_embedding_dimension(),
        host="localhost",  # Адрес Qdrant сервера
        port=6333          # Порт Qdrant сервера
    )
```

### 4. Настройка переменных окружения

Для гибкого управления конфигурацией можно использовать переменные окружения:

```bash
# Установка переменных окружения для конфигурации Qdrant
export QDRANT_HOST="localhost"
export QDRANT_PORT=6333
```

И в коде:

```python
host = os.environ.get("QDRANT_HOST", "localhost")
port = int(os.environ.get("QDRANT_PORT", 6333))

self.client = QdrantClient(host=host, port=port)
```

## Преимущества серверного режима

1. **Конкурентный доступ** - несколько процессов могут работать с одним хранилищем данных
2. **Масштабируемость** - серверный режим лучше справляется с большими объемами данных 
3. **Отказоустойчивость** - в случае сбоя клиента данные хранятся отдельно и не повреждаются
4. **Возможность распределенного хранения** - можно настроить кластер Qdrant серверов
5. **Мониторинг** - серверный режим предоставляет API для мониторинга состояния

## Примечания

1. При использовании серверного режима убедитесь, что у вас достаточно оперативной памяти
2. Рекомендуется настроить регулярное резервное копирование данных
3. В продакшн-окружении защитите доступ к Qdrant серверу с помощью аутентификации 