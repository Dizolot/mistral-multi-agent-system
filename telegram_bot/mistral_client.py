"""
Клиент для взаимодействия с Mistral API через HTTP
"""

import aiohttp
import json
import logging
import asyncio
import threading
import queue
from typing import Dict, Any, List, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mistral_client')

class MistralClient:
    """
    Клиент для взаимодействия с API Mistral через HTTP
    """
    
    def __init__(self, base_url: str, timeout: int = 180):
        """
        Инициализация клиента
        
        Args:
            base_url: Базовый URL API Mistral
            timeout: Таймаут запросов в секундах
        """
        self.base_url = base_url
        self.timeout = timeout
        self._session = None
        self._request_queue = queue.Queue()
        self._response_queues = {}
        self._worker_thread = None
        self._running = False
        
        # Запускаем фоновый поток для обработки запросов
        self._start_worker()
        
        logger.info(f'Инициализирован клиент Mistral API с базовым URL: {base_url}')
    
    def _start_worker(self):
        """
        Запускает фоновый поток для обработки запросов
        """
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Запущен фоновый поток для обработки запросов")
    
    def _worker_loop(self):
        """
        Основной цикл обработки запросов в фоновом потоке
        """
        # Создаем новый event loop для потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("Фоновый поток для обработки запросов запущен")
        
        while self._running:
            try:
                # Получаем запрос из очереди (неблокирующий режим)
                try:
                    request = self._request_queue.get(block=True, timeout=0.1)
                except queue.Empty:
                    continue
                
                logger.info(f"Получен запрос для обработки: {request.get('id')}")
                
                # Обрабатываем запрос
                request_id = request.get('id')
                prompt = request.get('prompt')
                temperature = request.get('temperature', 0.7)
                max_tokens = request.get('max_tokens', 1000)
                
                # Выполняем запрос асинхронно
                response = loop.run_until_complete(
                    self._process_request(prompt, temperature, max_tokens)
                )
                
                logger.info(f"Запрос {request_id} обработан, отправляем ответ")
                
                # Отправляем ответ в соответствующую очередь
                if request_id in self._response_queues:
                    self._response_queues[request_id].put(response)
                    del self._response_queues[request_id]
                
            except Exception as e:
                logger.error(f"Ошибка в фоновом потоке: {str(e)}", exc_info=True)
        
        # Закрываем event loop при завершении
        loop.close()
        logger.info("Фоновый поток для обработки запросов завершен")
    
    async def _process_request(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """
        Обрабатывает запрос к API Mistral
        """
        try:
            logger.info(f"Отправка запроса на {self.base_url}")
            
            # Определяем, какой эндпоинт использовать (для совместимости с разными реализациями)
            # Если URL содержит конкретный путь API, используем его
            if '/api/generate' in self.base_url or '/v1/chat/completions' in self.base_url:
                api_url = self.base_url
            else:
                # Пробуем стандартный эндпоинт Mistral
                api_url = f'{self.base_url}/completion'
            
            logger.info(f"Используемый URL API: {api_url}")
            
            async with aiohttp.ClientSession() as session:
                # Форматируем запрос в зависимости от типа API
                if '/v1/chat/completions' in api_url:
                    # OpenAI-совместимый формат
                    payload = {
                        "model": "mistral",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                elif '/api/generate' in api_url:
                    # Формат Ollama
                    payload = {
                        "model": "mistral",
                        "prompt": prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                else:
                    # Стандартный формат Mistral
                    payload = {
                        'prompt': f'<s>[INST] {prompt} [/INST]',
                        'n_predict': max_tokens,
                        'temperature': temperature,
                        'top_p': 0.95,
                        'stop': ["</s>", "[INST]"],
                        'stream': False
                    }
                
                logger.info(f"Отправляемый payload: {json.dumps(payload, ensure_ascii=False)[:200]}...")
                
                async with session.post(
                    api_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f'Ошибка при отправке запроса: {response.status}, {error_text}')
                        return f'Произошла ошибка при отправке запроса (код {response.status}): {error_text[:100]}'
                    
                    # Получаем ответ
                    result = await response.json()
                    logger.info(f"Получен ответ: {json.dumps(result, ensure_ascii=False)[:200]}...")
                    
                    # Парсим ответ в зависимости от формата API
                    if '/v1/chat/completions' in api_url and 'choices' in result:
                        # OpenAI-совместимый формат
                        return result['choices'][0]['message']['content'].strip()
                    elif '/api/generate' in api_url and 'response' in result:
                        # Формат Ollama
                        return result['response'].strip()
                    elif 'content' in result:
                        # Стандартный формат Mistral
                        return result['content'].strip()
                    else:
                        logger.error(f'Неожиданный формат ответа: {result}')
                        return 'Получен неожиданный формат ответа от модели'
                        
        except asyncio.TimeoutError:
            logger.error(f'Таймаут запроса после {self.timeout} секунд')
            return 'Запрос занял слишком много времени. Пожалуйста, попробуйте еще раз'
            
        except Exception as e:
            logger.error(f'Ошибка при генерации ответа: {str(e)}', exc_info=True)
            return f'Произошла ошибка: {str(e)}'
    
    def generate_text(self, context: List[Dict[str, str]], 
                     temperature: float = 0.7,
                     max_tokens: int = 1000) -> str:
        """
        Синхронная генерация текста на основе контекста
        """
        # Преобразуем контекст в промпт
        prompt = self._convert_messages_to_prompt(context)
        
        # Создаем уникальный ID для запроса
        request_id = id(prompt)
        
        logger.info(f"Создан запрос {request_id} для обработки")
        
        # Создаем очередь для ответа
        response_queue = queue.Queue()
        self._response_queues[request_id] = response_queue
        
        # Отправляем запрос в очередь
        self._request_queue.put({
            'id': request_id,
            'prompt': prompt,
            'temperature': temperature,
            'max_tokens': max_tokens
        })
        
        logger.info(f"Запрос {request_id} отправлен в очередь, ожидаем ответ")
        
        # Ждем ответ
        try:
            response = response_queue.get(block=True, timeout=self.timeout)
            logger.info(f"Получен ответ для запроса {request_id}")
            return response
        except queue.Empty:
            logger.error(f'Таймаут ожидания ответа после {self.timeout} секунд')
            # Удаляем очередь ответа, так как она больше не нужна
            if request_id in self._response_queues:
                del self._response_queues[request_id]
            return 'Превышено время ожидания ответа от модели'
    
    async def generate_chat_response(self, 
                                   messages: List[Dict[str, str]], 
                                   temperature: float = 0.7, 
                                   max_tokens: int = 1000) -> str:
        """
        Асинхронная генерация ответа на основе истории сообщений
        """
        logger.info(f"Запрос generate_chat_response с {len(messages)} сообщениями")
        
        # Используем синхронный метод в отдельном потоке через executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_text,
            messages,
            temperature,
            max_tokens
        )
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Преобразование истории сообщений в единый промпт
        """
        if not messages:
            return "Привет! Чем я могу помочь?"
            
        system_prompt = ""
        user_messages = []
        assistant_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg["role"] == "user":
                user_messages.append(msg["content"])
            elif msg["role"] == "assistant":
                assistant_messages.append(msg["content"])
        
        # Строим диалоговый контекст
        formatted_prompt = ""
        
        # Добавляем системный промпт
        if system_prompt:
            formatted_prompt = f"{system_prompt}\n\n"
        
        # Добавляем историю диалога (последние сообщения)
        if len(user_messages) > 1 and len(assistant_messages) > 0:
            # Добавляем контекст диалога
            for i in range(len(user_messages) - 1):
                if i < len(assistant_messages):
                    formatted_prompt += f"User: {user_messages[i]}\nAssistant: {assistant_messages[i]}\n\n"
        
        # Добавляем последний запрос пользователя
        if user_messages:
            if formatted_prompt:
                formatted_prompt += f"User: {user_messages[-1]}\nAssistant: "
            else:
                formatted_prompt = user_messages[-1]
        
        logger.info(f"Сформирован промпт длиной {len(formatted_prompt)} символов")
        return formatted_prompt
    
    def close(self):
        """
        Закрывает клиент и останавливает фоновый поток
        """
        logger.info("Закрытие клиента Mistral API")
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        logger.info("Клиент Mistral API закрыт") 