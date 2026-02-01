#!/bin/bash

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║        🎁 TELEGRAM MINI APP - GIFTS MARKET 🎁            ║"
echo "║                                                           ║"
echo "║              Единый запуск всех сервисов                  ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден!"
    echo "Установите Python 3.8+ и попробуйте снова"
    exit 1
fi

echo "✅ Python версия: $(python3 --version)"

# Проверка .env
if [ ! -f "backend/.env" ]; then
    echo "❌ Файл backend/.env не найден!"
    echo "Создайте его на основе backend/.env.example"
    exit 1
fi

echo "✅ Файл .env найден"

# Создание виртуального окружения если его нет
if [ ! -d ".venv" ]; then
    echo ""
    echo "📦 Создание виртуального окружения..."
    python3 -m venv .venv
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка создания venv"
        echo ""
        echo "Попробуйте установить python3-venv:"
        echo "  sudo apt-get install python3-venv"
        exit 1
    fi
    
    echo "✅ Виртуальное окружение создано"
fi

# Активация venv
echo ""
echo "🔄 Активация виртуального окружения..."
source .venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Ошибка активации venv"
    exit 1
fi

echo "✅ Виртуальное окружение активировано"

# Проверка и установка зависимостей
echo ""
echo "🔍 Проверка зависимостей..."

# Проверяем наличие основных пакетов В ВИРТУАЛЬНОМ ОКРУЖЕНИИ
python -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Установка зависимостей..."
    
    # ВАЖНО: Используем pip из venv, НЕ системный pip
    # Это избегает конфликтов с системным pyOpenSSL
    .venv/bin/python -m pip install --upgrade pip setuptools wheel -q
    
    # Устанавливаем зависимости через pip из venv
    .venv/bin/pip install -r backend/requirements.txt
    
    if [ $? -eq 0 ]; then
        echo "✅ Зависимости установлены"
    else
        echo "❌ Ошибка установки зависимостей"
        exit 1
    fi
else
    echo "✅ Зависимости уже установлены"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🚀 ЗАПУСК СЕРВЕРА"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Инициализируем базу данных
echo "🔧 Инициализация базы данных..."
python backend/init_database.py
if [ $? -eq 0 ]; then
    echo "✅ База данных инициализирована"
else
    echo "⚠️  Ошибка инициализации базы данных (продолжаем запуск)"
fi

echo ""

# Запуск приложения
python START_ALL.py

# Если сервер остановился
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "⏹️  Сервер остановлен"
echo "═══════════════════════════════════════════════════════════"
echo ""
