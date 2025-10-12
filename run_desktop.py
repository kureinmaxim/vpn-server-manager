#!/usr/bin/env python3
"""
Точка входа для desktop-версии VPN Server Manager
Автоматически запускает приложение в режиме --desktop
"""

import sys
import os

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Добавляем --desktop к аргументам, если его нет
if '--desktop' not in sys.argv:
    sys.argv.append('--desktop')

# Импортируем и запускаем основной модуль
if __name__ == '__main__':
    import run
    run.main()

