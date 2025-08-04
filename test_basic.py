#!/usr/bin/env python3
"""
Базовые тесты для VPN Server Manager без GUI
"""

import os
import sys
import json
from pathlib import Path

def test_config():
    """Тест конфигурации"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        assert 'app_info' in config
        assert 'service_urls' in config
        assert 'secret_pin' in config
        print("✅ Конфигурация загружается корректно")
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def test_imports():
    """Тест импорта модулей"""
    try:
        import app
        print("✅ app.py импортируется успешно")
        
        import pin_auth
        print("✅ pin_auth.py импортируется успешно")
        
        import decrypt_tool
        print("✅ decrypt_tool.py импортируется успешно")
        
        import build_macos
        print("✅ build_macos.py импортируется успешно")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_files():
    """Тест наличия необходимых файлов"""
    required_files = [
        'app.py',
        'config.json',
        'requirements.txt',
        'README.md',
        'CHANGELOG.md',
        'LICENSE',
        '.gitignore',
        'static/images/icon.png',
        'templates/index.html',
        'data/hints.json'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы: {missing_files}")
        return False
    else:
        print("✅ Все необходимые файлы присутствуют")
        return True

def test_env():
    """Тест переменных окружения"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        secret_key = os.environ.get('SECRET_KEY')
        if secret_key:
            print("✅ SECRET_KEY найден")
            return True
        else:
            print("⚠️ SECRET_KEY не найден (но это нормально для CI)")
            return True
    except Exception as e:
        print(f"❌ Ошибка переменных окружения: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 Запуск базовых тестов VPN Server Manager...")
    print("=" * 50)
    
    tests = [
        test_files,
        test_config,
        test_imports,
        test_env
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Результаты: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("❌ Некоторые тесты не пройдены")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 