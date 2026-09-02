#!/usr/bin/env python3
"""
GUI Launcher для macOS
Простой launcher без зависимостей от AppKit
"""

import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Настройка логирования при запуске из Finder"""
    try:
        # Всегда перенаправляем логи в файл
        log_dir = Path.home() / "Library" / "Logs" / "VPNServerManager"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
        
        # Открываем в режиме append
        log_handle = open(log_file, 'a', buffering=1)
        sys.stdout = log_handle
        sys.stderr = log_handle
        return True
    except Exception as e:
        # Если не можем создать лог, продолжаем без него
        return False

if __name__ == '__main__':
    # Настраиваем логирование
    setup_logging()
    
    print("=" * 60)
    print("VPN Server Manager - Starting")
    print(f"📍 Working directory: {os.getcwd()}")
    print(f"🐍 Python: {sys.executable}")
    print(f"📦 sys.argv: {sys.argv}")
    print(f"🕐 Started at: {__import__('datetime').datetime.now()}")
    print("=" * 60)
    
    # Добавляем --desktop к аргументам, если его нет
    if '--desktop' not in sys.argv:
        sys.argv.append('--desktop')
        print("✅ Added --desktop flag")
    
    try:
        print("📦 Importing run module...")
        import run
        print("✅ Run module imported")
        print("🚀 Starting main()...")
        run.main()
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Пауза чтобы увидеть ошибку
        import time
        time.sleep(10)
        sys.exit(1)

