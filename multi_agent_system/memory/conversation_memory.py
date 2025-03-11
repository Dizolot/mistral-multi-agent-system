"""
Модуль для хранения и управления историей разговоров.

Этот модуль использует различные типы памяти из LangChain для хранения истории диалогов
и предоставляет интерфейс для их использования в мульти-агентной системе.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.language_models import BaseLLM
from langchain_mistralai.chat_models import ChatMistralAI

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConversationMemoryManager:
    """
    Менеджер для хранения и управления памятью разговоров.
    
    Этот класс предоставляет интерфейс для работы с различными типами памяти LangChain,
    включая буферную память, суммаризирующую память и др.
    """
    
    def __init__(
        self,
        storage_dir: str = "multi_agent_system/memory/storage",
        max_buffer_length: int = 20,
        llm: Optional[BaseLLM] = None
    ):
        """
        Инициализирует менеджер памяти.
        
        Args:
            storage_dir: Директория для хранения данных памяти
            max_buffer_length: Максимальная длина буфера сообщений
            llm: Языковая модель для суммаризации (если None, используется локальный Mistral)
        """
        self.storage_dir = storage_dir
        self.max_buffer_length = max_buffer_length
        
        # Инициализируем языковую модель для суммаризации
        self.llm = llm or ChatMistralAI(
            model="mistral-medium",
            mistral_api_url="http://localhost:8080/completion"
        )
        
        # Создаем директорию для хранения данных памяти
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Словарь для хранения объектов памяти для каждого пользователя
        self.buffer_memories = {}
        self.summary_memories = {}
        
        logger.info(f"Менеджер памяти инициализирован. Директория хранения: {self.storage_dir}")
    
    def get_buffer_memory(self, user_id: str) -> ConversationBufferMemory:
        """
        Получает буферную память для пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Объект ConversationBufferMemory для пользователя
        """
        # Если память для пользователя еще не создана, создаем новую
        if user_id not in self.buffer_memories:
            memory = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history",
                output_key="response"
            )
            
            # Загружаем сохраненную память, если она существует
            memory_path = os.path.join(self.storage_dir, f"{user_id}_buffer.json")
            if os.path.exists(memory_path):
                try:
                    with open(memory_path, 'r', encoding='utf-8') as f:
                        memory_data = json.load(f)
                    
                    # Восстанавливаем историю сообщений
                    for message_data in memory_data.get("messages", []):
                        role = message_data.get("role", "")
                        content = message_data.get("content", "")
                        
                        if role == "human":
                            memory.chat_memory.add_user_message(content)
                        elif role == "ai":
                            memory.chat_memory.add_ai_message(content)
                        elif role == "system":
                            memory.chat_memory.add_message(SystemMessage(content=content))
                    
                    logger.info(f"Загружена буферная память для пользователя {user_id} ({len(memory_data.get('messages', []))} сообщений)")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке буферной памяти для пользователя {user_id}: {str(e)}")
            
            self.buffer_memories[user_id] = memory
        
        return self.buffer_memories[user_id]
    
    def get_summary_memory(self, user_id: str) -> ConversationSummaryMemory:
        """
        Получает суммаризирующую память для пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Объект ConversationSummaryMemory для пользователя
        """
        # Если память для пользователя еще не создана, создаем новую
        if user_id not in self.summary_memories:
            memory = ConversationSummaryMemory(
                llm=self.llm,
                return_messages=True,
                memory_key="chat_history",
                output_key="response"
            )
            
            # Загружаем сохраненную память, если она существует
            memory_path = os.path.join(self.storage_dir, f"{user_id}_summary.json")
            if os.path.exists(memory_path):
                try:
                    with open(memory_path, 'r', encoding='utf-8') as f:
                        memory_data = json.load(f)
                    
                    # Восстанавливаем историю сообщений и суммарную память
                    for message_data in memory_data.get("messages", []):
                        role = message_data.get("role", "")
                        content = message_data.get("content", "")
                        
                        if role == "human":
                            memory.chat_memory.add_user_message(content)
                        elif role == "ai":
                            memory.chat_memory.add_ai_message(content)
                        elif role == "system":
                            memory.chat_memory.add_message(SystemMessage(content=content))
                    
                    # Устанавливаем уже созданное резюме, если оно есть
                    if "summary" in memory_data:
                        memory.moving_summary_buffer = memory_data["summary"]
                    
                    logger.info(f"Загружена суммаризирующая память для пользователя {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке суммаризирующей памяти для пользователя {user_id}: {str(e)}")
            
            self.summary_memories[user_id] = memory
        
        return self.summary_memories[user_id]
    
    def add_user_message(self, user_id: str, message: str) -> None:
        """
        Добавляет сообщение пользователя в память.
        
        Args:
            user_id: Идентификатор пользователя
            message: Текст сообщения пользователя
        """
        # Добавляем сообщение в буферную память
        buffer_memory = self.get_buffer_memory(user_id)
        buffer_memory.chat_memory.add_user_message(message)
        
        # Добавляем сообщение в суммаризирующую память
        summary_memory = self.get_summary_memory(user_id)
        summary_memory.chat_memory.add_user_message(message)
        
        # Проверяем, не превышает ли буфер максимальную длину
        if len(buffer_memory.chat_memory.messages) > self.max_buffer_length:
            # Суммаризируем старую часть буфера перед его обрезкой
            messages_to_summarize = buffer_memory.chat_memory.messages[:-self.max_buffer_length]
            self._summarize_messages(user_id, messages_to_summarize)
            
            # Обрезаем буфер до максимальной длины
            buffer_memory.chat_memory.messages = buffer_memory.chat_memory.messages[-self.max_buffer_length:]
        
        # Сохраняем память
        self._save_memory(user_id)
        
        logger.info(f"Добавлено сообщение пользователя {user_id} в память")
    
    def add_ai_message(self, user_id: str, message: str, agent_name: Optional[str] = None) -> None:
        """
        Добавляет ответ AI в память.
        
        Args:
            user_id: Идентификатор пользователя
            message: Текст ответа AI
            agent_name: Имя агента, отправившего сообщение (опционально)
        """
        # Добавляем сообщение в буферную память
        buffer_memory = self.get_buffer_memory(user_id)
        
        if agent_name:
            # Если указано имя агента, добавляем его к сообщению
            ai_message = f"[{agent_name}]: {message}"
        else:
            ai_message = message
        
        buffer_memory.chat_memory.add_ai_message(ai_message)
        
        # Добавляем сообщение в суммаризирующую память
        summary_memory = self.get_summary_memory(user_id)
        summary_memory.chat_memory.add_ai_message(ai_message)
        
        # Проверяем, не превышает ли буфер максимальную длину
        if len(buffer_memory.chat_memory.messages) > self.max_buffer_length:
            # Суммаризируем старую часть буфера перед его обрезкой
            messages_to_summarize = buffer_memory.chat_memory.messages[:-self.max_buffer_length]
            self._summarize_messages(user_id, messages_to_summarize)
            
            # Обрезаем буфер до максимальной длины
            buffer_memory.chat_memory.messages = buffer_memory.chat_memory.messages[-self.max_buffer_length:]
        
        # Сохраняем память
        self._save_memory(user_id)
        
        logger.info(f"Добавлен ответ AI для пользователя {user_id} в память")
    
    def add_system_message(self, user_id: str, message: str) -> None:
        """
        Добавляет системное сообщение в память.
        
        Args:
            user_id: Идентификатор пользователя
            message: Текст системного сообщения
        """
        # Добавляем сообщение в буферную память
        buffer_memory = self.get_buffer_memory(user_id)
        buffer_memory.chat_memory.add_message(SystemMessage(content=message))
        
        # Добавляем сообщение в суммаризирующую память
        summary_memory = self.get_summary_memory(user_id)
        summary_memory.chat_memory.add_message(SystemMessage(content=message))
        
        # Сохраняем память
        self._save_memory(user_id)
        
        logger.info(f"Добавлено системное сообщение для пользователя {user_id} в память")
    
    def get_chat_history(self, user_id: str) -> List[BaseMessage]:
        """
        Получает историю чата для пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Список сообщений из истории чата
        """
        buffer_memory = self.get_buffer_memory(user_id)
        return buffer_memory.chat_memory.messages
    
    def get_chat_summary(self, user_id: str) -> str:
        """
        Получает суммарное представление истории чата для пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Строка с суммарным представлением истории чата
        """
        # Получаем суммаризирующую память для пользователя
        summary_memory = self.get_summary_memory(user_id)
        
        # В новой версии LangChain атрибут moving_summary_buffer не существует
        # Вместо этого используем предикторную функцию для получения суммарного представления
        try:
            # Пытаемся получить суммарное представление
            if hasattr(summary_memory, "moving_summary_buffer"):
                # Старая версия LangChain
                return summary_memory.moving_summary_buffer
            elif hasattr(summary_memory, "predict_new_summary"):
                # Новая версия LangChain
                messages = summary_memory.chat_memory.messages
                if not messages:
                    return ""
                
                # Создаем строковое представление сообщений в формате, понятном для LangChain
                messages_str = ""
                for msg in messages:
                    if hasattr(msg, "type"):
                        if msg.type == "human":
                            messages_str += f"Human: {msg.content}\n"
                        elif msg.type == "ai":
                            messages_str += f"AI: {msg.content}\n"
                        elif msg.type == "system":
                            messages_str += f"System: {msg.content}\n"
                    else:
                        # Для совместимости со старыми версиями
                        if isinstance(msg, HumanMessage):
                            messages_str += f"Human: {msg.content}\n"
                        elif isinstance(msg, AIMessage):
                            messages_str += f"AI: {msg.content}\n"
                        elif isinstance(msg, SystemMessage):
                            messages_str += f"System: {msg.content}\n"
                
                # Если нет сообщений, возвращаем пустую строку
                if not messages_str:
                    return ""
                
                # Используем простое резюме, если не можем получить через predict_new_summary
                try:
                    return summary_memory.predict_new_summary(messages_str, "")
                except Exception as e:
                    logger.warning(f"Не удалось получить суммарное представление через predict_new_summary: {str(e)}")
                    return f"История диалога содержит {len(messages)} сообщений."
            else:
                # Если не можем получить суммарное представление, возвращаем простое описание
                messages = summary_memory.chat_memory.messages
                return f"История диалога содержит {len(messages)} сообщений."
        except Exception as e:
            logger.error(f"Ошибка при получении суммарного представления для пользователя {user_id}: {str(e)}")
            return ""
    
    def clear_memory(self, user_id: str) -> None:
        """
        Очищает память для пользователя.
        
        Args:
            user_id: Идентификатор пользователя
        """
        # Очищаем буферную память
        if user_id in self.buffer_memories:
            self.buffer_memories[user_id].clear()
        
        # Очищаем суммаризирующую память
        if user_id in self.summary_memories:
            self.summary_memories[user_id].clear()
        
        # Удаляем файлы памяти
        buffer_path = os.path.join(self.storage_dir, f"{user_id}_buffer.json")
        summary_path = os.path.join(self.storage_dir, f"{user_id}_summary.json")
        
        if os.path.exists(buffer_path):
            os.remove(buffer_path)
        
        if os.path.exists(summary_path):
            os.remove(summary_path)
        
        logger.info(f"Очищена память для пользователя {user_id}")
    
    def _save_memory(self, user_id: str) -> None:
        """
        Сохраняет память для пользователя в файл.
        
        Args:
            user_id: Идентификатор пользователя
        """
        # Сохраняем буферную память
        try:
            buffer_memory = self.get_buffer_memory(user_id)
            buffer_memory_path = os.path.join(self.storage_dir, f"{user_id}_buffer.json")
            
            # Преобразуем сообщения в формат для сохранения
            messages_data = []
            for message in buffer_memory.chat_memory.messages:
                if isinstance(message, HumanMessage):
                    messages_data.append({"role": "human", "content": message.content})
                elif isinstance(message, AIMessage):
                    messages_data.append({"role": "ai", "content": message.content})
                elif isinstance(message, SystemMessage):
                    messages_data.append({"role": "system", "content": message.content})
            
            # Сохраняем данные в файл
            with open(buffer_memory_path, 'w', encoding='utf-8') as f:
                json.dump({"messages": messages_data}, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Буферная память для пользователя {user_id} сохранена")
        except Exception as e:
            logger.error(f"Ошибка при сохранении буферной памяти для пользователя {user_id}: {str(e)}")
        
        # Сохраняем суммаризирующую память
        try:
            summary_memory = self.get_summary_memory(user_id)
            summary_memory_path = os.path.join(self.storage_dir, f"{user_id}_summary.json")
            
            # Преобразуем сообщения в формат для сохранения
            messages_data = []
            for message in summary_memory.chat_memory.messages:
                if isinstance(message, HumanMessage):
                    messages_data.append({"role": "human", "content": message.content})
                elif isinstance(message, AIMessage):
                    messages_data.append({"role": "ai", "content": message.content})
                elif isinstance(message, SystemMessage):
                    messages_data.append({"role": "system", "content": message.content})
            
            # Получаем суммарное представление
            summary_data = ""
            if hasattr(summary_memory, "moving_summary_buffer"):
                summary_data = summary_memory.moving_summary_buffer
            else:
                # Для новой версии LangChain получаем суммарное представление через get_chat_summary
                summary_data = self.get_chat_summary(user_id)
            
            # Сохраняем данные в файл
            with open(summary_memory_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "messages": messages_data,
                    "summary": summary_data
                }, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Суммаризирующая память для пользователя {user_id} сохранена")
        except Exception as e:
            logger.error(f"Ошибка при сохранении суммаризирующей памяти для пользователя {user_id}: {str(e)}")
    
    def _summarize_messages(self, user_id: str, messages: List[BaseMessage]) -> None:
        """
        Суммаризирует сообщения и обновляет суммаризирующую память.
        
        Args:
            user_id: Идентификатор пользователя
            messages: Список сообщений для суммаризации
        """
        if not messages:
            return
        
        try:
            # Получаем суммаризирующую память
            summary_memory = self.get_summary_memory(user_id)
            
            # Создаем строковое представление сообщений в формате, понятном для LangChain
            messages_str = ""
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    messages_str += f"Human: {msg.content}\n"
                elif isinstance(msg, AIMessage):
                    messages_str += f"AI: {msg.content}\n"
                elif isinstance(msg, SystemMessage):
                    messages_str += f"System: {msg.content}\n"
            
            # Получаем текущее суммарное представление
            current_summary = ""
            if hasattr(summary_memory, "moving_summary_buffer"):
                # Старая версия LangChain
                current_summary = summary_memory.moving_summary_buffer
            
            # Создаем новое суммарное представление
            if hasattr(summary_memory, "predict_new_summary"):
                # Новая версия LangChain
                try:
                    new_summary = summary_memory.predict_new_summary(messages_str, current_summary)
                    
                    # Обновляем суммарное представление
                    if hasattr(summary_memory, "moving_summary_buffer"):
                        summary_memory.moving_summary_buffer = new_summary
                except Exception as e:
                    logger.warning(f"Не удалось создать суммарное представление через predict_new_summary: {str(e)}")
                    # Используем стандартный механизм добавления сообщений
                    for message in messages:
                        if isinstance(message, HumanMessage):
                            summary_memory.chat_memory.add_user_message(message.content)
                        elif isinstance(message, AIMessage):
                            summary_memory.chat_memory.add_ai_message(message.content)
                        elif isinstance(message, SystemMessage):
                            summary_memory.chat_memory.add_message(message)
            else:
                # Если метод predict_new_summary не доступен, используем стандартный механизм
                for message in messages:
                    if isinstance(message, HumanMessage):
                        summary_memory.chat_memory.add_user_message(message.content)
                    elif isinstance(message, AIMessage):
                        summary_memory.chat_memory.add_ai_message(message.content)
                    elif isinstance(message, SystemMessage):
                        summary_memory.chat_memory.add_message(message)
            
            # Сохраняем обновленную память
            self._save_memory(user_id)
            
            logger.info(f"Суммаризировано {len(messages)} сообщений для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при суммаризации сообщений для пользователя {user_id}: {str(e)}")
    
    def get_all_users(self) -> List[str]:
        """
        Получает список всех пользователей, для которых есть сохраненная память.
        
        Returns:
            Список идентификаторов пользователей
        """
        users = set()
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith("_buffer.json"):
                user_id = filename.replace("_buffer.json", "")
                users.add(user_id)
        
        return list(users)
    
    def get_formatted_history(self, user_id: str, include_system_messages: bool = False) -> List[Dict[str, str]]:
        """
        Получает форматированную историю чата для использования в LangChain.
        
        Args:
            user_id: Идентификатор пользователя
            include_system_messages: Включать ли системные сообщения в историю
            
        Returns:
            Список словарей с ролью и содержанием сообщения
        """
        buffer_memory = self.get_buffer_memory(user_id)
        formatted_history = []
        
        for message in buffer_memory.chat_memory.messages:
            if isinstance(message, HumanMessage):
                formatted_history.append({
                    "role": "user",
                    "content": message.content
                })
            elif isinstance(message, AIMessage):
                formatted_history.append({
                    "role": "assistant",
                    "content": message.content
                })
            elif isinstance(message, SystemMessage) and include_system_messages:
                formatted_history.append({
                    "role": "system",
                    "content": message.content
                })
        
        return formatted_history


# Если файл запущен как скрипт, выполняем демонстрационный пример
if __name__ == "__main__":
    # Создаем директорию для хранения данных памяти
    os.makedirs("multi_agent_system/memory/storage", exist_ok=True)
    
    # Создаем менеджер памяти
    memory_manager = ConversationMemoryManager()
    
    # Добавляем несколько сообщений
    memory_manager.add_system_message("test_user", "Начало разговора.")
    memory_manager.add_user_message("test_user", "Привет! Как дела?")
    memory_manager.add_ai_message("test_user", "Привет! У меня всё хорошо. Чем могу помочь?")
    memory_manager.add_user_message("test_user", "Расскажи мне о погоде.")
    memory_manager.add_ai_message("test_user", "Я не имею доступа к актуальной информации о погоде.", "general_agent")
    
    # Получаем историю чата
    chat_history = memory_manager.get_chat_history("test_user")
    print(f"История чата для пользователя test_user ({len(chat_history)} сообщений):")
    for message in chat_history:
        print(f"- {message.type}: {message.content}")
    
    # Получаем форматированную историю
    formatted_history = memory_manager.get_formatted_history("test_user")
    print("\nФорматированная история чата:")
    for message in formatted_history:
        print(f"- {message['role']}: {message['content']}")
    
    # Очищаем память
    memory_manager.clear_memory("test_user")
    print("\nПамять очищена.") 