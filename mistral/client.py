import asyncio
import json
import logging
import os
import httpx
import nest_asyncio

# Применяем патч для возможности вложенных циклов событий
nest_asyncio.apply()

def generate_text(self, context: List[Dict[str, str]], 
                 temperature: float = 0.7,
                 max_tokens: int = 1000) -> str:
    """
    Синхронная генерация текста на основе контекста
    """
    try:
        # Используем текущий цикл событий, если он существует
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Если цикла нет, создаем новый
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Выполняем асинхронный запрос в синхронном контексте
        response = loop.run_until_complete(
            self.generate_chat_response(
                messages=context,
                temperature=temperature,
                max_tokens=max_tokens
            )
        )
        
        # Не закрываем цикл событий, так как он может использоваться другими компонентами
        
        return response
    except Exception as e:
        logging.error(f"Ошибка в методе generate_text: {str(e)}")
        return f"Произошла ошибка при обработке запроса: {str(e)}" 