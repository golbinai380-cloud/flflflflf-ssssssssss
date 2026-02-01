# Запуск с ngrok для разработки

Telegram Mini App требует HTTPS. Для локальной разработки используйте ngrok.

## Проблема ERR_QUIC_PROTOCOL_ERROR

Эта ошибка возникает когда:
- Домен недоступен по HTTPS
- SSL сертификат невалидный или истек
- Проблемы с DNS или сетью

**Решение**: Используйте ngrok для создания временного HTTPS туннеля.

## Установка ngrok

### Windows
1. Скачайте: https://ngrok.com/download
2. Распакуйте `ngrok.exe` в папку проекта или любую папку в PATH
3. (Опционально) Зарегистрируйтесь на ngrok.com и получите authtoken:
   ```
   ngrok config add-authtoken YOUR_TOKEN
   ```

### Через Chocolatey
```bash
choco install ngrok
```

### Проверка установки
```bash
ngrok version
```

## Быстрый запуск

### Вариант 1: Автоматический (рекомендуется)

```bash
# Установите requests если еще не установлен
pip install requests

# Запустите скрипт
python site-clone/START_WITH_NGROK.py
```

Скрипт автоматически:
- ✅ Запустит ngrok туннель на порт 8000
- ✅ Обновит WEB_APP_URL в .env
- ✅ Запустит API и Bot
- ✅ Покажет публичный HTTPS URL

### Вариант 2: Ручной

1. Запустите ngrok в отдельном терминале:
```bash
ngrok http 8000
```

2. Скопируйте HTTPS URL (например: `https://abc123.ngrok-free.app`)

3. Обновите `.env`:
```env
WEB_APP_URL=https://abc123.ngrok-free.app
```

4. Запустите сервисы:
```bash
python site-clone/START_ALL.py
```

## Настройка бота

После запуска обновите URL в BotFather:

```
/setmenubutton
Выберите: @GiftsMarketAppBot
Отправьте URL: https://abc123.ngrok-free.app
```

Или используйте команду для установки Web App:
```
/newapp
Выберите: @GiftsMarketAppBot
Название: Gift Market
URL: https://abc123.ngrok-free.app
```

## Мониторинг

- **ngrok dashboard**: http://localhost:4040 (все запросы в реальном времени)
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/health

## Остановка

Нажмите `Ctrl+C` для остановки всех сервисов.

## Важные примечания

⚠️ **ngrok URL меняется при каждом запуске** (бесплатная версия)
- После каждого перезапуска нужно обновлять URL в BotFather
- Для постоянного URL нужна платная подписка ngrok ($8/месяц)

✅ **Для production**:
- Используйте реальный домен с SSL сертификатом
- Настройте nginx с Let's Encrypt
- Или используйте Cloudflare для SSL

## Альтернативы ngrok

- **localtunnel**: `npm install -g localtunnel && lt --port 8000`
- **serveo**: `ssh -R 80:localhost:8000 serveo.net`
- **cloudflared**: Cloudflare Tunnel (бесплатный, постоянный URL)

## Troubleshooting

### ngrok не найден
```bash
# Проверьте PATH
where ngrok

# Или укажите полный путь
C:\path\to\ngrok.exe http 8000
```

### Ошибка "Too many connections"
Бесплатная версия ngrok ограничена. Подождите или используйте другой аккаунт.

### Mini App не открывается
1. Проверьте что ngrok работает: http://localhost:4040
2. Проверьте что API запущен: http://localhost:8000/api/health
3. Проверьте URL в BotFather
4. Очистите кеш Telegram (Settings → Advanced → Clear cache)
