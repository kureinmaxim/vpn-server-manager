# Инструкция по запуску приложения в терминале

Этот файл содержит основные команды для работы с проектом через терминал на macOS.

## Основные команды

### 1. Переход в директорию проекта

Прежде всего, вам нужно перейти в папку с проектом. Скопируйте и вставьте эту команду в терминал:

```bash
cd /Users/olgazaharova/Project/ProjectPython/VPNserverManage
```

### 2. Активация виртуального окружения

Для корректной работы приложения необходимо активировать виртуальное окружение.

```bash
source venv/bin/activate
```
После активации вы увидите `(venv)` в начале строки терминала.

### 3. Запуск приложения

После активации окружения, используйте эту команду для запуска приложения:

```bash
python3 app.py
```

---

## Единая команда для запуска

Вы можете объединить все шаги в одну команду для быстрого запуска:

```bash
cd /Users/olgazaharova/Project/ProjectPython/VPNserverManage && source venv/bin/activate && python3 app.py
```

---

## Управление зависимостями

### Установка новых пакетов

Если нужно установить дополнительные пакеты Python:

```bash
source venv/bin/activate && pip install название_пакета
```

### Обновление списка зависимостей

После установки новых пакетов обновите requirements.txt:

```bash
source venv/bin/activate && pip freeze > requirements.txt
```

### Установка всех зависимостей из requirements.txt

При первой настройке или после клонирования проекта:

```bash
source venv/bin/activate && pip install -r requirements.txt
```

---

## Работа с данными

### Создание ключа шифрования

Если файл `.env` отсутствует, создайте новый ключ шифрования:

```bash
python3 -c "from cryptography.fernet import Fernet; print('SECRET_KEY=' + Fernet.generate_key().decode())" > .env
```

### Просмотр текущего ключа

Чтобы увидеть ваш текущий ключ шифрования:

```bash
cat .env
```

### Проверка данных

Для расшифровки и просмотра данных используйте встроенную утилиту:

```bash
source venv/bin/activate && python3 decrypt_tool.py
```

---

## Полезные команды для разработки

### Просмотр структуры проекта

```bash
tree -I 'venv|__pycache__|*.pyc|.git' -a
```

Если `tree` не установлена:

```bash
find . -type f -not -path "./venv/*" -not -path "./.git/*" -not -name "*.pyc" | head -20
```

### Поиск файлов

Найти все `.html` файлы:

```bash
find . -name "*.html" -not -path "./venv/*"
```

Найти все файлы с данными:

```bash
find . -name "*.enc" -o -name "*.json" -not -path "./venv/*"
```

### Проверка синтаксиса Python

```bash
source venv/bin/activate && python3 -m py_compile app.py
```

---

## Сборка приложения

### Сборка для macOS

```bash
source venv/bin/activate && python3 build_macos.py
```

### Установка PyInstaller (если не установлен)

```bash
source venv/bin/activate && pip install pyinstaller
```

---

## Работа с Git

### Статус изменений

```bash
git status
```

### Просмотр изменений

```bash
git diff
```

### Фиксация изменений

```bash
git add .
git commit -m "Описание изменений"
```

### Просмотр истории

```bash
git log --oneline | head -10
```

---

## Диагностика и отладка

### Проверка портов

Проверить, свободен ли порт 5050:

```bash
lsof -i :5050
```

### Завершение процессов на порту

Если порт занят:

```bash
lsof -ti:5050 | xargs kill -9
```

### Просмотр логов

Если приложение запущено с выводом в файл:

```bash
tail -f app.log
```

### Проверка места на диске

```bash
df -h
du -sh *
```

---

## Полезные алиасы

Добавьте эти строки в `~/.zshrc` для быстрого доступа:

```bash
# VPN Server Manager
alias vpn-cd='cd /Users/olgazaharova/Project/ProjectPython/VPNserverManage'
alias vpn-run='cd /Users/olgazaharova/Project/ProjectPython/VPNserverManage && source venv/bin/activate && python3 app.py'
alias vpn-build='cd /Users/olgazaharova/Project/ProjectPython/VPNserverManage && source venv/bin/activate && python3 build_macos.py'
alias vpn-key='cd /Users/olgazaharova/Project/ProjectPython/VPNserverManage && cat .env'
```

После добавления выполните:

```bash
source ~/.zshrc
```

Теперь вы можете использовать короткие команды:
- `vpn-cd` - перейти в папку проекта
- `vpn-run` - запустить приложение
- `vpn-build` - собрать приложение
- `vpn-key` - показать ключ шифрования

---

## Дополнительные команды

### Остановка приложения

Для остановки приложения, запущенного в терминале, просто нажмите комбинацию клавиш:

```
Ctrl + C
```

### Очистка терминала

```bash
clear
```

### Информация о системе

```bash
system_profiler SPSoftwareDataType | grep "System Version"
python3 --version
pip --version
```

---

## Новые функции

### Изменение масштаба интерфейса

Приложение теперь поддерживает изменение масштаба интерфейса (80%, 90%, 100%) через значок лупы в верхней панели.

### Импорт из другой установки

Новая функция позволяет импортировать данные из других установок с использованием внешнего ключа шифрования. Доступна в разделе "Настройки".

### Офлайн режим (v3.4.0)

Приложение теперь корректно работает без интернета:
- **Индикатор состояния сети**: WiFi/WiFi-off иконки
- **Отключение недоступных функций**: Кнопки "Проверить IP" отключаются в офлайн режиме
- **Graceful обработка ошибок**: Детальные сообщения об ошибках сети

### Исправление иконки приложения (v3.4.0)

- **Автоматическая конвертация**: favicon.ico → icon.icns
- **Правильное отображение**: Иконка корректно отображается в Dock и Finder
- **Использование оригинальной иконки**: Применяется favicon.ico из проекта

### Улучшенный .gitignore

Проект теперь исключает больше временных и системных файлов из системы контроля версий.

---

## Решение проблем

### Проблема с правами доступа

```bash
chmod +x venv/bin/activate
```

### Переустановка виртуального окружения

```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Проблемы с PyWebView на macOS

```bash
source venv/bin/activate && pip install --upgrade pywebview
```

Для получения дополнительной помощи обратитесь к документации проекта или справке в приложении.

### Дополнительная документация

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Подробная структура проекта
- **[CHANGELOG_v3.4.0.md](CHANGELOG_v3.4.0.md)** - История изменений версии 3.4.0
- **[SECRET_KEY.md](SECRET_KEY.md)** - Система шифрования
- **[BUILD.md](BUILD.md)** - Инструкции по сборке 