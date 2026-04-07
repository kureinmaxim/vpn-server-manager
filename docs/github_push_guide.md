# GitHub Push Guide

Короткий практический сценарий для публикации изменений и релиза.

## Базовый цикл

```bash
git status
git add <files>
git commit -m "type: short summary"
git push origin main
```

Если репозиторий требует Pull Request, используйте PR вместо прямого push.

## Релиз и версия

Версия релиза берётся из:

- `config/config.json.template`

Проверка:

```text
python tools/update_version.py status
```

Создание тега:

```bash
VERSION=$(jq -r .app_info.version config/config.json.template)
TAG=v$VERSION
git tag -a "$TAG" -m "Release $VERSION"
git push origin "$TAG"
```

Подробный релизный процесс:

- `release_guide.md`
- `../VERSION_MANAGEMENT.md`
