#!/usr/bin/env python3
"""
Скрипт для сборки VPN Server Manager (версия из config/config.json.template).
Включает поддержку Application Factory, Service Layer и современные практики разработки.
Версия автоматически загружается из config.json.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
import json
from datetime import datetime

# Основные директории
PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / 'dist' / 'macos-local'
BUILD_DIR = PROJECT_ROOT / 'build' / 'macos-local'

def cleanup_previous_builds():
    """Очистка предыдущих сборок"""
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    print("✅ Очистка предыдущих сборок завершена")

def get_build_metadata_sources():
    """Возвращает доступные файлы конфигурации для сборки"""
    return [
        PROJECT_ROOT / "config" / "config.json.template",
    ]

def convert_ico_to_icns():
    """Конвертация favicon.ico в icon.icns для macOS"""
    favicon_path = PROJECT_ROOT / "static" / "images" / "icon_clean.ico"
    icns_path = PROJECT_ROOT / "static" / "images" / "icon_clean.icns"
    
    if not favicon_path.exists():
        print("❌ icon_clean.ico не найден")
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
        
        print(f"✅ icon_clean.ico конвертирован в {icns_path}")
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
    
    # Получаем версию из config.json для PyInstaller
    version = get_version_from_config()
    print(f"📦 Версия для сборки: {version}")
    
    # Проверяем наличие иконки
    print("🔄 Проверка иконки...")
    icon_path = PROJECT_ROOT / "static" / "images" / "icon_clean.png"
    if icon_path.exists():
        print("✅ Иконка найдена")
    else:
        print("⚠️ Иконка не найдена")
    
    # Определяем файлы для включения в сборку
    datas = [
        "templates:templates",          # HTML шаблоны
        "static:static",                # CSS, изображения
        "env.example:.",                # Пример конфигурации (шаблон)
        # NOTE: .env и config.json НЕ включаются в сборку по соображениям безопасности
        # Пользователь должен создать их самостоятельно после установки
        # WARNING: data contains private server databases and notes.
        # Runtime creates user data separately; never package the local directory.
        "app:app",                      # Новое приложение
        "desktop:desktop",              # Desktop GUI
    ]

    config_template = PROJECT_ROOT / "config" / "config.json.template"
    if config_template.exists():
        datas.append("config/config.json.template:config")
    else:
        print("⚠️ config/config.json.template не найден, шаблон конфигурации не будет включен в сборку")

    requirements_path = PROJECT_ROOT / "requirements.txt"
    if requirements_path.exists():
        datas.append("requirements.txt:.")
    else:
        print("⚠️ requirements.txt не найден, файл не будет включен в сборку")

    # ВКЛЮЧАЕМ ПЕРЕВОДЫ (.po/.mo). Достаточно добавить всю папку translations
    if (PROJECT_ROOT / 'translations').exists():
        datas.append("translations:translations")
    
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
    datas_args = [f"--add-data={PROJECT_ROOT / source}:{target}"
                  for source, target in (data.split(":", 1) for data in datas)]
    
    # Проверяем наличие иконки
    icon_path = PROJECT_ROOT / "static" / "images" / "icon_clean.icns"
    if not icon_path.exists():
        # Если нет .icns файла, используем .png
        icon_path = PROJECT_ROOT / "static" / "images" / "icon_clean.png"
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
        
        # macOS AppKit для GUI активации
        "--hidden-import=AppKit",
        "--hidden-import=Foundation",
        "--hidden-import=objc",
        
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
        "--hidden-import=dotenv",
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
        sys.executable,
        "-m", "PyInstaller",
        "--onedir",                     # Создать папку с приложением
        "--windowed",                   # GUI приложение (обязательно для .app)
        "--name=VPNServerManager-Clean",
        icon_arg,                       # Иконка (если есть)
        "--clean",
        "--noconfirm",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
        "--noupx",
        "--strip",
        "--osx-bundle-identifier=com.vpnservermanager.clean.app",
        # "--debug=all",  # Отключаем debug для чистой сборки
        *datas_args,
        *hidden_imports,
        "launch_gui.py"  # GUI Launcher с активацией foreground для macOS
    ]
    
    # Убираем пустые аргументы
    pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]
    
    print("🔨 Запуск PyInstaller...")
    print(f"Команда: {' '.join(pyinstaller_cmd)}")
    
    # Запуск PyInstaller
    build_env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(BUILD_DIR / 'cache'))
    result = subprocess.run(pyinstaller_cmd, capture_output=False, text=True, cwd=PROJECT_ROOT, env=build_env)
    
    if result.returncode != 0:
        print(f"❌ ОШИБКА: PyInstaller завершился с кодом {result.returncode}")
        return False
    
    return (DIST_DIR / "VPNServerManager-Clean.app").is_dir()

def create_readme():
    """Создание файла README.txt с инструкциями"""
    readme_content = """VPN Server Manager — LOCAL DEVELOPMENT BUILD

This ad-hoc signed build is not notarized and is not a public macOS release.
Do not disable Gatekeeper to distribute it. Public distribution requires
Developer ID signing, notarization, stapling and clean-Mac installation tests.
Architecture and the binary deployment-target lower bound are in the adjacent
JSON build manifest. The oldest supported OS still needs a real smoke test.

Building does not modify the installed application or the user's profile.
Runtime data: ~/Library/Application Support/VPNServerManager-Clean/
That profile contains secrets and the encryption key: never attach it to issues.
"""

    readme_path = DIST_DIR / "README.txt"
    with open(readme_path, "w", encoding='utf-8') as f:
        f.write(readme_content)
    
    return readme_path

def create_dmg(app_path, metadata):
    """Создание DMG образа для распространения"""
    app_name = app_path.name.split('.')[0]
    dmg_name = f"{app_name}-{metadata['version']}-{metadata['architecture']}-local.dmg"
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
        shutil.copytree(app_path, tmp_dir / app_path.name, symlinks=True)
        from tools.macos_bundle import verify
        verify(tmp_dir / app_path.name)
        
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
        
        subprocess.run(['hdiutil', 'verify', str(dmg_path)], check=True)
        # Удаляем временную папку
        shutil.rmtree(tmp_dir)
        
        print(f"✅ DMG образ создан: {dmg_path}")
        return dmg_path
    except Exception as e:
        print(f"❌ Ошибка создания DMG: {e}")
        return None

def get_version_from_config():
    """Получение версии из config.json"""
    try:
        for config_path in get_build_metadata_sources():
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    version = config.get('app_info', {}).get('version')
                    if version:
                        print(f"ℹ️ Версия сборки взята из {config_path.relative_to(PROJECT_ROOT)}")
                        return version

        print("⚠️ Файлы конфигурации версии не найдены, используем версию по умолчанию")
        return '5.0.19'
    except Exception as e:
        print(f"⚠️ Ошибка чтения конфигурации версии: {e}, используем версию по умолчанию")
        return '5.0.19'

def main():
    """Local build: mutate resources, sign, verify, then package; fail closed."""
    from tools.macos_bundle import finalize, write_manifest
    if sys.platform != 'darwin':
        raise SystemExit('macOS is required')
    version = get_version_from_config()
    print(f'Local macOS build {version}; output: {DIST_DIR}')
    # These dedicated output directories never contain the installed app/profile.
    cleanup_previous_builds()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if not build_app():
        raise SystemExit('PyInstaller build failed')
    app_path = DIST_DIR / 'VPNServerManager-Clean.app'
    metadata = finalize(app_path, PROJECT_ROOT / 'Info.plist.template', version,
                        target=os.environ.get('MACOSX_DEPLOYMENT_TARGET', '13.0'))
    subprocess.run([str(app_path / 'Contents/MacOS/VPNServerManager-Clean'),
                    '--build-smoke-test'], check=True, timeout=60)
    metadata['runtime_smoke'] = 'passed-on-build-host'
    metadata['python'] = sys.version.split()[0]
    dmg_path = create_dmg(app_path, metadata)
    if not dmg_path:
        raise SystemExit('DMG creation or verification failed')
    manifest = write_manifest(dmg_path, metadata)
    print(f'Local build verified: {dmg_path}\nManifest: {manifest}')
    print('Ad-hoc signature only. Not notarized; not ready for public release.')


if __name__ == '__main__':
    main()
