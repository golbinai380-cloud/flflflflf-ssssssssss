#!/usr/bin/env python3
"""
🚀 ЕДИНЫЙ LAUNCHER ДЛЯ TELEGRAM MINI APP
Запускает API сервер и Telegram бота одновременно
"""

import os
import sys
import asyncio
import subprocess
import signal
import logging
import threading
from pathlib import Path
from typing import List, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LAUNCHER")

# Цвета для консоли
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Глобальные переменные для процессов
processes: List[subprocess.Popen] = []
running = True


def print_banner():
    """Выводит красивый баннер"""
    banner = f"""
{Colors.OKCYAN}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        🎁 TELEGRAM MINI APP - GIFTS MARKET 🎁            ║
║                                                           ║
║              Единый запуск всех сервисов                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.ENDC}
"""
    print(banner)


def check_python_version():
    """Проверяет версию Python"""
    if sys.version_info < (3, 8):
        logger.error(f"{Colors.FAIL}❌ Требуется Python 3.8 или выше!{Colors.ENDC}")
        logger.error(f"   Текущая версия: {sys.version}")
        sys.exit(1)
    logger.info(f"{Colors.OKGREEN}✅ Python версия: {sys.version.split()[0]}{Colors.ENDC}")


def check_env_file():
    """Проверяет наличие .env файла"""
    env_path = Path("backend/.env")
    
    if not env_path.exists():
        logger.error(f"{Colors.FAIL}❌ Файл backend/.env не найден!{Colors.ENDC}")
        logger.error(f"   Создайте его на основе backend/.env.example")
        logger.error(f"   Команда: cp backend/.env.example backend/.env")
        sys.exit(1)
    
    logger.info(f"{Colors.OKGREEN}✅ Файл .env найден{Colors.ENDC}")
    
    # Проверяем критические переменные
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    required_vars = {
        "TELEGRAM_BOT_TOKEN": "Токен Telegram бота",
        "ADMIN_ID": "ID администратора",
        "API_HOST": "Хост API сервера",
        "API_PORT": "Порт API сервера",
    }
    
    missing = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value == f"your_{var.lower()}_here":
            missing.append(f"{var} ({description})")
    
    if missing:
        logger.error(f"{Colors.FAIL}❌ Не заполнены переменные в .env:{Colors.ENDC}")
        for var in missing:
            logger.error(f"   - {var}")
        logger.error(f"\n   Откройте backend/.env и заполните эти переменные")
        sys.exit(1)
    
    logger.info(f"{Colors.OKGREEN}✅ Все критические переменные заполнены{Colors.ENDC}")


def check_dependencies():
    """Проверяет установленные зависимости"""
    logger.info("🔍 Проверка зависимостей...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "aiogram",
        "aiohttp",
        "python-dotenv",
        "pydantic",
        "sqlalchemy",
        "aiosqlite",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        logger.warning(f"{Colors.WARNING}⚠️  Не установлены пакеты:{Colors.ENDC}")
        for pkg in missing:
            logger.warning(f"   - {pkg}")
        logger.info(f"\n{Colors.OKCYAN}📦 Устанавливаю зависимости...{Colors.ENDC}")
        
        try:
            # ВАЖНО: НЕ обновляем системный pip - это вызывает конфликты с pyOpenSSL
            # Просто устанавливаем зависимости напрямую
            logger.info("Установка зависимостей...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"
            ], env={**os.environ, 'PYTHONWARNINGS': 'ignore'})
            logger.info(f"{Colors.OKGREEN}✅ Зависимости установлены{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            logger.error(f"{Colors.FAIL}❌ Ошибка установки зависимостей: {e}{Colors.ENDC}")
            logger.error(f"\n{Colors.WARNING}💡 Попробуйте установить зависимости вручную:{Colors.ENDC}")
            logger.error(f"   python3 -m pip install --user -r backend/requirements.txt")
            logger.error(f"\n{Colors.WARNING}Или используйте виртуальное окружение:{Colors.ENDC}")
            logger.error(f"   python3 -m venv .venv")
            logger.error(f"   source .venv/bin/activate  # Linux/Mac")
            logger.error(f"   .venv\\Scripts\\activate  # Windows")
            logger.error(f"   pip install -r backend/requirements.txt")
            sys.exit(1)
    else:
        logger.info(f"{Colors.OKGREEN}✅ Все зависимости установлены{Colors.ENDC}")


def start_api_server():
    """Запускает API сервер"""
    logger.info(f"{Colors.OKCYAN}🚀 Запуск API сервера...{Colors.ENDC}")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "backend/run_api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        processes.append(process)
        logger.info(f"{Colors.OKGREEN}✅ API сервер запущен (PID: {process.pid}){Colors.ENDC}")
        return process
    except Exception as e:
        logger.error(f"{Colors.FAIL}❌ Ошибка запуска API: {e}{Colors.ENDC}")
        return None


def start_telegram_bot():
    """Запускает Telegram бота"""
    logger.info(f"{Colors.OKCYAN}🤖 Запуск Telegram бота...{Colors.ENDC}")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "backend/run_bot.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        processes.append(process)
        logger.info(f"{Colors.OKGREEN}✅ Telegram бот запущен (PID: {process.pid}){Colors.ENDC}")
        return process
    except Exception as e:
        logger.error(f"{Colors.FAIL}❌ Ошибка запуска бота: {e}{Colors.ENDC}")
        return None


def monitor_process(process: subprocess.Popen, name: str):
    """Мониторит вывод процесса в реальном времени"""
    try:
        while True:
            line = process.stdout.readline()
            if not line:
                # Процесс завершился
                break
            # Выводим строку с префиксом
            line = line.rstrip()
            if line:
                if name == "API":
                    print(f"{Colors.OKBLUE}[API]{Colors.ENDC} {line}")
                else:
                    print(f"{Colors.OKCYAN}[BOT]{Colors.ENDC} {line}")
                sys.stdout.flush()
    except Exception as e:
        logger.error(f"Ошибка мониторинга {name}: {e}")


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    global running
    logger.info(f"\n{Colors.WARNING}⏹️  Получен сигнал остановки...{Colors.ENDC}")
    running = False
    stop_all_processes()


def stop_all_processes():
    """Останавливает все запущенные процессы"""
    logger.info(f"{Colors.WARNING}🛑 Остановка всех сервисов...{Colors.ENDC}")
    
    for process in processes:
        try:
            if process.poll() is None:  # Процесс еще работает
                process.terminate()
                try:
                    process.wait(timeout=5)
                    logger.info(f"✅ Процесс {process.pid} остановлен")
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠️  Принудительная остановка процесса {process.pid}")
                    process.kill()
        except Exception as e:
            logger.error(f"Ошибка остановки процесса: {e}")
    
    logger.info(f"{Colors.OKGREEN}✅ Все сервисы остановлены{Colors.ENDC}")


def print_info():
    """Выводит информацию о запущенных сервисах"""
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = os.getenv("API_PORT", "8000")
    
    display_host = "localhost" if api_host == "0.0.0.0" else api_host
    
    info = f"""
{Colors.OKGREEN}╔═══════════════════════════════════════════════════════════╗
║                  🎉 ВСЕ СЕРВИСЫ ЗАПУЩЕНЫ! 🎉             ║
╚═══════════════════════════════════════════════════════════╝{Colors.ENDC}

{Colors.OKCYAN}📡 API Сервер:{Colors.ENDC}
   • URL: http://{display_host}:{api_port}
   • Документация: http://{display_host}:{api_port}/docs
   • Статус: http://{display_host}:{api_port}/api/health

{Colors.OKCYAN}🤖 Telegram Bot:{Colors.ENDC}
   • Статус: Активен и слушает сообщения
   • Команда: /start в боте

{Colors.OKCYAN}🌐 Frontend:{Colors.ENDC}
   • Главная: http://{display_host}:{api_port}/
   • Маркет: http://{display_host}:{api_port}/market/

{Colors.OKBLUE}📋 ЛОГИ:{Colors.ENDC}
   • {Colors.OKBLUE}[API]{Colors.ENDC} - логи API сервера
   • {Colors.OKCYAN}[BOT]{Colors.ENDC} - логи Telegram бота

{Colors.WARNING}⚠️  Для остановки нажмите Ctrl+C{Colors.ENDC}

{Colors.BOLD}{'='*60}{Colors.ENDC}
"""
    print(info)


async def main():
    """Главная функция"""
    global running
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Баннер
        print_banner()
        
        # Проверки
        check_python_version()
        check_env_file()
        check_dependencies()
        
        # Инициализируем базу данных
        logger.info(f"\n{Colors.OKCYAN}🔧 Инициализация базы данных...{Colors.ENDC}")
        try:
            result = subprocess.run(
                [sys.executable, "backend/init_database.py"],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"{Colors.OKGREEN}✅ База данных инициализирована{Colors.ENDC}")
                # Выводим вывод скрипта
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        logger.info(f"   {line}")
            else:
                logger.warning(f"{Colors.WARNING}⚠️  Ошибка инициализации базы данных{Colors.ENDC}")
                if result.stderr:
                    logger.warning(result.stderr)
        except Exception as e:
            logger.warning(f"{Colors.WARNING}⚠️  Не удалось инициализировать базу данных: {e}{Colors.ENDC}")
        
        logger.info(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
        logger.info(f"{Colors.BOLD}ЗАПУСК СЕРВИСОВ{Colors.ENDC}")
        logger.info(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
        
        # Запускаем сервисы
        api_process = start_api_server()
        if not api_process:
            logger.error(f"{Colors.FAIL}❌ Не удалось запустить API сервер{Colors.ENDC}")
            sys.exit(1)
        
        await asyncio.sleep(2)  # Даем API время на запуск
        
        bot_process = start_telegram_bot()
        if not bot_process:
            logger.error(f"{Colors.FAIL}❌ Не удалось запустить Telegram бота{Colors.ENDC}")
            stop_all_processes()
            sys.exit(1)
        
        await asyncio.sleep(2)  # Даем боту время на запуск
        
        # Проверяем, что процессы запустились
        if api_process.poll() is not None:
            logger.error(f"{Colors.FAIL}❌ API сервер не запустился{Colors.ENDC}")
            stop_all_processes()
            sys.exit(1)
        
        if bot_process.poll() is not None:
            logger.error(f"{Colors.FAIL}❌ Telegram бот не запустился{Colors.ENDC}")
            stop_all_processes()
            sys.exit(1)
        
        # Запускаем мониторинг логов в отдельных потоках
        api_thread = threading.Thread(target=monitor_process, args=(api_process, "API"), daemon=True)
        bot_thread = threading.Thread(target=monitor_process, args=(bot_process, "BOT"), daemon=True)
        
        api_thread.start()
        bot_thread.start()
        
        # Показываем информацию
        print_info()
        
        # Мониторим процессы
        while running:
            # Проверяем, что процессы еще работают
            if api_process.poll() is not None:
                logger.error(f"\n{Colors.FAIL}❌ API сервер остановился!{Colors.ENDC}")
                running = False
                break
            
            if bot_process.poll() is not None:
                logger.error(f"\n{Colors.FAIL}❌ Telegram бот остановился!{Colors.ENDC}")
                running = False
                break
            
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info(f"\n{Colors.WARNING}⏹️  Остановка по запросу пользователя{Colors.ENDC}")
    except Exception as e:
        logger.error(f"{Colors.FAIL}❌ Критическая ошибка: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
    finally:
        stop_all_processes()
        logger.info(f"\n{Colors.OKGREEN}👋 До свидания!{Colors.ENDC}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sys.exit(1)
