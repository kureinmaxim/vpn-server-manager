"""
Скрипт для сборки Windows-инсталлятора VPN Server Manager.
Создает как полную, так и портативную версии.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Основные директории и файлы проекта
PROJECT_ROOT = Path.cwd()
DIST_DIR = PROJECT_ROOT / 'dist'
BUILD_DIR = PROJECT_ROOT / 'build'
INNO_SCRIPT = PROJECT_ROOT / 'vpnserver_setup.iss'

# Создаем директории для сборки если их нет
DIST_DIR.mkdir(exist_ok=True)
BUILD_DIR.mkdir(exist_ok=True)

# Удаляем предыдущие сборки
def cleanup_previous_builds():
    print("Очистка предыдущих сборок...")
    if DIST_DIR.exists():
        for item in DIST_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    
    # Очищаем сборочную директорию
    if BUILD_DIR.exists():
        for item in BUILD_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

# Сборка основного приложения с PyInstaller
def build_app(portable=False):
    app_name = "VPNServerManager-Portable" if portable else "VPNServerManager"
    icon_path = os.path.join(PROJECT_ROOT, "static", "favicon.ico")
    
    pyinstaller_cmd = [
        "pyinstaller",
        "--name={}".format(app_name),
        "--icon={}".format(icon_path) if os.path.exists(icon_path) else "",
        "--add-data=static;static",
        "--add-data=templates;templates",
        "--add-data=requirements.txt;.",
        "--hidden-import=flask",
        "--hidden-import=cryptography",
        "--hidden-import=dotenv",
        "--hidden-import=werkzeug",
        "--hidden-import=requests",
        "--hidden-import=jinja2",
        "--onedir",
        "app.py"
    ]
    
    # Для портативной версии добавляем специальные настройки
    if portable:
        pyinstaller_cmd.append("--add-binary=portable_launcher.py;.")
        pyinstaller_cmd.append("--noconsole")
    
    # Выполняем команду сборки
    subprocess.call(pyinstaller_cmd)
    
    return app_name

# Создание файла конфигурации для Inno Setup
def create_inno_script(app_name):
    version = "1.0.0"  # Версию можно получать из app.py или другого места
    
    inno_script = f"""
    #define MyAppName "VPN Server Manager"
    #define MyAppVersion "{version}"
    #define MyAppPublisher "Olga Zaharova"
    #define MyAppURL ""
    #define MyAppExeName "{app_name}.exe"

    [Setup]
    AppId={{BC6C0492-0759-4241-BFBC-BAD3308147FA}}
    AppName={{#MyAppName}}
    AppVersion={{#MyAppVersion}}
    AppPublisher={{#MyAppPublisher}}
    AppPublisherURL={{#MyAppURL}}
    AppSupportURL={{#MyAppURL}}
    AppUpdatesURL={{#MyAppURL}}
    DefaultDirName={{autopf}}\\{{#MyAppName}}
    DisableProgramGroupPage=yes
    LicenseFile={PROJECT_ROOT / "LICENSE"}
    PrivilegesRequiredOverridesAllowed=dialog
    OutputDir={DIST_DIR}
    OutputBaseFilename=VPNServerManager_Setup_{version}
    SetupIconFile={PROJECT_ROOT / "static" / "favicon.ico"}
    Compression=lzma
    SolidCompression=yes
    WizardStyle=modern

    [Languages]
    Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

    [Tasks]
    Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"
    Name: "startmenuicon"; Description: "Создать ярлык в меню Пуск"; GroupDescription: "Ярлыки:"

    [Files]
    Source: "{DIST_DIR / app_name / "*"}"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

    [Icons]
    Name: "{{autoprograms}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
    Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon
    """
    
    with open(INNO_SCRIPT, 'w') as f:
        f.write(inno_script)
        
    print(f"Создан скрипт для Inno Setup: {INNO_SCRIPT}")
    return INNO_SCRIPT

# Запуск Inno Setup для создания установщика
def build_installer(inno_script):
    # Путь к Inno Setup Compiler (может отличаться на вашей системе)
    inno_compiler = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    
    if os.path.exists(inno_compiler):
        print("Запуск Inno Setup для создания установщика...")
        subprocess.call([inno_compiler, str(inno_script)])
        print("Инсталлятор создан успешно!")
    else:
        print("ВНИМАНИЕ: Inno Setup не найден. Пожалуйста, установите Inno Setup 6 с сайта https://jrsoftware.org/isdl.php")
        print("После установки запустите этот скрипт еще раз или скомпилируйте .iss файл вручную.")

# Создание портативной версии
def create_portable_version(app_name):
    portable_dir = DIST_DIR / app_name
    print(f"Создание портативной версии в {portable_dir}...")
    
    # Создаем .bat файл для запуска портативной версии
    launcher = portable_dir / "VPNServerManager-Portable.bat"
    with open(launcher, 'w') as f:
        f.write('@echo off\n')
        f.write('echo Запуск VPN Server Manager...\n')
        f.write(f'start "" "{app_name}.exe"\n')
    
    # Создаем portable_config.ini для указания, что это портативная версия
    config = portable_dir / "portable_config.ini"
    with open(config, 'w') as f:
        f.write('[Settings]\n')
        f.write('Portable=1\n')
        f.write('DataPath=data\n')
        f.write('UploadsPath=uploads\n')
    
    # Создаем пустые директории для данных
    (portable_dir / "data").mkdir(exist_ok=True)
    (portable_dir / "uploads").mkdir(exist_ok=True)
    
    # Создаем ZIP архив с портативной версией
    portable_zip = DIST_DIR / f"{app_name}.zip"
    if os.path.exists(portable_zip):
        os.remove(portable_zip)
    
    print("Создание ZIP архива для портативной версии...")
    shutil.make_archive(
        str(portable_dir),  # базовое имя архива (без расширения)
        'zip',              # формат архива
        portable_dir        # папка для архивации
    )
    print(f"Портативная версия создана: {portable_zip}")

# Основная функция сборки
def main():
    print("Сборка VPN Server Manager для Windows")
    print("=====================================")
    
    cleanup_previous_builds()
    
    # 1. Сборка обычного приложения
    print("\n[1/4] Сборка основного приложения...")
    app_name = build_app()
    
    # 2. Создание Inno Setup скрипта
    print("\n[2/4] Создание скрипта для инсталлятора...")
    inno_script = create_inno_script(app_name)
    
    # 3. Сборка инсталлятора
    print("\n[3/4] Сборка инсталлятора...")
    build_installer(inno_script)
    
    # 4. Сборка портативной версии
    print("\n[4/4] Сборка портативной версии...")
    portable_app_name = build_app(portable=True)
    create_portable_version(portable_app_name)
    
    print("\nСборка завершена! Результаты находятся в папке dist/")

if __name__ == "__main__":
    main() 