# 🎁 Telegram Gifts Market

Telegram Mini App для покупки и продажи подарков.

## 🚀 Быстрый запуск

### Если возникает ошибка OpenSSL:

```bash
chmod +x ИСПРАВЛЕНИЕ_OPENSSL.sh
./ИСПРАВЛЕНИЕ_OPENSSL.sh
```

Затем:

```bash
chmod +x START_ALL.sh
./START_ALL.sh
```

### Обычный запуск (Linux/Mac):
```bash
chmod +x START_ALL.sh
./START_ALL.sh
```

### Windows:
```bash
python START_ALL.py
```

## 📋 Требования

- Python 3.8+
- Заполненный файл `backend/.env` (см. `backend/.env.example`)

## 🌐 После запуска

Сервер будет доступен по адресу:
- **Frontend**: http://localhost:8000/
- **API**: http://localhost:8000/docs
- **Telegram Bot**: Активен и слушает сообщения

## ⚙️ Конфигурация

Все настройки находятся в файле `backend/.env`:
- `TELEGRAM_BOT_TOKEN` - токен вашего бота
- `ADMIN_ID` - ваш Telegram ID
- `API_HOST` и `API_PORT` - настройки сервера

## 🐛 Решение проблем

### Ошибка OpenSSL (AttributeError: X509_V_FLAG_CB_ISSUER_CHECK)

Это конфликт системного Python с pyOpenSSL. Решение:

```bash
./ИСПРАВЛЕНИЕ_OPENSSL.sh
```

Или вручную:
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -r backend/requirements.txt
./START_ALL.sh
```

## 📝 Примечания

- Скрипт `START_ALL.sh` автоматически создаст виртуальное окружение
- Все зависимости установятся автоматически в изолированное окружение
- Для остановки нажмите `Ctrl+C`
- Виртуальное окружение избегает конфликтов с системными пакетами
"# flflflflf-ssssssssss" 
