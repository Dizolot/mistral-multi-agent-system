"""
Модуль для сбора и хранения данных о взаимодействии пользователей с агентами.
Собирает метрики производительности, запросы пользователей и ответы агентов
для дальнейшего анализа и улучшения.
"""
import os
import json
import time
import logging
import datetime
from typing import Dict, List, Any, Optional, Union

# Импорты для работы с базой данных
try:
    import sqlite3
except ImportError:
    logging.warning("SQLite3 не установлен или не доступен")

# Локальные импорты
from multi_agent_system.logger import get_logger

# Настройка логгера
logger = get_logger(__name__)

class AgentDataCollector:
    """
    Класс для сбора данных о взаимодействии пользователей с агентами.
    """
    
    def __init__(
        self, 
        storage_type: str = "json", 
        db_path: str = "agent_analytics/agent_data.db",
        json_dir: str = "agent_analytics/data"
    ):
        """
        Инициализация коллектора данных.
        
        Args:
            storage_type: Тип хранилища данных ("json" или "sqlite")
            db_path: Путь к файлу базы данных SQLite
            json_dir: Директория для хранения JSON-файлов
        """
        self.storage_type = storage_type
        self.db_path = db_path
        self.json_dir = json_dir
        
        # Создаем директорию для JSON-файлов, если её нет
        if self.storage_type == "json":
            os.makedirs(self.json_dir, exist_ok=True)
        
        # Инициализируем соединение с базой данных, если используется SQLite
        if self.storage_type == "sqlite":
            self._init_db()
        
        logger.info(f"AgentDataCollector инициализирован с хранилищем типа {storage_type}")
    
    def _init_db(self):
        """
        Инициализирует базу данных SQLite и создает необходимые таблицы, если их нет.
        """
        try:
            # Создаем директорию для базы данных, если её нет
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Устанавливаем соединение с базой данных
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу для хранения запросов и ответов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    session_id TEXT,
                    agent_name TEXT,
                    request TEXT,
                    response TEXT,
                    timestamp TIMESTAMP,
                    processing_time REAL,
                    is_successful BOOLEAN,
                    metadata TEXT
                )
            ''')
            
            # Создаем таблицу для хранения метрик производительности
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    timestamp TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Создаем таблицу для хранения оценок пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    session_id TEXT,
                    interaction_id INTEGER,
                    rating INTEGER,
                    feedback TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (interaction_id) REFERENCES interactions (id)
                )
            ''')
            
            # Создаем индексы для ускорения поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON interactions (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_agent_name ON interactions (agent_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_agent_name ON metrics (agent_name)')
            
            # Сохраняем изменения и закрываем соединение
            conn.commit()
            conn.close()
            
            logger.info("База данных SQLite успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
    
    def record_interaction(
        self,
        user_id: str,
        session_id: str,
        agent_name: str,
        request: str,
        response: str,
        processing_time: float,
        is_successful: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Записывает данные о взаимодействии пользователя с агентом.
        
        Args:
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии
            agent_name: Имя агента
            request: Запрос пользователя
            response: Ответ агента
            processing_time: Время обработки запроса (в секундах)
            is_successful: Признак успешной обработки
            metadata: Дополнительные метаданные
            
        Returns:
            bool: True, если запись успешно сохранена, иначе False
        """
        try:
            # Текущее время
            timestamp = datetime.datetime.now().isoformat()
            
            # Подготавливаем метаданные
            metadata_str = json.dumps(metadata) if metadata else "{}"
            
            # Сохраняем данные в соответствии с выбранным типом хранилища
            if self.storage_type == "sqlite":
                # Сохраняем в SQLite
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO interactions 
                    (user_id, session_id, agent_name, request, response, timestamp, processing_time, is_successful, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, session_id, agent_name, request, response, timestamp, processing_time, is_successful, metadata_str))
                
                # Сохраняем изменения и закрываем соединение
                conn.commit()
                conn.close()
            
            elif self.storage_type == "json":
                # Сохраняем в JSON-файл
                # Формируем имя файла на основе даты
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                file_path = os.path.join(self.json_dir, f"interactions_{date_str}.json")
                
                # Данные для записи
                interaction_data = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "request": request,
                    "response": response,
                    "timestamp": timestamp,
                    "processing_time": processing_time,
                    "is_successful": is_successful,
                    "metadata": metadata
                }
                
                # Проверяем, существует ли файл
                if os.path.exists(file_path):
                    # Если файл существует, загружаем данные и добавляем новую запись
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            # Если файл поврежден, создаем новый массив
                            data = []
                else:
                    # Если файл не существует, создаем новый массив
                    data = []
                
                # Добавляем новую запись
                data.append(interaction_data)
                
                # Сохраняем данные
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            else:
                logger.error(f"Неподдерживаемый тип хранилища: {self.storage_type}")
                return False
            
            logger.debug(f"Записано взаимодействие с агентом {agent_name}, пользователь {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при записи взаимодействия: {str(e)}")
            return False
    
    def record_metric(
        self,
        agent_name: str,
        metric_name: str,
        metric_value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Записывает метрику производительности агента.
        
        Args:
            agent_name: Имя агента
            metric_name: Название метрики
            metric_value: Значение метрики
            metadata: Дополнительные метаданные
            
        Returns:
            bool: True, если метрика успешно сохранена, иначе False
        """
        try:
            # Текущее время
            timestamp = datetime.datetime.now().isoformat()
            
            # Подготавливаем метаданные
            metadata_str = json.dumps(metadata) if metadata else "{}"
            
            # Сохраняем данные в соответствии с выбранным типом хранилища
            if self.storage_type == "sqlite":
                # Сохраняем в SQLite
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO metrics 
                    (agent_name, metric_name, metric_value, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (agent_name, metric_name, metric_value, timestamp, metadata_str))
                
                # Сохраняем изменения и закрываем соединение
                conn.commit()
                conn.close()
            
            elif self.storage_type == "json":
                # Сохраняем в JSON-файл
                # Формируем имя файла на основе даты
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                file_path = os.path.join(self.json_dir, f"metrics_{date_str}.json")
                
                # Данные для записи
                metric_data = {
                    "agent_name": agent_name,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "timestamp": timestamp,
                    "metadata": metadata
                }
                
                # Проверяем, существует ли файл
                if os.path.exists(file_path):
                    # Если файл существует, загружаем данные и добавляем новую запись
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            # Если файл поврежден, создаем новый массив
                            data = []
                else:
                    # Если файл не существует, создаем новый массив
                    data = []
                
                # Добавляем новую запись
                data.append(metric_data)
                
                # Сохраняем данные
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            else:
                logger.error(f"Неподдерживаемый тип хранилища: {self.storage_type}")
                return False
            
            logger.debug(f"Записана метрика {metric_name}={metric_value} для агента {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при записи метрики: {str(e)}")
            return False
    
    def record_user_rating(
        self,
        user_id: str,
        session_id: str,
        interaction_id: Optional[int] = None,
        rating: int = 0,
        feedback: str = ""
    ) -> bool:
        """
        Записывает оценку пользователя для ответа агента.
        
        Args:
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии
            interaction_id: Идентификатор взаимодействия (опционально)
            rating: Оценка от пользователя (обычно от 1 до 5)
            feedback: Текстовый отзыв от пользователя
            
        Returns:
            bool: True, если оценка успешно сохранена, иначе False
        """
        try:
            # Текущее время
            timestamp = datetime.datetime.now().isoformat()
            
            # Сохраняем данные в соответствии с выбранным типом хранилища
            if self.storage_type == "sqlite":
                # Сохраняем в SQLite
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO ratings 
                    (user_id, session_id, interaction_id, rating, feedback, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, session_id, interaction_id, rating, feedback, timestamp))
                
                # Сохраняем изменения и закрываем соединение
                conn.commit()
                conn.close()
            
            elif self.storage_type == "json":
                # Сохраняем в JSON-файл
                # Формируем имя файла на основе даты
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                file_path = os.path.join(self.json_dir, f"ratings_{date_str}.json")
                
                # Данные для записи
                rating_data = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "interaction_id": interaction_id,
                    "rating": rating,
                    "feedback": feedback,
                    "timestamp": timestamp
                }
                
                # Проверяем, существует ли файл
                if os.path.exists(file_path):
                    # Если файл существует, загружаем данные и добавляем новую запись
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            # Если файл поврежден, создаем новый массив
                            data = []
                else:
                    # Если файл не существует, создаем новый массив
                    data = []
                
                # Добавляем новую запись
                data.append(rating_data)
                
                # Сохраняем данные
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            else:
                logger.error(f"Неподдерживаемый тип хранилища: {self.storage_type}")
                return False
            
            logger.debug(f"Записана оценка {rating} от пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при записи оценки: {str(e)}")
            return False
    
    def get_agent_interactions(
        self,
        agent_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получает список взаимодействий с агентом за указанный период.
        
        Args:
            agent_name: Имя агента (если None, то для всех агентов)
            start_date: Начальная дата в формате YYYY-MM-DD
            end_date: Конечная дата в формате YYYY-MM-DD
            limit: Максимальное количество результатов
            
        Returns:
            List[Dict[str, Any]]: Список взаимодействий
        """
        interactions = []
        
        try:
            if self.storage_type == "sqlite":
                # Получаем данные из SQLite
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Формируем базовый запрос
                query = "SELECT * FROM interactions"
                params = []
                
                # Добавляем условия
                conditions = []
                
                if agent_name:
                    conditions.append("agent_name = ?")
                    params.append(agent_name)
                
                if start_date:
                    conditions.append("timestamp >= ?")
                    params.append(f"{start_date}T00:00:00")
                
                if end_date:
                    conditions.append("timestamp <= ?")
                    params.append(f"{end_date}T23:59:59")
                
                # Добавляем условия к запросу
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                # Добавляем сортировку и лимит
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                # Выполняем запрос
                cursor.execute(query, params)
                
                # Получаем результаты
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    interaction = dict(zip(columns, row))
                    try:
                        # Преобразуем метаданные из JSON
                        interaction["metadata"] = json.loads(interaction["metadata"])
                    except:
                        interaction["metadata"] = {}
                    interactions.append(interaction)
                
                # Закрываем соединение
                conn.close()
            
            elif self.storage_type == "json":
                # Получаем данные из JSON-файлов
                
                # Формируем список дат для загрузки
                if start_date and end_date:
                    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    dates = []
                    current = start
                    while current <= end:
                        dates.append(current.strftime("%Y-%m-%d"))
                        current += datetime.timedelta(days=1)
                else:
                    # Если даты не указаны, используем только текущую дату
                    dates = [datetime.datetime.now().strftime("%Y-%m-%d")]
                
                # Загружаем данные из файлов для каждой даты
                all_interactions = []
                for date_str in dates:
                    file_path = os.path.join(self.json_dir, f"interactions_{date_str}.json")
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                all_interactions.extend(data)
                        except Exception as e:
                            logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
                
                # Фильтруем по агенту, если указан
                if agent_name:
                    all_interactions = [i for i in all_interactions if i.get("agent_name") == agent_name]
                
                # Сортируем по времени (от новых к старым)
                all_interactions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                # Ограничиваем количество результатов
                interactions = all_interactions[:limit]
            
            return interactions
            
        except Exception as e:
            logger.error(f"Ошибка при получении взаимодействий: {str(e)}")
            return []
    
    def get_agent_metrics(
        self,
        agent_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получает список метрик агента за указанный период.
        
        Args:
            agent_name: Имя агента (если None, то для всех агентов)
            metric_name: Название метрики (если None, то все метрики)
            start_date: Начальная дата в формате YYYY-MM-DD
            end_date: Конечная дата в формате YYYY-MM-DD
            limit: Максимальное количество результатов
            
        Returns:
            List[Dict[str, Any]]: Список метрик
        """
        metrics = []
        
        try:
            if self.storage_type == "sqlite":
                # Получаем данные из SQLite
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Формируем базовый запрос
                query = "SELECT * FROM metrics"
                params = []
                
                # Добавляем условия
                conditions = []
                
                if agent_name:
                    conditions.append("agent_name = ?")
                    params.append(agent_name)
                
                if metric_name:
                    conditions.append("metric_name = ?")
                    params.append(metric_name)
                
                if start_date:
                    conditions.append("timestamp >= ?")
                    params.append(f"{start_date}T00:00:00")
                
                if end_date:
                    conditions.append("timestamp <= ?")
                    params.append(f"{end_date}T23:59:59")
                
                # Добавляем условия к запросу
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                # Добавляем сортировку и лимит
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                # Выполняем запрос
                cursor.execute(query, params)
                
                # Получаем результаты
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    metric = dict(zip(columns, row))
                    try:
                        # Преобразуем метаданные из JSON
                        metric["metadata"] = json.loads(metric["metadata"])
                    except:
                        metric["metadata"] = {}
                    metrics.append(metric)
                
                # Закрываем соединение
                conn.close()
            
            elif self.storage_type == "json":
                # Получаем данные из JSON-файлов
                
                # Формируем список дат для загрузки
                if start_date and end_date:
                    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    dates = []
                    current = start
                    while current <= end:
                        dates.append(current.strftime("%Y-%m-%d"))
                        current += datetime.timedelta(days=1)
                else:
                    # Если даты не указаны, используем только текущую дату
                    dates = [datetime.datetime.now().strftime("%Y-%m-%d")]
                
                # Загружаем данные из файлов для каждой даты
                all_metrics = []
                for date_str in dates:
                    file_path = os.path.join(self.json_dir, f"metrics_{date_str}.json")
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                all_metrics.extend(data)
                        except Exception as e:
                            logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
                
                # Фильтруем по агенту, если указан
                if agent_name:
                    all_metrics = [m for m in all_metrics if m.get("agent_name") == agent_name]
                
                # Фильтруем по названию метрики, если указано
                if metric_name:
                    all_metrics = [m for m in all_metrics if m.get("metric_name") == metric_name]
                
                # Сортируем по времени (от новых к старым)
                all_metrics.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                # Ограничиваем количество результатов
                metrics = all_metrics[:limit]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка при получении метрик: {str(e)}")
            return []
    
    def get_user_ratings(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получает список оценок от пользователей за указанный период.
        
        Args:
            user_id: Идентификатор пользователя (если None, то для всех пользователей)
            start_date: Начальная дата в формате YYYY-MM-DD
            end_date: Конечная дата в формате YYYY-MM-DD
            limit: Максимальное количество результатов
            
        Returns:
            List[Dict[str, Any]]: Список оценок
        """
        ratings = []
        
        try:
            if self.storage_type == "sqlite":
                # Получаем данные из SQLite
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Формируем базовый запрос
                query = "SELECT * FROM ratings"
                params = []
                
                # Добавляем условия
                conditions = []
                
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                
                if start_date:
                    conditions.append("timestamp >= ?")
                    params.append(f"{start_date}T00:00:00")
                
                if end_date:
                    conditions.append("timestamp <= ?")
                    params.append(f"{end_date}T23:59:59")
                
                # Добавляем условия к запросу
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                # Добавляем сортировку и лимит
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                # Выполняем запрос
                cursor.execute(query, params)
                
                # Получаем результаты
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    rating = dict(zip(columns, row))
                    ratings.append(rating)
                
                # Закрываем соединение
                conn.close()
            
            elif self.storage_type == "json":
                # Получаем данные из JSON-файлов
                
                # Формируем список дат для загрузки
                if start_date and end_date:
                    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    dates = []
                    current = start
                    while current <= end:
                        dates.append(current.strftime("%Y-%m-%d"))
                        current += datetime.timedelta(days=1)
                else:
                    # Если даты не указаны, используем только текущую дату
                    dates = [datetime.datetime.now().strftime("%Y-%m-%d")]
                
                # Загружаем данные из файлов для каждой даты
                all_ratings = []
                for date_str in dates:
                    file_path = os.path.join(self.json_dir, f"ratings_{date_str}.json")
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                all_ratings.extend(data)
                        except Exception as e:
                            logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
                
                # Фильтруем по пользователю, если указан
                if user_id:
                    all_ratings = [r for r in all_ratings if r.get("user_id") == user_id]
                
                # Сортируем по времени (от новых к старым)
                all_ratings.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                # Ограничиваем количество результатов
                ratings = all_ratings[:limit]
            
            return ratings
            
        except Exception as e:
            logger.error(f"Ошибка при получении оценок: {str(e)}")
            return []

# Создаем экземпляр коллектора данных для использования в других модулях
data_collector = AgentDataCollector() 