; VPN Server Manager - Inno Setup Installer Script
; Version 4.0.9
; Compatible with Inno Setup 6.x

#define MyAppName "VPN Server Manager"
#define MyAppVersion "4.0.9"
#define MyAppPublisher "Куреин М.Н."
#define MyAppURL "https://github.com/kureinmaxim/vpn-server-manager"
#define MyAppExeName "start_windows.bat"
#define PythonMinVersion "3.8"

[Setup]
; Основные настройки
AppId={{8F9A5B3C-1D2E-4F6A-9C8B-7E5D4A3F2B1C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=README_WINDOWS.md
OutputDir=installer_output
OutputBaseFilename=VPN-Server-Manager-Setup-v{#MyAppVersion}
SetupIconFile=static\favicon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\static\favicon.ico

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Запускать при входе в Windows"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
; Основные файлы приложения
Source: "app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "desktop\*"; DestDir: "{app}\desktop"; Flags: ignoreversion recursesubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion
Source: "translations\*"; DestDir: "{app}\translations"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "tests\*"; DestDir: "{app}\tests"; Flags: ignoreversion recursesubdirs createallsubdirs

; Документация
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_WINDOWS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "SECURITY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "PROJECT_DOCUMENTATION.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "DOCKER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion

; Python скрипты
Source: "run.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "generate_key.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "launch_gui.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "decrypt_tool.py"; DestDir: "{app}"; Flags: ignoreversion

; Конфигурационные файлы
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "pytest.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "babel.cfg"; DestDir: "{app}"; Flags: ignoreversion
Source: "Makefile"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup.py"; DestDir: "{app}"; Flags: ignoreversion

; Шаблоны конфигурации (НЕ сами конфиги!)
Source: "env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json.example"; DestDir: "{app}"; Flags: ignoreversion

; Bat-скрипты для Windows
Source: "setup_windows.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "start_windows.bat"; DestDir: "{app}"; Flags: ignoreversion

; Создаем пустые директории
Source: "data\hints.json"; DestDir: "{app}\data"; Flags: ignoreversion

; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Dirs]
; Создание необходимых директорий
Name: "{app}\data"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full
Name: "{app}\venv"; Permissions: users-full
Name: "{app}\backup"; Permissions: users-full

[Icons]
; Иконки в меню Пуск
Name: "{group}\{#MyAppName}"; Filename: "{app}\start_windows.bat"; IconFilename: "{app}\static\favicon.ico"; WorkingDir: "{app}"
Name: "{group}\Открыть папку приложения"; Filename: "{app}"
Name: "{group}\Документация"; Filename: "{app}\README_WINDOWS.md"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"

; Иконка на рабочем столе
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\start_windows.bat"; IconFilename: "{app}\static\favicon.ico"; WorkingDir: "{app}"; Tasks: desktopicon

; Автозагрузка (опционально)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\start_windows.bat"; IconFilename: "{app}\static\favicon.ico"; WorkingDir: "{app}"; Tasks: startupicon

[Run]
; Проверка Python при установке
Filename: "python"; Parameters: "--version"; StatusMsg: "Проверка наличия Python..."; Flags: runhidden waituntilterminated; Check: CheckPythonInstalled

; Запуск setup_windows.bat после установки (с видимым окном для отслеживания прогресса)
Filename: "{app}\setup_windows.bat"; Description: "Установить зависимости и настроить приложение (рекомендуется)"; StatusMsg: "Настройка виртуального окружения и установка зависимостей (это займет 3-5 минут)..."; Flags: postinstall waituntilterminated; Check: CheckPythonInstalled

; Запуск приложения после установки
Filename: "{app}\start_windows.bat"; Description: "Запустить {#MyAppName}"; Flags: postinstall skipifsilent nowait; Check: CheckSetupCompleted

; Открыть README
Filename: "{app}\README_WINDOWS.md"; Description: "Открыть руководство пользователя"; Flags: postinstall shellexec skipifsilent

[UninstallDelete]
; Удаление созданных файлов и папок при деинсталляции
Type: filesandordirs; Name: "{app}\venv"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\app\__pycache__"
Type: filesandordirs; Name: "{app}\desktop\__pycache__"
Type: filesandordirs; Name: "{app}\*.pyc"
Type: dirifempty; Name: "{app}\backup"
; NOTE: НЕ удаляем .env, config.json и data/* - пользовательские данные!

[Code]
var
  PythonInstalled: Boolean;
  SetupCompleted: Boolean;

// Проверка установленного Python
function CheckPythonInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  PythonInstalled := False;
  
  // Проверяем, установлен ли Python
  if Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      PythonInstalled := True;
      Result := True;
    end;
  end;
end;

// Проверка завершения настройки
function CheckSetupCompleted: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\venv\Scripts\python.exe'));
  SetupCompleted := Result;
end;

// Инициализация установщика
function InitializeSetup: Boolean;
begin
  Result := True;
  PythonInstalled := False;
  SetupCompleted := False;
  
  // Проверяем Python
  if not CheckPythonInstalled then
  begin
    if MsgBox('Python не обнаружен на вашем компьютере.' + #13#10#13#10 +
              'Для работы приложения требуется Python 3.8 или выше.' + #13#10#13#10 +
              'Хотите продолжить установку? (Вам потребуется установить Python вручную)', 
              mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end
    else
    begin
      MsgBox('После завершения установки:' + #13#10 +
             '1. Скачайте Python с https://www.python.org/downloads/' + #13#10 +
             '2. При установке отметьте "Add Python to PATH"' + #13#10 +
             '3. Запустите setup_windows.bat из папки приложения', 
             mbInformation, MB_OK);
    end;
  end;
end;

// После успешной установки
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Проверяем, создан ли файл .env
    if not FileExists(ExpandConstant('{app}\.env')) then
    begin
      Log('File .env not found, will be created during first run');
    end;
    
    // Проверяем, создан ли файл config.json
    if not FileExists(ExpandConstant('{app}\config.json')) then
    begin
      Log('File config.json not found, will be created during first run');
    end;
  end;
end;

// Информация перед удалением
function InitializeUninstall(): Boolean;
var
  Response: Integer;
begin
  Result := True;
  
  Response := MsgBox('Сохранить пользовательские данные?' + #13#10#13#10 +
                     'Файлы .env, config.json и папка data содержат ваши настройки и данные серверов.' + #13#10 +
                     'Рекомендуется сохранить их перед удалением.' + #13#10#13#10 +
                     'YES - Сохранить данные (удалить только программу)' + #13#10 +
                     'NO - Удалить всё, включая данные' + #13#10 +
                     'CANCEL - Отменить удаление',
                     mbConfirmation, MB_YESNOCANCEL);
  
  case Response of
    IDYES:
      begin
        // Пользователь хочет сохранить данные - не удаляем их
        Result := True;
      end;
    IDNO:
      begin
        // Пользователь хочет удалить всё
        DeleteFile(ExpandConstant('{app}\.env'));
        DeleteFile(ExpandConstant('{app}\config.json'));
        DelTree(ExpandConstant('{app}\data'), True, True, True);
        Result := True;
      end;
    IDCANCEL:
      begin
        // Отменить удаление
        Result := False;
      end;
  end;
end;

// После удаления
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Показываем сообщение о сохраненных данных
    if FileExists(ExpandConstant('{app}\.env')) or 
       FileExists(ExpandConstant('{app}\config.json')) then
    begin
      MsgBox('Ваши данные сохранены в:' + #13#10 +
             ExpandConstant('{app}') + #13#10#13#10 +
             'Файлы: .env, config.json, data\' + #13#10#13#10 +
             'При переустановке приложения эти файлы будут использованы автоматически.',
             mbInformation, MB_OK);
    end;
  end;
end;

