# Git Guide

Этот файл теперь служит короткой точкой входа по Git и GitHub для проекта `VPN Server Manager`.

## Для повседневной работы

- `git status`
- `git add <files>`
- `git commit -m "type: summary"`
- `git push origin <branch>`

## Для релизов

Используйте актуальные документы:

- `github_push_guide.md`
- `release_guide.md`
- `../VERSION_MANAGEMENT.md`

## Важно для этого проекта

- версия релиза синхронизируется через `tools/update_version.py`;
- источник правды для версии: `config/config.json.template`;
- локальный `config.json` не должен использоваться как источник версии репозитория.

Если нужен исторический контекст старых Git-инструкций, используйте git history для предыдущих ревизий этого файла.
