#!/bin/bash

# Скрипт для отката к резервному состоянию
# Использование: ./rollback.sh [backup-branch-name]

set -e

echo "🔄 Скрипт отката к резервному состоянию"
echo "========================================"

# Определяем резервную ветку
if [ -n "$1" ]; then
    BACKUP_BRANCH="$1"
else
    BACKUP_BRANCH="backup/current-state-20250805-103439"
fi

echo "📋 Резервная ветка: $BACKUP_BRANCH"

# Проверяем существование ветки
if ! git show-ref --verify --quiet refs/remotes/origin/$BACKUP_BRANCH; then
    echo "❌ Ошибка: Резервная ветка $BACKUP_BRANCH не найдена"
    echo "Доступные резервные ветки:"
    git branch -r | grep backup/ || echo "Нет резервных веток"
    exit 1
fi

echo "⚠️  ВНИМАНИЕ: Это действие откатит все изменения!"
echo "Текущие изменения будут потеряны."
read -p "Продолжить? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Откат отменен"
    exit 1
fi

echo "🔄 Выполняем откат..."

# Сохраняем текущие изменения в stash (если есть)
if ! git diff-index --quiet HEAD --; then
    echo "💾 Сохраняем текущие изменения в stash..."
    git stash push -m "Auto-stash before rollback $(date)"
fi

# Переключаемся на резервную ветку
echo "🔄 Переключаемся на резервную ветку..."
git checkout $BACKUP_BRANCH

# Обновляем ветку
echo "🔄 Обновляем резервную ветку..."
git pull origin $BACKUP_BRANCH

echo "✅ Откат завершен успешно!"
echo "📋 Текущая ветка: $(git branch --show-current)"
echo "📋 Последний коммит: $(git log --oneline -1)"

echo ""
echo "💡 Полезные команды:"
echo "  - git log --oneline -10  # Посмотреть историю коммитов"
echo "  - git stash list         # Посмотреть сохраненные изменения"
echo "  - git stash pop          # Восстановить последние изменения"
echo "  - git branch -a          # Посмотреть все ветки" 