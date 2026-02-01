"""
Миграция: добавление поля phone_code_hash в таблицу telegram_sessions
"""
import sqlite3
import os

# Путь к БД
db_path = os.path.join(os.path.dirname(__file__), 'database.db')

print(f"Подключение к БД: {db_path}")

# Подключаемся к БД
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Проверяем, существует ли уже колонка
    cursor.execute("PRAGMA table_info(telegram_sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'phone_code_hash' in columns:
        print("✅ Колонка phone_code_hash уже существует")
    else:
        # Добавляем колонку
        print("Добавление колонки phone_code_hash...")
        cursor.execute("ALTER TABLE telegram_sessions ADD COLUMN phone_code_hash VARCHAR")
        conn.commit()
        print("✅ Колонка phone_code_hash успешно добавлена")
    
except Exception as e:
    print(f"❌ Ошибка миграции: {e}")
    conn.rollback()
finally:
    conn.close()
    print("Соединение закрыто")
