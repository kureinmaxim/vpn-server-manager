#!/usr/bin/env python3
"""
Скрипт для сборки VPN Server Manager с исправленными зависимостями.
Включает поддержку офлайн режима и улучшенную обработку ошибок.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime

# Основные директории
PROJECT_ROOT = Path.cwd()
DIST_DIR = PROJECT_ROOT / 'dist'
BUILD_DIR = PROJECT_ROOT / 'build'

# Создаем директории
DIST_DIR.mkdir(exist_ok=True)
BUILD_DIR.mkdir(exist_ok=True)

def cleanup_previous_builds():
    """Очистка предыдущих сборок"""
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    print("✅ Очистка предыдущих сборок завершена")

def convert_ico_to_icns():
    """Конвертация favicon.ico в icon.icns для macOS"""
    favicon_path = PROJECT_ROOT / "static" / "favicon.ico"
    icns_path = PROJECT_ROOT / "static" / "images" / "icon.icns"
    
    if not favicon_path.exists():
        print("❌ favicon.ico не найден")
        return False
    
    # Создаем временную папку для конвертации
    temp_dir = PROJECT_ROOT / "temp_icons"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Используем sips для конвертации (встроенный в macOS)
        # Сначала конвертируем в PNG разных размеров
        sizes = [16, 32, 64, 128, 256, 512]
        
        for size in sizes:
            png_path = temp_dir / f"icon_{size}.png"
            subprocess.run([
                "sips", "-s", "format", "png", 
                str(favicon_path), "--out", str(png_path),
                "-z", str(size), str(size)
            ], check=True)
        
        # Создаем .iconset папку
        iconset_path = temp_dir / "icon.iconset"
        iconset_path.mkdir(exist_ok=True)
        
        # Переименовываем файлы в формат iconset
        icon_mapping = {
            16: "icon_16x16.png",
            32: "icon_16x16@2x.png",
            32: "icon_32x32.png", 
            64: "icon_32x32@2x.png",
            128: "icon_128x128.png",
            256: "icon_128x128@2x.png",
            256: "icon_256x256.png",
            512: "icon_256x256@2x.png",
            512: "icon_512x512.png",
            1024: "icon_512x512@2x.png"
        }
        
        for size, filename in icon_mapping.items():
            if size <= 512:  # Максимальный размер из favicon
                src = temp_dir / f"icon_{size}.png"
                dst = iconset_path / filename
                if src.exists():
                    shutil.copy2(src, dst)
        
        # Конвертируем iconset в icns
        subprocess.run([
            "iconutil", "-c", "icns", str(iconset_path), "-o", str(icns_path)
        ], check=True)
        
        print(f"✅ favicon.ico конвертирован в {icns_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка конвертации: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        # Очищаем временные файлы
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def build_app():
    """Создание .app файла с исправленными зависимостями"""
    
    # Конвертируем favicon.ico в icon.icns
    print("🔄 Конвертация иконки...")
    if not convert_ico_to_icns():
        print("⚠️ Не удалось конвертировать иконку, используем существующую")
    
    # Определяем файлы для включения в сборку
    datas = [
        "templates:templates",          # HTML шаблоны
        "static:static",                # CSS, изображения
        "config.json:.",                # Конфигурация
        "data:data",                    # Данные
        "lessons:lessons",              # Учебные материалы
        "requirements.txt:.",           # Зависимости
        "docs:docs",                    # Документация
    ]
    
    # Добавляем дополнительные файлы если они есть
    additional_files = [
        "ai_services_schema.json",
        "env.example",
        "yubikey_auth.py",
        "security_logger.py",
        "decrypt_tool.py",
        "generate_key.py"
    ]
    
    for file in additional_files:
        if Path(file).exists():
            datas.append(f"{file}:.")
    
    # Формируем аргументы для PyInstaller
    datas_args = [f"--add-data={data}" for data in datas]
    
    # Проверяем наличие иконки
    icon_path = PROJECT_ROOT / "static" / "images" / "icon.icns"
    icon_arg = f"--icon={icon_path}" if icon_path.exists() else ""
    
    # КРИТИЧЕСКИ ВАЖНО: Скрытые импорты для Flask и офлайн режима
    hidden_imports = [
        # Flask и связанные модули
        "--hidden-import=flask",
        "--hidden-import=flask.app",
        "--hidden-import=flask.blueprints",
        "--hidden-import=flask.cli",
        "--hidden-import=flask.config",
        "--hidden-import=flask.ctx",
        "--hidden-import=flask.debughelpers",
        "--hidden-import=flask.helpers",
        "--hidden-import=flask.json",
        "--hidden-import=flask.logging",
        "--hidden-import=flask.sessions",
        "--hidden-import=flask.signals",
        "--hidden-import=flask.templating",
        "--hidden-import=flask.testing",
        "--hidden-import=flask.views",
        
        # Werkzeug (WSGI утилиты)
        "--hidden-import=werkzeug",
        "--hidden-import=werkzeug.datastructures",
        "--hidden-import=werkzeug.debug",
        "--hidden-import=werkzeug.exceptions",
        "--hidden-import=werkzeug.filesystem",
        "--hidden-import=werkzeug.formparser",
        "--hidden-import=werkzeug.http",
        "--hidden-import=werkzeug.local",
        "--hidden-import=werkzeug.middleware",
        "--hidden-import=werkzeug.middleware.proxy_fix",
        "--hidden-import=werkzeug.middleware.shared_data",
        "--hidden-import=werkzeug.routing",
        "--hidden-import=werkzeug.security",
        "--hidden-import=werkzeug.serving",
        "--hidden-import=werkzeug.test",
        "--hidden-import=werkzeug.testapp",
        "--hidden-import=werkzeug.urls",
        "--hidden-import=werkzeug.utils",
        "--hidden-import=werkzeug.wrappers",
        "--hidden-import=werkzeug.wsgi",
        
        # Jinja2 (шаблонизатор)
        "--hidden-import=jinja2",
        "--hidden-import=jinja2.async_utils",
        "--hidden-import=jinja2.bccache",
        "--hidden-import=jinja2.compiler",
        "--hidden-import=jinja2.debug",
        "--hidden-import=jinja2.defaults",
        "--hidden-import=jinja2.environment",
        "--hidden-import=jinja2.ext",
        "--hidden-import=jinja2.filters",
        "--hidden-import=jinja2.lexer",
        "--hidden-import=jinja2.loaders",
        "--hidden-import=jinja2.meta",
        "--hidden-import=jinja2.nativetypes",
        "--hidden-import=jinja2.nodes",
        "--hidden-import=jinja2.optimizer",
        "--hidden-import=jinja2.parser",
        "--hidden-import=jinja2.runtime",
        "--hidden-import=jinja2.sandbox",
        "--hidden-import=jinja2.tests",
        "--hidden-import=jinja2.utils",
        "--hidden-import=jinja2.visitor",
        
        # PyWebView (GUI)
        "--hidden-import=webview",
        "--hidden-import=webview.platforms.cocoa",
        "--hidden-import=webview.platforms.cef",
        "--hidden-import=webview.platforms.gtk",
        "--hidden-import=webview.platforms.winforms",
        "--hidden-import=webview.platforms.edgechromium",
        "--hidden-import=webview.platforms.edgehtml",
        "--hidden-import=webview.platforms.mshtml",
        "--hidden-import=webview.platforms.qt",
        
        # Криптография и безопасность
        "--hidden-import=cryptography",
        "--hidden-import=cryptography.fernet",
        "--hidden-import=cryptography.hazmat",
        "--hidden-import=cryptography.hazmat.primitives",
        "--hidden-import=cryptography.hazmat.primitives.ciphers",
        "--hidden-import=cryptography.hazmat.primitives.hashes",
        "--hidden-import=cryptography.hazmat.primitives.kdf",
        "--hidden-import=cryptography.hazmat.primitives.asymmetric",
        "--hidden-import=cryptography.hazmat.primitives.serialization",
        
        # Сетевые модули для офлайн режима
        "--hidden-import=requests",
        "--hidden-import=urllib3",
        "--hidden-import=urllib3.util",
        "--hidden-import=urllib3.exceptions",
        "--hidden-import=requests.adapters",
        "--hidden-import=requests.auth",
        "--hidden-import=requests.cookies",
        "--hidden-import=requests.models",
        "--hidden-import=requests.sessions",
        "--hidden-import=requests.structures",
        "--hidden-import=requests.utils",
        "--hidden-import=socket",
        "--hidden-import=urllib.parse",
        
        # Другие важные модули
        "--hidden-import=python-dotenv",
        "--hidden-import=threading",
        "--hidden-import=subprocess",
        "--hidden-import=signal",
        "--hidden-import=logging",
        "--hidden-import=re",
        "--hidden-import=uuid",
        "--hidden-import=copy",
        "--hidden-import=shutil",
        "--hidden-import=tempfile",
        "--hidden-import=zipfile",
        "--hidden-import=base64",
        "--hidden-import=datetime",
        "--hidden-import=pathlib",
        "--hidden-import=json",
        "--hidden-import=os",
        "--hidden-import=sys",
        
        # Исключения для уменьшения размера
        "--exclude-module=PyQt6",
        "--exclude-module=PyQt5",
        "--exclude-module=PySide6",
        "--exclude-module=PySide2",
        "--exclude-module=_tkinter",
        "--exclude-module=tkinter",
        "--exclude-module=tcl",
        "--exclude-module=tk",
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy"
    ]
    
    # Команда PyInstaller
    pyinstaller_cmd = [
        "python3",
        "-m", "PyInstaller",
        "--onedir",                     # Создать папку с приложением
        "--windowed",                   # GUI приложение
        "--name=VPNServerManager",
        icon_arg,                       # Иконка (если есть)
        "--clean",
        "--noconfirm",
        "--distpath=dist",
        "--workpath=build",
        "--noupx",
        "--strip",
        "--osx-bundle-identifier=com.vpnservermanager.app",
        "--debug=all",
        *datas_args,
        *hidden_imports,
        "app.py"  # Основной файл приложения
    ]
    
    # Убираем пустые аргументы
    pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]
    
    print("🔨 Запуск PyInstaller...")
    print(f"Команда: {' '.join(pyinstaller_cmd)}")
    
    # Запуск PyInstaller
    result = subprocess.run(pyinstaller_cmd, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"❌ ОШИБКА: PyInstaller завершился с кодом {result.returncode}")
        return False
    
    return True

def create_app_bundle():
    """Создание .app бандла для macOS"""
    app_name = "VPNServerManager"
    
    # Проверяем, создалась ли папка с приложением
    app_dir = DIST_DIR / app_name
    
    if app_dir.exists():
        print(f"✅ Папка приложения создана: {app_dir}")
        
        # Проверяем, есть ли уже .app файл
        app_path = DIST_DIR / f"{app_name}.app"
        
        if app_path.exists():
            print(f"✅ Приложение уже существует: {app_path}")
            # Проверяем и копируем иконку если её нет
            icon_path = app_path / "Contents" / "Resources" / "AppIcon.icns"
            if not icon_path.exists():
                source_icon = PROJECT_ROOT / "static" / "images" / "icon.icns"
                if source_icon.exists():
                    shutil.copy2(source_icon, icon_path)
                    print(f"📁 Иконка скопирована: {source_icon}")
            return app_path
        
        # Создаем .app бандл из папки
        app_contents = app_path / "Contents"
        app_macos = app_contents / "MacOS"
        app_resources = app_contents / "Resources"
        
        # Создаем директории
        app_macos.mkdir(parents=True, exist_ok=True)
        app_resources.mkdir(parents=True, exist_ok=True)
        
        # Копируем все файлы из папки приложения
        shutil.copytree(app_dir, app_macos / app_name, dirs_exist_ok=True)
        
        # Создаем Info.plist
        info_plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{app_name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.vpnservermanager.app</string>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>3.3.4</string>
    <key>CFBundleVersion</key>
    <string>3.3.4</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>CFBundleIconFile</key>
    <string>AppIcon.icns</string>
</dict>
</plist>"""
        
        with open(app_contents / "Info.plist", "w") as f:
            f.write(info_plist_content)
        
        # Копируем иконку если есть
        icon_path = PROJECT_ROOT / "static" / "images" / "icon.icns"
        if icon_path.exists():
            shutil.copy2(icon_path, app_resources / "AppIcon.icns")
            print(f"📁 Иконка скопирована: {icon_path}")
        else:
            print("⚠️ Иконка не найдена")
        
        print(f"✅ Приложение создано: {app_path}")
        return app_path
    else:
        print(f"❌ Ошибка: папка приложения не найдена в {app_dir}")
        return None

def create_readme():
    """Создание файла README.txt с инструкциями"""
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
    with open(readme_path, "w", encoding='utf-8') as f:
        f.write(readme_content)
    
    return readme_path

def create_dmg(app_path):
    """Создание DMG образа для распространения"""
    app_name = app_path.name.split('.')[0]
    dmg_name = f"{app_name}_Installer.dmg"
    dmg_path = DIST_DIR / dmg_name
    
    # Удаляем старый DMG если есть
    if dmg_path.exists():
        dmg_path.unlink()
    
    # Создаем README файл
    readme_path = create_readme()
    
    try:
        print("📦 Создание DMG образа...")
        
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
        subprocess.run([
            'hdiutil', 'create', '-volname', app_name, 
            '-srcfolder', str(tmp_dir), 
            '-ov', '-format', 'UDZO', str(dmg_path)
        ], check=True)
        
        # Удаляем временную папку
        shutil.rmtree(tmp_dir)
        
        print(f"✅ DMG образ создан: {dmg_path}")
        return dmg_path
    except Exception as e:
        print(f"❌ Ошибка создания DMG: {e}")
        return None

def diagnose_app(app_path):
    """Диагностика проблем с запуском приложения"""
    print("\n🔍 Диагностика приложения...")
    
    if not app_path.exists():
        print("❌ Приложение не найдено")
        return False
    
    # Проверяем права доступа
    try:
        executable_path = app_path / "Contents" / "MacOS" / "VPNServerManager" / "VPNServerManager"
        if executable_path.exists():
            os.chmod(executable_path, 0o755)
            print("✅ Права доступа установлены")
        else:
            print("⚠️ Исполняемый файл не найден")
    except Exception as e:
        print(f"⚠️ Ошибка установки прав: {e}")
    
    # Проверяем зависимости
    try:
        if executable_path.exists():
            result = subprocess.run([
                "otool", "-L", str(executable_path)
            ], capture_output=True, text=True)
            print("✅ Зависимости проверены")
        else:
            print("⚠️ Не удалось проверить зависимости")
    except Exception as e:
        print(f"⚠️ Ошибка проверки зависимостей: {e}")
    
    # Проверяем Info.plist
    info_plist = app_path / "Contents" / "Info.plist"
    if info_plist.exists():
        print("✅ Info.plist найден")
    else:
        print("❌ Info.plist отсутствует")
    
    # Проверяем иконку
    icon_path = app_path / "Contents" / "Resources" / "AppIcon.icns"
    if icon_path.exists():
        print("✅ Иконка найдена")
    else:
        print("⚠️ Иконка отсутствует")
    
    # Проверяем структуру приложения
    app_dir = app_path / "Contents" / "MacOS" / "VPNServerManager"
    if app_dir.exists():
        print("✅ Структура приложения корректна")
        # Показываем размер
        try:
            size = sum(f.stat().st_size for f in app_dir.rglob('*') if f.is_file())
            print(f"📊 Размер приложения: {size / 1024 / 1024:.1f} MB")
        except:
            pass
    else:
        print("❌ Структура приложения некорректна")
    
    print("🔍 Диагностика завершена")
    return True

def main():
    """Основная функция сборки"""
    print("🚀 Сборка VPN Server Manager v3.3.4")
    print("=====================================")
    print(f"📁 Проект: {PROJECT_ROOT}")
    print(f"📦 Результат: {DIST_DIR}")
    print()
    
    # Очистка
    cleanup_previous_builds()
    
    # Сборка
    if build_app():
        print("✅ Сборка завершена успешно!")
        
        # Создание .app бандла
        app_path = create_app_bundle()
        if app_path:
            print("🎉 Приложение готово к использованию!")
            print(f"📁 Расположение: {DIST_DIR}")
            
            # Диагностика приложения
            diagnose_app(app_path)
            
            # Создание DMG образа
            print("\n📦 Создание инсталлятора...")
            dmg_path = create_dmg(app_path)
            
            if dmg_path:
                print("🎉 Инсталлятор создан успешно!")
                print(f"📦 DMG файл: {dmg_path}")
                print()
                print("🔧 Особенности сборки:")
                print("   ✅ Поддержка офлайн режима")
                print("   ✅ Улучшенная обработка ошибок")
                print("   ✅ Криптографические функции")
                print("   ✅ PyWebView GUI")
                print("   ✅ Flask веб-сервер")
                print("   ✅ Шифрование данных")
                print("   ✅ DMG инсталлятор")
                print("   ✅ Иконка приложения")
            else:
                print("⚠️ Приложение создано, но DMG не создался")
                print("Приложение доступно в папке dist/")
        else:
            print("❌ Ошибка создания .app бандла")
            sys.exit(1)
    else:
        print("❌ Ошибка сборки")
        sys.exit(1)

if __name__ == "__main__":
    main() 