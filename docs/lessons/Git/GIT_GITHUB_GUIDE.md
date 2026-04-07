# 🔧 Руководство по работе с Git и GitHub для VPN Server Manager v4.0.0

Это руководство описывает работу с Git локально, использование .gitignore, и публикацию проекта на GitHub с использованием GitHub CLI (gh) и без него.

## 📋 Содержание

- [Настройка Git](#настройка-git)
- [Работа с .gitignore](#работа-с-gitignore)
- [Локальная работа с Git](#локальная-работа-с-git)
- [Публикация на GitHub с gh CLI](#публикация-на-github-с-gh-cli)
- [Публикация на GitHub без gh CLI](#публикация-на-github-без-gh-cli)
- [Создание релизов](#создание-релизов)
- [Работа с ветками](#работа-с-ветками)
- [GitHub Actions](#github-actions)
- [Troubleshooting](#troubleshooting)

## ⚙️ Настройка Git

### Первоначальная настройка
```bash
# Настройка пользователя
git config --global user.name "Ваше Имя"
git config --global user.email "your.email@example.com"

# Настройка редактора
git config --global core.editor "code --wait"  # VS Code
# или
git config --global core.editor "nano"

# Настройка автопереноса строк
git config --global core.autocrlf input  # macOS/Linux
git config --global core.autocrlf true   # Windows

# Настройка SSH ключей (рекомендуется)
ssh-keygen -t ed25519 -C "your.email@example.com"
ssh-add ~/.ssh/id_ed25519
```

### Проверка настроек
```bash
# Просмотр всех настроек
git config --list

# Просмотр конкретной настройки
git config user.name
git config user.email
```

## 📁 Работа с .gitignore

### Структура .gitignore для проекта

Наш `.gitignore` файл уже настроен для VPN Server Manager v4.0.0:

```gitignore
# Python
__pycache__/
*.py[cod]
*.so
.Python
build/
dist/
*.egg-info/

# Virtual environments
.env
.venv
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Application specific
logs/
uploads/
test_data/
data/servers.json.enc
data/hints.json
pin_block_state.json

# Security
*.key
*.pem
*.crt
*.p12
*.pfx

# Testing
.coverage
.pytest_cache/
htmlcov/

# Docker
.dockerignore
```

### Проверка .gitignore
```bash
# Проверка игнорируемых файлов
git status --ignored

# Проверка конкретного файла
git check-ignore data/servers.json.enc

# Принудительное добавление игнорируемого файла
git add -f data/servers.json.enc
```

### Обновление .gitignore
```bash
# Если нужно добавить новые правила
echo "new_pattern" >> .gitignore

# Удаление уже отслеживаемых файлов из Git
git rm --cached filename
git rm -r --cached directory/
```

## 🔄 Локальная работа с Git

### Инициализация репозитория
```bash
# Инициализация нового репозитория
git init

# Клонирование существующего репозитория
git clone https://github.com/username/vpn-server-manager.git
cd vpn-server-manager
```

### Основные команды
```bash
# Проверка статуса
git status

# Добавление файлов
git add .                    # Все файлы
git add filename.py          # Конкретный файл
git add app/                 # Директория
git add -A                   # Все изменения включая удаленные

# Коммит
git commit -m "feat: add new modular architecture"
git commit -am "fix: update version to 4.0.0"  # Добавить и закоммитить

# Просмотр истории
git log --oneline
git log --graph --oneline --all
git log -p filename.py       # История конкретного файла

# Просмотр изменений
git diff                    # Неиндексированные изменения
git diff --staged           # Индексированные изменения
git diff HEAD~1             # Изменения с последнего коммита
```

### Работа с ветками
```bash
# Создание и переключение на ветку
git checkout -b feature/new-architecture
git switch -c feature/new-architecture  # Новая команда

# Переключение между ветками
git checkout main
git switch main

# Список веток
git branch                  # Локальные ветки
git branch -a               # Все ветки
git branch -r               # Удаленные ветки

# Удаление ветки
git branch -d feature-branch
git branch -D feature-branch  # Принудительное удаление

# Слияние веток
git checkout main
git merge feature-branch
```

### Отмена изменений
```bash
# Отмена изменений в рабочей директории
git checkout -- filename.py
git restore filename.py     # Новая команда

# Отмена индексации
git reset HEAD filename.py
git restore --staged filename.py

# Отмена последнего коммита
git reset --soft HEAD~1     # Сохранить изменения
git reset --hard HEAD~1     # Удалить изменения

# Отмена до конкретного коммита
git reset --hard commit-hash
```

## 🚀 Публикация на GitHub с gh CLI

### Установка GitHub CLI
```bash
# macOS
brew install gh

# Ubuntu/Debian
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Windows
winget install GitHub.cli
```

### Аутентификация
```bash
# Вход в GitHub
gh auth login

# Выберите:
# - GitHub.com
# - HTTPS
# - Yes (authenticate Git with GitHub credentials)
# - Login with a web browser

# Проверка аутентификации
gh auth status
```

### Создание репозитория
```bash
# Создание публичного репозитория
gh repo create vpn-server-manager --public --description "VPN Server Manager v4.0.0 with modular architecture"

# Создание приватного репозитория
gh repo create vpn-server-manager --private --description "VPN Server Manager v4.0.0 with modular architecture"

# Создание с README
gh repo create vpn-server-manager --public --add-readme

# Клонирование созданного репозитория
gh repo clone username/vpn-server-manager
```

### Публикация кода
```bash
# Добавление удаленного репозитория
git remote add origin https://github.com/username/vpn-server-manager.git

# Первый push
git push -u origin main

# Последующие push
git push

# Push в конкретную ветку
git push origin feature-branch

# Force push (осторожно!)
git push --force-with-lease origin main
```

### Создание Pull Request
```bash
# Создание PR из текущей ветки
gh pr create --title "Add new modular architecture" --body "Description of changes"

# Создание PR с шаблоном
gh pr create --template .github/pull_request_template.md

# Список PR
gh pr list

# Просмотр PR
gh pr view 123

# Мерж PR
gh pr merge 123 --merge
gh pr merge 123 --squash
gh pr merge 123 --rebase
```

### Создание Issues
```bash
# Создание issue
gh issue create --title "Bug: Application crashes on startup" --body "Detailed description"

# Список issues
gh issue list

# Закрытие issue
gh issue close 123
```

## 🌐 Публикация на GitHub без gh CLI

### Создание репозитория через веб-интерфейс
1. Перейдите на [GitHub.com](https://github.com)
2. Нажмите "New repository"
3. Заполните:
   - Repository name: `vpn-server-manager`
   - Description: `VPN Server Manager v4.0.0 with modular architecture`
   - Visibility: Public/Private
   - Initialize with README: No (у нас уже есть файлы)

### Настройка локального репозитория
```bash
# Инициализация Git (если еще не сделано)
git init

# Добавление всех файлов
git add .

# Первый коммит
git commit -m "feat: initial commit with v4.0.0 modular architecture"

# Добавление удаленного репозитория
git remote add origin https://github.com/username/vpn-server-manager.git

# Переименование ветки в main (если нужно)
git branch -M main

# Первый push
git push -u origin main
```

### Работа с ветками
```bash
# Создание feature ветки
git checkout -b feature/new-feature

# Внесение изменений и коммит
git add .
git commit -m "feat: add new feature"

# Push ветки
git push -u origin feature/new-feature

# Создание PR через веб-интерфейс GitHub
```

## 🏷️ Создание релизов

### С gh CLI
```bash
# Создание релиза
gh release create v4.0.0 \
  --title "VPN Server Manager v4.0.0" \
  --notes "Major release with modular architecture" \
  --latest

# Создание релиза с файлами
gh release create v4.0.0 \
  --title "VPN Server Manager v4.0.0" \
  --notes "Major release with modular architecture" \
  dist/VPNServerManager-Clean_Installer.dmg \
  --latest

# Создание draft релиза
gh release create v4.0.0 \
  --title "VPN Server Manager v4.0.0" \
  --notes "Major release with modular architecture" \
  --draft

# Список релизов
gh release list

# Просмотр релиза
gh release view v4.0.0
```

### Без gh CLI (через веб-интерфейс)
1. Перейдите в раздел "Releases" на GitHub
2. Нажмите "Create a new release"
3. Заполните:
   - Tag version: `v4.0.0`
   - Release title: `VPN Server Manager v4.0.0`
   - Description: Описание изменений
4. Прикрепите файлы (DMG, архив)
5. Нажмите "Publish release"

### Автоматическое создание релизов
```bash
# Создание тега
git tag -a v4.0.0 -m "Release version 4.0.0"
git push origin v4.0.0

# Создание аннотированного тега
git tag -a v4.0.0 -m "Release version 4.0.0" commit-hash
```

## 🌿 Работа с ветками

### Git Flow (рекомендуемый подход)
```bash
# Основные ветки
main                    # Production код
develop                 # Development код
feature/*              # Новые функции
hotfix/*               # Критические исправления
release/*              # Подготовка релизов

# Создание feature ветки
git checkout develop
git pull origin develop
git checkout -b feature/new-architecture
git push -u origin feature/new-architecture

# Завершение feature
git checkout develop
git merge feature/new-architecture
git push origin develop
git branch -d feature/new-architecture
```

### GitHub Flow (простой подход)
```bash
# Основные ветки
main                    # Production код
feature/*              # Новые функции

# Создание feature ветки
git checkout main
git pull origin main
git checkout -b feature/new-feature
git push -u origin feature/new-feature

# Завершение через PR
# Создать PR через GitHub веб-интерфейс или gh CLI
```

## ⚡ GitHub Actions

### Создание workflow файла
```bash
# Создание директории
mkdir -p .github/workflows

# Создание workflow файла
cat > .github/workflows/ci.yml << 'EOF'
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest
    
    - name: Run linting
      run: |
        flake8 app tests
        black --check app tests
EOF
```

### Workflow для релизов
```bash
cat > .github/workflows/release.yml << 'EOF'
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest
    
    - name: Build application
      run: |
        python build_macos.py
    
    - name: Create Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        draft: false
        prerelease: false
EOF
```

## 🔧 Troubleshooting

### Частые проблемы

#### 1. Конфликты при merge
```bash
# Просмотр конфликтов
git status

# Разрешение конфликтов
# Отредактируйте файлы с конфликтами
git add resolved-file.py
git commit -m "resolve merge conflict"
```

#### 2. Отмена последнего push
```bash
# Отмена последнего коммита локально
git reset --hard HEAD~1

# Force push (осторожно!)
git push --force-with-lease origin main
```

#### 3. Проблемы с аутентификацией
```bash
# Обновление токена
gh auth refresh

# Проверка SSH ключей
ssh -T git@github.com

# Переключение на HTTPS
git remote set-url origin https://github.com/username/repo.git
```

#### 4. Большие файлы
```bash
# Удаление больших файлов из истории
git filter-branch --tree-filter 'rm -f large-file.zip' HEAD

# Использование Git LFS
git lfs track "*.dmg"
git lfs track "*.zip"
git add .gitattributes
```

#### 5. Проблемы с .gitignore
```bash
# Очистка кеша Git
git rm -r --cached .
git add .
git commit -m "fix: update .gitignore"

# Проверка игнорируемых файлов
git status --ignored
```

### Полезные команды

#### Очистка репозитория
```bash
# Удаление неиспользуемых веток
git branch --merged | grep -v main | xargs -n 1 git branch -d

# Очистка удаленных веток
git remote prune origin

# Очистка неотслеживаемых файлов
git clean -fd
```

#### Информация о репозитории
```bash
# Размер репозитория
du -sh .git

# Статистика коммитов
git shortlog -sn

# Статистика файлов
git ls-files | xargs wc -l
```

## 📝 Примеры workflow

### Ежедневная работа
```bash
# Утром
git checkout main
git pull origin main
git checkout -b feature/daily-work

# Работа
# ... вносим изменения ...

# Вечером
git add .
git commit -m "feat: add daily improvements"
git push -u origin feature/daily-work

# Создание PR
gh pr create --title "Daily improvements" --body "Description"
```

### Подготовка релиза
```bash
# Создание release ветки
git checkout main
git pull origin main
git checkout -b release/v4.0.0

# Обновление версии
# ... обновляем версию в файлах ...

git add .
git commit -m "chore: bump version to 4.0.0"
git push -u origin release/v4.0.0

# Создание PR
gh pr create --title "Release v4.0.0" --body "Release notes"

# После мержа
git checkout main
git pull origin main
git tag -a v4.0.0 -m "Release version 4.0.0"
git push origin v4.0.0

# Создание релиза
gh release create v4.0.0 --title "VPN Server Manager v4.0.0" --latest
```

## 🔗 Полезные ссылки

- [Git Documentation](https://git-scm.com/doc)
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## 📞 Поддержка

При возникновении проблем:

1. Проверьте статус: `git status`
2. Посмотрите логи: `git log --oneline`
3. Проверьте .gitignore: `git status --ignored`
4. Создайте issue в репозитории с подробным описанием проблемы

---

**Примечание**: Это руководство актуально для VPN Server Manager v4.0.0 с новой модульной архитектурой.
