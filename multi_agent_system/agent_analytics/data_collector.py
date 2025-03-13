import os
import json
from datetime import datetime


class AgentDataCollector:
    def __init__(self, storage_type="json", json_dir=None):
        self.storage_type = storage_type
        if json_dir is None:
            # По умолчанию используем директорию multi_agent_system/agent_analytics/data
            self.json_dir = os.path.join("multi_agent_system", "agent_analytics", "data")
        else:
            self.json_dir = json_dir

        if self.storage_type == "json":
            os.makedirs(self.json_dir, exist_ok=True)
        else:
            # Реализация для sqlite пока не предусмотрена
            pass

    def record_interaction(self, user_id, session_id, agent_name, request, response, processing_time, is_successful, metadata=None):
        # Проверка типов входных данных
        if not (isinstance(user_id, str) and isinstance(session_id, str) and isinstance(agent_name, str) \
                and isinstance(request, str) and isinstance(response, str) and isinstance(processing_time, (int, float)) \
                and isinstance(is_successful, bool)):
            raise ValueError("Invalid data types provided for interaction.")

        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "agent_name": agent_name,
            "request": request,
            "response": response,
            "processing_time": processing_time,
            "is_successful": is_successful
        }
        
        # Добавляем метаданные, если они предоставлены
        if metadata is not None and isinstance(metadata, dict):
            interaction["metadata"] = metadata
            
        file_path = os.path.join(self.json_dir, f"{session_id}.json")

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
                except Exception:
                    data = []
        else:
            data = []

        data.append(interaction)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        return True

    def get_interactions(self, **filters):
        interactions = []
        if not os.path.exists(self.json_dir):
            return interactions
        
        for filename in os.listdir(self.json_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.json_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        records = json.load(f)
                        if isinstance(records, list):
                            interactions.extend(records)
                except Exception:
                    continue
        
        for key, value in filters.items():
            interactions = [record for record in interactions if record.get(key) == value]
        return interactions
        
    def get_agent_interactions(self, agent_name=None):
        """
        Получает взаимодействия для конкретного агента.
        Если agent_name не указан, возвращает все взаимодействия.
        
        Args:
            agent_name (str, optional): Имя агента. По умолчанию None.
            
        Returns:
            list: Список взаимодействий (словари).
        """
        if agent_name:
            return self.get_interactions(agent_name=agent_name)
        else:
            return self.get_interactions() 