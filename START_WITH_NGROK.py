"""
Запуск всех сервисов с ngrok туннелем для Telegram Mini App
"""
import subprocess
import sys
import time
import os
import signal
from pathlib import Path

# Цвета для консоли
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_colored(text, color):
    print(f"{color}{text}{Colors.RESET}")

def check_ngrok():
    """Проверяет установлен ли ngrok"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_colored(f"✅ ngrok установлен: {result.stdout.strip()}", Colors.GREEN)
            return True
    except FileNotFoundError:
        pass
    
    print_colored("❌ ngrok не установлен!", Colors.RED)
    print_colored("\nУстановите ngrok:", Colors.YELLOW)
    print("1. Скачайте: https://ngrok.com/download")
    print("2. Распакуйте в любую папку")
    print("3. Добавьте в PATH или положите ngrok.exe в папку проекта")
    print("\nИли используйте chocolatey: choco install ngrok")
    return False

def start_ngrok(port=8000):
    """Запускает ngrok туннель"""
    print_colored(f"\n🌐 Запуск ngrok туннеля на порт {port}...", Colors.BLUE)
    
    # Запускаем ngrok в фоне
    ngrok_process = subprocess.Popen(
        ['ngrok', 'http', str(port), '--log=stdout'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Ждем пока ngrok запустится
    time.sleep(3)
    
    # Получаем публичный URL
    try:
        import requests
        response = requests.get('http://localhost:4040/api/tunnels')
        tunnels = response.json()['tunnels']
        
        if tunnels:
            public_url = tunnels[0]['public_url']
            print_colored(f"✅ ngrok туннель создан: {public_url}", Colors.GREEN)
            print_colored(f"📊 ngrok dashboard: http://localhost:4040", Colors.BLUE)
            return ngrok_process, public_url
    except Exception as e:
        print_colored(f"⚠️  Не удалось получить URL через API: {e}", Colors.YELLOW)
        print_colored("Откройте http://localhost:4040 чтобы увидеть URL", Colors.YELLOW)
    
    return ngrok_process, None

def update_env_file(ngrok_url):
    """Обновляет WEB_APP_URL в .env файле"""
    env_path = Path(__file__).parent / "backend" / ".env"
    
    if not env_path.exists():
        print_colored("❌ Файл .env не найден!", Colors.RED)
        return False
    
    # Читаем .env
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Обновляем WEB_APP_URL
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('WEB_APP_URL='):
            lines[i] = f'WEB_APP_URL={ngrok_url}\n'
            updated = True
            break
    
    # Записываем обратно
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    if updated:
        print_colored(f"✅ WEB_APP_URL обновлен в .env: {ngrok_url}", Colors.GREEN)
    else:
        print_colored("⚠️  WEB_APP_URL не найден в .env", Colors.YELLOW)
    
    return True

def start_services():
    """Запускает API и Bot"""
    backend_dir = Path(__file__).parent / "backend"
    
    print_colored("\n🚀 Запуск API сервера...", Colors.BLUE)
    api_process = subprocess.Popen(
        [sys.executable, "run_api.py"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    time.sleep(3)
    
    print_colored("🤖 Запуск Telegram бота...", Colors.BLUE)
    bot_process = subprocess.Popen(
        [sys.executable, "run_bot.py"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    return api_process, bot_process

def main():
    print_colored("=" * 60, Colors.BLUE)
    print_colored("  Telegram Mini App - Запуск с ngrok", Colors.BLUE)
    print_colored("=" * 60, Colors.BLUE)
    
    # Проверяем ngrok
    if not check_ngrok():
        sys.exit(1)
    
    # Проверяем requests для получения ngrok URL
    try:
        import requests
    except ImportError:
        print_colored("\n⚠️  Установите requests: pip install requests", Colors.YELLOW)
    
    processes = []
    
    try:
        # Запускаем ngrok
        ngrok_process, ngrok_url = start_ngrok(8000)
        processes.append(('ngrok', ngrok_process))
        
        if ngrok_url:
            # Обновляем .env
            update_env_file(ngrok_url)
            
            print_colored("\n" + "=" * 60, Colors.GREEN)
            print_colored(f"  🌐 Ваш Mini App доступен по адресу:", Colors.GREEN)
            print_colored(f"  {ngrok_url}", Colors.GREEN)
            print_colored("=" * 60, Colors.GREEN)
            print_colored("\n📝 Обновите URL в BotFather:", Colors.YELLOW)
            print_colored(f"   /setmenubutton -> @GiftsMarketAppBot -> {ngrok_url}", Colors.YELLOW)
        else:
            print_colored("\n⚠️  Откройте http://localhost:4040 чтобы увидеть ngrok URL", Colors.YELLOW)
        
        # Запускаем сервисы
        api_process, bot_process = start_services()
        processes.append(('API', api_process))
        processes.append(('Bot', bot_process))
        
        print_colored("\n✅ Все сервисы запущены!", Colors.GREEN)
        print_colored("\n📊 Мониторинг:", Colors.BLUE)
        print_colored("   - ngrok dashboard: http://localhost:4040", Colors.BLUE)
        print_colored("   - API docs: http://localhost:8000/docs", Colors.BLUE)
        print_colored("\n⏹️  Нажмите Ctrl+C для остановки", Colors.YELLOW)
        
        # Ждем
        while True:
            time.sleep(1)
            
            # Проверяем что процессы живы
            for name, proc in processes:
                if proc.poll() is not None:
                    print_colored(f"\n❌ {name} остановлен!", Colors.RED)
                    raise KeyboardInterrupt
    
    except KeyboardInterrupt:
        print_colored("\n\n⏹️  Остановка сервисов...", Colors.YELLOW)
        
        # Останавливаем все процессы
        for name, proc in processes:
            try:
                print_colored(f"   Остановка {name}...", Colors.YELLOW)
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        
        print_colored("\n✅ Все сервисы остановлены", Colors.GREEN)

if __name__ == "__main__":
    main()
