### Автоперевод PO-файлов (ускорение первичного наполнения)

Иногда удобно быстро заполнить `.po` черновыми переводами, чтобы UI не содержал пустых строк.

Мы добавили скрипт: `tools/auto_translate_po.py`
Он:
- защищает плейсхолдеры (`%(name)s`, `%s`)
- переводит с помощью Google (deep_translator)
- обрабатывает множественные формы
- периодически сохраняет прогресс, чтобы избежать потерь

#### Установка зависимостей (dev)
```bash
source venv/bin/activate && pip install deep-translator polib | cat
```

#### Запуск для английского или китайского
```bash
source venv/bin/activate && python3 tools/auto_translate_po.py en | cat
source venv/bin/activate && python3 tools/auto_translate_po.py zh | cat
```

#### Компиляция после автоперевода
```bash
source venv/bin/activate && pybabel compile -d translations | cat
```

Примечания и ограничения:
- Нужен интернет; возможно ограничение по скорости/квотам
- Машинный перевод — отправная точка; после — улучшайте вручную ключевые строки
- Скрипт коалесцирует `None` и обрабатывает plurals, но предупреждения Babel о формах возможны — см. «Траблшутинг» 