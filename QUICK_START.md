# 🚀 Quick Start Guide

## Быстрый запуск системы

### 1. Установка зависимостей

```bash
cd site-clone/backend
pip install -r requirements.txt
```

### 2. Проверка конфигурации

Убедитесь что `.env` файл заполнен:
```bash
cat backend/.env
```

Должны быть заполнены:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_APP_ID`
- `TELEGRAM_APP_HASH`
- `ADMIN_ID`
- `BOT_USERNAME`

### 3. Запуск системы

**Linux/Mac:**
```bash
chmod +x START_ALL.sh
./START_ALL.sh
```

**Windows:**
```bash
python START_ALL.py
```

**Или вручную:**
```bash
# Терминал 1 - Backend API
cd site-clone/backend
python run_api.py

# Терминал 2 - Telegram Bot
cd site-clone/backend
python run_bot.py
```

### 4. Проверка работы

1. **API:** http://localhost:8000/docs
2. **Health:** http://localhost:8000/api/health
3. **Main App:** http://localhost:8000/

### 5. Первый запуск

1. Откройте бота в Telegram: `@GiftsMarketAppBot`
2. Нажмите `/start`
3. Нажмите "🎁 Открыть Маркет"
4. Miniapp откроется

### 6. Добавление воркера (для админа)

1. Зайдите в профиль в miniapp
2. Нажмите "👑 Admin Panel"
3. Перейдите в таб "Воркеры"
4. Нажмите "Добавить воркера"
5. Введите Telegram ID воркера

### 7. Тестирование Worker Panel

1. Зайдите в профиль как воркер
2. Нажмите "👷 Worker Panel"
3. Просмотрите статистику и пользователей

### 8. Тестирование рассылки

1. Admin Panel → Рассылка
2. Введите текст
3. Нажмите "Предпросмотр"
4. Проверьте сообщение в боте
5. Нажмите "Отправить всем"

---

## 🔍 Troubleshooting

### Ошибка: "Missing initData"
- Убедитесь что открываете через Telegram WebApp
- Проверьте что бот запущен

### Ошибка: "Invalid token"
- Проверьте `TELEGRAM_BOT_TOKEN` в `.env`
- Перезапустите бота

### Панели не видны
- Проверьте что пользователь добавлен как воркер/админ
- Проверьте `ADMIN_ID` в `.env`

### GeoIP не работает
- Проверьте интернет соединение
- API ip-api.com может быть недоступен
- Система продолжит работать без геолокации

---

## 📚 Дополнительная информация

- **Полная документация:** `ВСЕ_ЭТАПЫ_ЗАВЕРШЕНЫ.md`
- **Изменения фронтенда:** `ИЗМЕНЕНИЯ_ФРОНТЕНДА.md`
- **Тестирование:** `ТЕСТИРОВАНИЕ.md`
