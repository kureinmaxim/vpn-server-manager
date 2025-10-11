# 📚 Индекс документации VPN Server Manager

Полная документация проекта VPN Server Manager v4.0.1

## 🚀 Быстрый старт

- [README.md](../README.md) - Основная информация о проекте
- [README_NEW_STRUCTURE.md](../README_NEW_STRUCTURE.md) - Новая архитектура v4.0.1
- [CHANGELOG.md](../CHANGELOG.md) - История изменений

## 📋 Основная документация

### Архитектура и структура
- [Структура проекта](project_info/PROJECT_STRUCTURE.md) - Полная структура файлов и папок
- [Архитектурные правила](../ArchitecturalRules.md) - Принципы и правила архитектуры
- [Отчет о реструктуризации](../RESTRUCTURING_REPORT.md) - Подробный отчет о переходе на v4.0

### Сборка и развертывание
- [Инструкция по сборке](project_info/BUILD.md) - Как собрать приложение
- [Руководство по релизу](release_guide.md) - Процесс создания релизов
- [Docker руководство](../DOCKER_GUIDE.md) - Работа с Docker

### Безопасность и настройка
- [Управление ключами шифрования](project_info/SECRET_KEY.md) - Система шифрования данных
- [Инструменты резервного копирования](project_info/BACKUP_TOOLS.md) - Резервное копирование и восстановление

## 🔧 Технические отчеты и исправления

### Исправления v4.0.1 (11 октября 2025)
- ✅ [PIN Authentication Fix](../PIN_AUTHENTICATION_FIX.md) - **Исправлена проблема входа по PIN**
  - Проблема: JavaScript отправлял данные в неправильном формате
  - Решение: Изменен формат на JSON в `layout.html`
  - Статус: Полностью работает

### Другие отчеты
- [Port Solution Report](../PORT_SOLUTION_REPORT.md) - Решение проблем с портами
- [Final Testing Report](../FINAL_TESTING_REPORT.md) - Финальный отчет о тестировании
- [Testing Report Chrome MCP](../TESTING_REPORT_CHROME_MCP.md) - Тестирование с Chrome DevTools
- [Update Summary](../UPDATE_SUMMARY.md) - Сводка обновлений

## 📝 Git и GitHub

### Работа с репозиторием
- [Git и GitHub руководство](../GIT_GITHUB_GUIDE.md) - Полное руководство по Git
- [Git шпаргалка](../GIT_CHEATSHEET.md) - Быстрая справка по командам
- [Руководство по публикации на GitHub](github_push_guide.md) - Как опубликовать проект

### GitHub Actions
- [Индекс GitHub Actions](lessons/github-actions/GITHUB_ACTIONS_INDEX.md)
- [Уроки GitHub Actions](lessons/github-actions/GITHUB_ACTIONS_LESSONS.md)
- [FAQ GitHub Actions](lessons/github-actions/GITHUB_ACTIONS_FAQ.md)
- [Использование в проекте](lessons/github-actions/PROJECT_USAGE.md)

### Стандарты GitHub
- [Кодекс поведения](lessons/github_docs/CODE_OF_CONDUCT.md)
- [Руководство для контрибьюторов](lessons/github_docs/CONTRIBUTING.md)
- [Политика безопасности](lessons/github_docs/SECURITY.md)

## 📘 Учебные материалы

### Основы GitHub
- [01 - Основы Git и GitHub](lessons/github_tutorials/github_basics_tutorials/01_основы_git_и_github.md)
- [02 - Ветки и слияния](lessons/github_tutorials/github_basics_tutorials/02_ветки_и_слияния.md)
- [03 - Pull Requests](lessons/github_tutorials/github_basics_tutorials/03_pull_requests.md)
- [04 - Issues и проекты](lessons/github_tutorials/github_basics_tutorials/04_issues_и_проекты.md)
- [05 - GitHub Actions](lessons/github_tutorials/github_basics_tutorials/05_github_actions.md)

### GitHub CLI
- [01 - Введение в GitHub CLI](lessons/github_tutorials/github_cli_tutorials/01_введение_в_github_cli.md)
- [02 - Работа с репозиториями](lessons/github_tutorials/github_cli_tutorials/02_работа_с_репозиториями.md)
- [03 - Issues и Pull Requests](lessons/github_tutorials/github_cli_tutorials/03_работа_с_issues_и_pull_requests.md)
- [04 - GitHub Actions через CLI](lessons/github_tutorials/github_cli_tutorials/04_работа_с_github_actions.md)
- [05 - Расширенные возможности](lessons/github_tutorials/github_cli_tutorials/05_расширенные_возможности_и_интеграции.md)

### Интернационализация (i18n)
- [Введение в Flask-Babel](lessons/i18n/flask-babel.md)
- [Автоматический перевод](lessons/i18n/auto-translate.md)
- [Добавление языка](lessons/i18n/add-language.md)
- [Workflow с Babel CLI](lessons/i18n/babel-cli-workflow.md)
- [PyInstaller и i18n](lessons/i18n/pyinstaller.md)
- [Troubleshooting](lessons/i18n/troubleshooting.md)

## 🛠️ Обслуживание

- [Быстрая очистка](project_info/quick_cleanup.md) - Очистка ошибок GitHub Actions
- [Руководство по очистке репозитория](project_info/repo_cleanup_guide.md) - Очистка истории Git
- [Руководство по миграции](../MIGRATION_GUIDE.md) - Миграция со старых версий

## 📦 Инструменты резервного копирования

Документация в папке `backup_tools/`:
- [README](../backup_tools/README.md) - Обзор инструментов
- [Быстрый старт](../backup_tools/QUICK_START.md) - Начало работы
- [Индекс](../backup_tools/INDEX.md) - Полный индекс
- [Стратегия резервного копирования](../backup_tools/backup_strategy.md)

## 📌 Статус проекта

**Текущая версия**: v4.0.1  
**Дата последнего обновления**: 11 октября 2025  
**Статус**: ✅ Стабильная версия, все функции работают

### Известные проблемы
- ✅ ~~Проблема входа по PIN~~ - **ИСПРАВЛЕНО** в v4.0.1

### Следующие шаги
- Добавление новых функций управления серверами
- Улучшение UI/UX
- Расширение документации

---

**Нужна помощь?**
- Проверьте [FAQ](lessons/github-actions/GITHUB_ACTIONS_FAQ.md)
- Посмотрите [Troubleshooting](lessons/i18n/troubleshooting.md)
- Создайте Issue на GitHub

