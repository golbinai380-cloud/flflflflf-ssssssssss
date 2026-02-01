#!/bin/bash

# Простой запуск всего бэкенда в одном процессе

cd "$(dirname "$0")"

echo "🚀 Запуск Telegram Mini App Backend (Single Process)"
echo "=================================================="

# Активируем виртуальное окружение если есть
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Виртуальное окружение активировано"
fi

# Переходим в backend
cd backend

# Запускаем единый файл
python3 run_single.py
