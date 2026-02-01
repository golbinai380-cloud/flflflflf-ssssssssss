-- Добавление поля phone_code_hash в таблицу telegram_sessions
ALTER TABLE telegram_sessions ADD COLUMN phone_code_hash VARCHAR;
