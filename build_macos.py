#!/usr/bin/env python3
"""
Скрипт для сборки macOS-приложения VPN Server Manager.
Создает .app бандл и .dmg образ для распространения.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime
import sysconfig

# Основные директории и файлы проекта
PROJECT_ROOT = Path.cwd()
DIST_DIR = PROJECT_ROOT / 'dist'
BUILD_DIR = PROJECT_ROOT / 'build'
ICON_FILE = PROJECT_ROOT / 'static' / 'images' / 'icon.icns'  # Иконка в формате .icns для macOS
CONFIG_FILE = PROJECT_ROOT / 'config.json'

# Создаем директории для сборки если их нет
DIST_DIR.mkdir(exist_ok=True)
BUILD_DIR.mkdir(exist_ok=True)

# Удаляем предыдущие сборки
def cleanup_previous_builds():
    print("Очистка предыдущих сборок...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    spec_file = PROJECT_ROOT / f"VPNServerManager.spec"
    if spec_file.exists():
        print(f"Удаление старого файла .spec: {spec_file}")
        spec_file.unlink()

# Обновление даты в config.json и получение текущей версии
def update_config_and_get_version():
    """
    Читает config.json, обновляет дату сборки, сохраняет файл
    и возвращает номер текущей версии.
    """
    print("Обновление даты сборки в config.json и чтение версии...")
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Получаем версию
        version = config_data.get('app_info', {}).get('version')
        if not version:
            print("ОШИБКА: Версия не найдена в config.json.")
            return None

        # Обновляем дату
        config_data['app_info']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            
        print(f"Дата в config.json обновлена. Версия для сборки: {version}")
        return version
    except FileNotFoundError:
        print(f"ОШИБКА: {CONFIG_FILE} не найден.")
        return None
    except Exception as e:
        print(f"ОШИБКА при работе с config.json: {e}")
        return None

# Проверка наличия иконки, если нет - создаем её из PNG
def check_and_create_icns():
    if not ICON_FILE.exists():
        print("Иконка .icns не найдена. Попытка создать из PNG...")
        png_icon = PROJECT_ROOT / 'static' / 'icon.png'
        
        if not png_icon.exists():
            print("PNG иконка тоже не найдена. Будет использована стандартная иконка.")
            return False
        
        try:
            # Создаем временную директорию для iconset
            iconset_dir = PROJECT_ROOT / 'static' / 'tmp.iconset'
            iconset_dir.mkdir(exist_ok=True)
            
            # Создаем иконки разных размеров
            sizes = [16, 32, 64, 128, 256, 512, 1024]
            for size in sizes:
                size2x = size * 2
                # Генерируем обычную и @2x версии
                subprocess.call(['sips', '-z', str(size), str(size), 
                               str(png_icon), '--out', 
                               str(iconset_dir / f"icon_{size}x{size}.png")])
                                
                if size < 512:  # Только для размеров до 512
                    subprocess.call(['sips', '-z', str(size2x), str(size2x), 
                                   str(png_icon), '--out', 
                                   str(iconset_dir / f"icon_{size}x{size}@2x.png")])
            
            # Конвертируем iconset в .icns
            subprocess.call(['iconutil', '-c', 'icns', str(iconset_dir), 
                           '-o', str(ICON_FILE)])
            
            # Удаляем временную директорию
            shutil.rmtree(iconset_dir)
            
            print(f"Иконка .icns успешно создана: {ICON_FILE}")
            return True
        except Exception as e:
            print(f"Ошибка создания .icns: {e}")
            return False
    
    return True

# Создание файла README.txt с инструкциями
def create_readme():
    readme_content = """# VPN Server Manager

## Важно: Первый запуск

При первом запуске приложения может появиться предупреждение безопасности macOS о том, 
что приложение получено не из App Store. Для решения:

1. В Finder щелкните по приложению правой кнопкой мыши (или Control+клик)
2. Выберите "Открыть" в контекстном меню
3. В появившемся диалоге нажмите "Открыть"
4. После этого приложение будет запускаться без предупреждений

## Хранение данных

Приложение автоматически сохраняет все данные в вашей пользовательской директории:
~/Library/Application Support/VPNServerManager/

В этой директории хранятся:
- Файлы конфигурации
- Зашифрованные данные серверов
- Загруженные чеки и иконки

## Резервное копирование

Для создания резервной копии данных, сохраните директорию:
~/Library/Application Support/VPNServerManager/

## Проблемы с запуском

Если приложение не запускается, проверьте:
1. Наличие файла .env с ключом шифрования
2. Наличие прав доступа к директории данных

Для технической поддержки обратитесь к разработчику.
"""
    
    readme_path = DIST_DIR / "README.txt"
    with open(readme_path, "w") as f:
        f.write(readme_content)
    
    return readme_path

# Сборка основного приложения с PyInstaller
def build_app():
    app_name = "VPNServerManager"
    
    # Проверяем/создаем иконку
    has_icon = check_and_create_icns()
    
    # Определяем путь к плагинам PyQt6
    try:
        qt_plugins_path = Path(sysconfig.get_paths()["purelib"]) / "PyQt6" / "Qt6" / "plugins"
        if not qt_plugins_path.exists():
            print(f"ОШИБКА: Не удалось найти директорию с плагинами PyQt6: {qt_plugins_path}")
            sys.exit(1)
    except Exception as e:
        print(f"Критическая ошибка при поиске плагинов PyQt6: {e}")
        sys.exit(1)
    
    pyinstaller_cmd = [
        "python3", "-m", "PyInstaller",
        "--name={}".format(app_name),
        
        # --- Основные данные приложения ---
        "--add-data=static:static",
        "--add-data=templates:templates",
        "--add-data=requirements.txt:.",
        "--add-data=config.json:.",
        
        # --- Явно указываем Qt, где искать плагины ---
        "--add-data=qt.conf:.",
        f"--add-data={qt_plugins_path}:PlugIns",

        # --- Скрытые импорты (оставляем только то, что не определяется автоматически) ---
        "--hidden-import=dotenv",
        "--hidden-import=cryptography.hazmat.primitives.kdf.scrypt",


        "--onedir",
        "--windowed",  # Без консоли
        "--debug=all", # Включаем полную отладку
        "app.py"
    ]
    
    # Добавляем иконку, если она есть
    if has_icon:
        pyinstaller_cmd.insert(-1, f"--icon={ICON_FILE}")
    
    # Выполняем команду сборки
    print("Запуск PyInstaller для создания .app бандла...")
    subprocess.call(pyinstaller_cmd)
    
    # Пути к созданному .app
    app_path = DIST_DIR / f"{app_name}.app"
    
    # Копируем .env файл если он существует
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        target_resources = app_path / 'Contents' / 'Resources'
        # Убедимся, что директория существует, прежде чем копировать
        os.makedirs(target_resources, exist_ok=True)
        shutil.copy(env_file, target_resources)
        print(f"Файл .env скопирован в {target_resources}")
    else:
        print("КРИТИЧЕСКАЯ ОШИБКА: Файл .env не найден. Приложение не будет работать.")
        sys.exit(1) # Прерываем сборку, если нет ключа
    
    return app_path

# Создание DMG образа
def create_dmg(app_path):
    app_name = app_path.name.split('.')[0]
    dmg_name = f"{app_name}_Installer.dmg"
    dmg_path = DIST_DIR / dmg_name
    
    # Удаляем старый DMG если есть
    if os.path.exists(dmg_path):
        os.remove(dmg_path)
    
    # Создаем README файл
    readme_path = create_readme()
    
    # Готовим команду для создания DMG
    # hdiutil используется для создания DMG в macOS
    try:
        print("Создание DMG образа...")
        
        # Создаем временную папку для монтирования
        tmp_dir = DIST_DIR / "tmp_dmg"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)
        
        # Копируем .app в эту папку
        shutil.copytree(app_path, tmp_dir / app_path.name)
        
        # Копируем README.txt
        shutil.copy(readme_path, tmp_dir / "README.txt")
        
        # Создаем символьную ссылку на Applications
        os.symlink('/Applications', tmp_dir / 'Applications')
        
        # Создаем DMG
        subprocess.call([
            'hdiutil', 'create', '-volname', app_name, 
            '-srcfolder', str(tmp_dir), 
            '-ov', '-format', 'UDZO', str(dmg_path)
        ])
        
        # Удаляем временную папку
        shutil.rmtree(tmp_dir)
        
        print(f"DMG образ создан: {dmg_path}")
        return dmg_path
    except Exception as e:
        print(f"Ошибка создания DMG: {e}")
        return None

# Основная функция сборки
def main():
    print("Сборка VPN Server Manager для macOS")
    print("==================================")
    
    cleanup_previous_builds()
    
    # 0. Обновляем конфиг и получаем версию
    print("\n[0/3] Обновление файла конфигурации...")
    app_version = update_config_and_get_version()
    if not app_version:
        sys.exit(1) # Прерываем, если не удалось получить версию
    
    # 1. Сборка .app
    print(f"\n[1/3] Сборка .app бандла для версии {app_version}...")
    app_path = build_app()
    
    # 2. Создание .dmg
    print(f"\n[2/3] Создание .dmg образа для версии {app_version}...")
    dmg_path = create_dmg(app_path)
    
    if dmg_path:
        print("\nСборка завершена успешно!")
        print(f"- Приложение: {app_path}")
        print(f"- DMG образ: {dmg_path}")
        
        print("\n=== ВАЖНАЯ ИНФОРМАЦИЯ ДЛЯ ЗАПУСКА ===")
        print("Приложение хранит все данные в директории пользователя:")
        print("~/Library/Application Support/VPNServerManager/")
        print("\nПри первом запуске:")
        print("1. Щелкните по приложению правой кнопкой мыши")
        print("2. Выберите 'Открыть'")
        print("3. В диалоге безопасности нажмите 'Открыть'")
    else:
        print("\nСборка завершена с ошибками.")

if __name__ == "__main__":
    main() 