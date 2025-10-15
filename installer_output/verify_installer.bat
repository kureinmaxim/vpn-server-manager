@echo off
REM Автоматическая проверка контрольной суммы инсталлятора
REM VPN Server Manager v4.0.7

echo ========================================
echo Проверка подлинности инсталлятора
echo VPN Server Manager v4.0.9
echo ========================================
echo.

set INSTALLER=VPN-Server-Manager-Setup-v4.0.9.exe
set CHECKSUM_FILE=checksum.txt

REM Проверяем наличие файлов
if not exist "%INSTALLER%" (
    echo [ОШИБКА] Файл %INSTALLER% не найден!
    echo.
    echo Убедитесь, что скрипт находится в той же папке с инсталлятором.
    pause
    exit /b 1
)

if not exist "%CHECKSUM_FILE%" (
    echo [ОШИБКА] Файл %CHECKSUM_FILE% не найден!
    echo.
    echo Скачайте checksum.txt с официальной страницы релиза.
    pause
    exit /b 1
)

echo [OK] Все файлы найдены
echo.

echo Читаем официальную контрольную сумму...
set /p EXPECTED=<%CHECKSUM_FILE%
echo [OK] Загружено: %EXPECTED%
echo.

echo Вычисляем контрольную сумму инсталлятора...
echo (это может занять несколько секунд)
echo.

REM Вычисляем SHA-256 через certutil
certutil -hashfile "%INSTALLER%" SHA256 > temp_hash.txt 2>&1

REM Извлекаем только хеш (вторая строка)
set LINE_NUM=0
for /f "skip=1 tokens=*" %%a in (temp_hash.txt) do (
    if !LINE_NUM!==0 (
        set ACTUAL=%%a
        set LINE_NUM=1
    )
)

REM Удаляем временный файл
del temp_hash.txt 2>nul

REM Удаляем пробелы из хеша
set ACTUAL=%ACTUAL: =%

echo [OK] Вычислено: %ACTUAL%
echo.

echo Сравнение контрольных сумм...
echo.

REM Сравниваем (без учета регистра)
if /i "%EXPECTED%"=="%ACTUAL%" (
    echo ========================================
    echo [V] ПРОВЕРКА УСПЕШНА!
    echo ========================================
    echo.
    echo Файл подлинный и не поврежден.
    echo Можно безопасно устанавливать.
    echo.
    
    choice /C YN /M "Запустить установку сейчас"
    if errorlevel 2 goto :cancel
    if errorlevel 1 goto :install
) else (
    echo ========================================
    echo [X] ПРОВЕРКА НЕ ПРОЙДЕНА!
    echo ========================================
    echo.
    echo ВНИМАНИЕ: Файл поврежден или подделан!
    echo НЕ УСТАНАВЛИВАЙТЕ ЭТОТ ФАЙЛ!
    echo.
    echo Ожидалось:
    echo   %EXPECTED%
    echo.
    echo Получено:
    echo   %ACTUAL%
    echo.
    echo Рекомендации:
    echo   1. Удалите этот файл
    echo   2. Очистите кэш браузера
    echo   3. Скачайте заново с официального сайта
    echo   4. Проверьте снова
    echo.
    pause
    exit /b 1
)

:install
echo.
echo Запуск инсталлятора...
start "" "%INSTALLER%"
exit /b 0

:cancel
echo.
echo Установка отменена.
pause
exit /b 0

