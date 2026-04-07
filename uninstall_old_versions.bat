@echo off
REM Скрипт для удаления старых версий VPN Server Manager
REM Сначала удалите вручную через "Программы и компоненты"

echo ========================================
echo Удаление старых версий VPN Server Manager
echo ========================================
echo.
echo ВНИМАНИЕ: Этот скрипт удалит ВСЕ версии VPN Server Manager.
echo Ваши данные (.env, config.json, data/) будут сохранены.
echo.
pause

echo.
echo Открываю "Программы и компоненты"...
appwiz.cpl

echo.
echo ========================================
echo Инструкция:
echo ========================================
echo.
echo 1. Найдите "VPN Server Manager 3.5.9"
echo 2. Нажмите "Удалить"
echo 3. При удалении выберите "Сохранить данные"
echo.
echo 4. Найдите "VPN Server Manager, версия 4.0.8"
echo 5. Нажмите "Удалить" 
echo 6. При удалении выберите "Сохранить данные"
echo.
echo 7. После удаления обеих версий нажмите любую клавишу
echo.
pause

echo.
echo Проверяю оставшиеся файлы...
echo.

if exist "C:\Program Files\VPN Server Manager" (
    echo НАЙДЕНО: C:\Program Files\VPN Server Manager
    echo Удаляю...
    rd /s /q "C:\Program Files\VPN Server Manager"
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\VPN Server Manager" (
    echo НАЙДЕНО: C:\Users\%USERNAME%\AppData\Local\Programs\VPN Server Manager
    echo Оставляем - там могут быть данные пользователя
)

echo.
echo Удаляю старые ярлыки...
del "%USERPROFILE%\Desktop\VPN Server Manager.lnk" 2>nul
del "%USERPROFILE%\OneDrive\Рабочий стол\VPN Server Manager.lnk" 2>nul

echo.
echo ========================================
echo Готово! Теперь установите новую версию.
echo ========================================
echo.
pause

