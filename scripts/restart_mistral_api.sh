#!/bin/bash
# Скрипт для перезапуска Mistral API (llama.cpp server)

# Настройки
SERVER_HOST="139.59.241.176"
SERVER_PORT="8080"
SERVER_USER="root"
SSH_KEY="${HOME}/.ssh/id_rsa"
RESTART_COMMAND="sudo systemctl restart mistral-api || ( pkill -f 'llama-server' && cd /opt/mistral && ./run_mistral_server.sh )"
CHECK_COMMAND="curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/v1/models"

# Проверяем локальную доступность перед рестартом
function check_local_api() {
  echo "Проверка локальной доступности Mistral API..."
  status_code=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_HOST}:${SERVER_PORT}/v1/models)
  
  if [ "$status_code" = "200" ]; then
    echo "API доступен (код ответа: $status_code). Перезапуск не требуется."
    return 0
  else
    echo "API недоступен или вернул ошибку (код ответа: $status_code)."
    return 1
  fi
}

# Перезапуск API через SSH
function restart_api() {
  echo "Выполняем перезапуск Mistral API на сервере ${SERVER_HOST}..."
  
  # Проверяем наличие ключа SSH
  if [ ! -f "$SSH_KEY" ]; then
    echo "Ошибка: SSH ключ не найден по пути $SSH_KEY"
    echo "Пожалуйста, укажите корректный путь к SSH ключу в переменной SSH_KEY."
    return 1
  fi
  
  # Проверяем успешность подключения по SSH (без выполнения команды)
  ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_HOST} exit &>/dev/null
  if [ $? -ne 0 ]; then
    echo "Ошибка: Не удалось подключиться к серверу ${SERVER_HOST} по SSH."
    echo "Проверьте сервер, учетные данные и сетевое подключение."
    return 1
  fi
  
  # Выполняем перезапуск
  echo "Отправка команды перезапуска..."
  ssh -i "$SSH_KEY" ${SERVER_USER}@${SERVER_HOST} "${RESTART_COMMAND}" || {
    echo "Ошибка при выполнении команды перезапуска."
    return 1
  }
  
  # Ожидаем запуск сервиса
  echo "Ожидаем запуск сервиса (до 30 секунд)..."
  for i in {1..30}; do
    echo -n "."
    sleep 1
    
    # Проверяем статус API с сервера
    status=$(ssh -i "$SSH_KEY" ${SERVER_USER}@${SERVER_HOST} "${CHECK_COMMAND}" 2>/dev/null || echo "error")
    
    if [ "$status" = "200" ]; then
      echo
      echo "Сервис успешно запущен на сервере (проверка на сервере)."
      break
    fi
    
    # На всякий случай проверяем и локально
    local_status=$(curl -s -o /dev/null -w "%{http_code}" http://${SERVER_HOST}:${SERVER_PORT}/v1/models 2>/dev/null || echo "error")
    if [ "$local_status" = "200" ]; then
      echo
      echo "Сервис успешно запущен (локальная проверка)."
      break
    fi
    
    # Если прошло 30 секунд и сервис не запустился
    if [ $i -eq 30 ]; then
      echo
      echo "Превышено время ожидания запуска сервиса."
      return 1
    fi
  done
  
  return 0
}

# Главная функция
function main() {
  echo "=== Утилита перезапуска Mistral API ==="
  echo "Сервер: ${SERVER_HOST}:${SERVER_PORT}"
  echo "Пользователь: ${SERVER_USER}"
  echo

  # Проверяем, нужен ли перезапуск
  if check_local_api; then
    echo "Mistral API работает нормально, перезапуск не требуется."
    exit 0
  fi

  # Выполняем перезапуск
  if restart_api; then
    echo "Перезапуск Mistral API выполнен успешно."
    
    # Финальная проверка
    if check_local_api; then
      echo "Mistral API успешно восстановлен и доступен."
      exit 0
    else
      echo "Предупреждение: Mistral API после перезапуска все еще недоступен."
      exit 1
    fi
  else
    echo "Ошибка: не удалось перезапустить Mistral API."
    exit 1
  fi
}

# Запуск основной функции
main 