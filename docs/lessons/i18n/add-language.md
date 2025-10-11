### Добавление нового языка

#### 1) Экспорт POT
```bash
source venv/bin/activate && pybabel extract -F babel.cfg -o translations/messages.pot . | cat
```

#### 2) Инициализация каталога языка (пример: испанский `es`)
```bash
source venv/bin/activate && pybabel init -i translations/messages.pot -d translations -l es | cat
```
Создаст `translations/es/LC_MESSAGES/messages.po`.

#### 3) Перевод `.po`
Заполните `msgstr` в `messages.po`.

Совет: можно быстро накинуть черновой перевод:
```bash
source venv/bin/activate && python3 tools/auto_translate_po.py es | cat
```
(При необходимости добавьте язык-цель в скрипт.)

#### 4) Компиляция
```bash
source venv/bin/activate && pybabel compile -d translations | cat
```

#### 5) Переключатель в UI
Добавьте ссылку/кнопку на `/language/es`. 