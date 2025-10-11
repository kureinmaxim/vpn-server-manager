### Babel CLI: рабочий цикл (extract → update → translate → compile)

#### Конфиг
Уже есть `babel.cfg`:
```
[python: **.py]
[jinja2: **/templates/**.html]
```

#### 1) Экстракция строк в POT
```bash
source venv/bin/activate && pybabel extract -F babel.cfg -o translations/messages.pot . | cat
```

#### 2) Обновление/создание каталогов переводов
- Обновить существующие:
```bash
source venv/bin/activate && pybabel update -i translations/messages.pot -d translations -l en -l zh | cat
```
- Создать новый язык (пример: de):
```bash
source venv/bin/activate && pybabel init -i translations/messages.pot -d translations -l de | cat
```

#### 3) Редактирование `.po`
Откройте `translations/<lang>/LC_MESSAGES/messages.po` и заполните `msgstr`.

#### 4) Компиляция `.mo`
```bash
source venv/bin/activate && pybabel compile -d translations | cat
```

Советы (Cursor/macOS):
- Всегда активируйте окружение: `source venv/bin/activate`
- Добавляйте `| cat`, чтобы избежать пейджера
- Если предупреждения про plural — проверьте формы множественного числа и ключ `Plural-Forms` в заголовке `.po` 