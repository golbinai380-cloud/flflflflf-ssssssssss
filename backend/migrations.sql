-- Миграции для Gifts Market Database
-- Выполните этот файл если база данных уже существует

-- 1. Добавление phone_code_hash в telegram_sessions
-- (нужно для корректной верификации кода)
ALTER TABLE telegram_sessions ADD COLUMN IF NOT EXISTS phone_code_hash VARCHAR;

-- 2. Добавление gift_slug в gift_transfers  
-- (нужно для работы с Telegram Gift API)
ALTER TABLE gift_transfers ADD COLUMN IF NOT EXISTS gift_slug VARCHAR;

-- Примечание: SQLite не поддерживает IF NOT EXISTS в ALTER TABLE
-- Для SQLite используйте отдельные скрипты или проверяйте наличие колонки перед добавлением
