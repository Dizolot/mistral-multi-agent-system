import aiohttp
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mistral_client')

class MistralClient:
    """
    Асинхронный клиент для взаимодействия с API Mistral
    """
    
    def __init__(self, base_url: str, timeout: int = 180):
        """
        Инициализация клиента Mistral API
        
        Args:
            base_url: Базовый URL API Mistral
            timeout: Таймаут запросов в секундах
        """
        self.base_url = base_url
        self.timeout = timeout
        logger.info(f'Инициализирован клиент Mistral API с базовым URL: {base_url}')
        
    async def generate_response(self, prompt: str, 
                               temperature: float = 0.7, 
                               max_tokens: int = 1000) -> str:
        """
        Генерация ответа на основе промпта
        
        Args:
            prompt: Текст запроса
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе
            
        Returns:
            Сгенерированный ответ
        """
        try:
            # Формируем запрос в формате llama.cpp
            payload = {
                'prompt': f'<s>[INST] {prompt} [/INST]',
                'n_predict': max_tokens,
                'temperature': temperature,
                'top_p': 0.95,
                'stop': ["</s>", "[INST]"],
                'stream': False
            }
            
            logger.info(f'Отправка запроса на {self.base_url}/completion, длина промпта: {len(prompt)} символов')
            logger.info(f'Payload: {json.dumps(payload)}')
            
            async with aiohttp.ClientSession() as session:
                try:
                    logger.info(f'Начало отправки запроса к {self.base_url}/completion')
                    async with session.post(
                        f'{self.base_url}/completion',
                        json=payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f'Ошибка при отправке запроса: {response.status}, {error_text}')
                            return f'Произошла ошибка при отправке запроса (код {response.status}). Попробуйте еще раз.'
                        
                        result = await response.json()
                        logger.info(f'Получен ответ: {json.dumps(result)}')
                        
                        # Извлекаем текст ответа
                        if 'content' in result:
                            content = result['content'].strip()
                            logger.info(f'Получен ответ длиной {len(content)} символов')
                            return content
                        else:
                            logger.error(f'Неожиданный формат ответа: {result}')
                            return 'Получен неожиданный формат ответа от модели.'
                except aiohttp.ClientError as e:
                    logger.error(f'Ошибка клиента aiohttp: {str(e)}')
                    return f'Произошла ошибка при подключении к серверу: {str(e)}'
                    
        except asyncio.TimeoutError:
            logger.error(f'Таймаут запроса после {self.timeout} секунд')
            return 'Запрос занял слишком много времени. Пожалуйста, попробуйте еще раз или упростите запрос.'
            
        except Exception as e:
            logger.error(f'Ошибка при генерации ответа: {str(e)}')
            import traceback
            logger.error(f'Трассировка: {traceback.format_exc()}')
            return f'Произошла ошибка: {str(e)}'
    
    async def generate_chat_response(self, 
                                    messages: List[Dict[str, str]], 
                                    temperature: float = 0.7, 
                                    max_tokens: int = 1000) -> str:
        """
        Генерация ответа на основе истории сообщений
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}, ...]
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе
            
        Returns:
            Сгенерированный ответ
        """
        # Для llama.cpp мы преобразуем историю сообщений в один промпт
        prompt = self._convert_messages_to_prompt(messages)
        return await self.generate_response(prompt, temperature, max_tokens)
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Преобразование истории сообщений в единый промпт для llama.cpp
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}, ...]
            
        Returns:
            Промпт для модели
        """
        if not messages:
            return "Привет! Чем я могу помочь?"
            
        # Извлекаем системный промпт, если он есть
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
        
        # Строим промпт для Mistral в формате llama.cpp
        formatted_prompt = ""
        
        # Добавляем системный промпт в начало, если он есть
        if system_prompt:
            formatted_prompt = f"{system_prompt}\n\n"
            
        # Добавляем последнее сообщение пользователя
        if user_messages:
            formatted_prompt += user_messages[-1]
            
        logger.info(f"Сформирован промпт длиной {len(formatted_prompt)} символов")
        return formatted_prompt 