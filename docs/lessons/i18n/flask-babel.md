### Flask-Babel: базовая интеграция

Этот метод — основной для Flask-приложений. Он использует `Flask-Babel` и файлы переводов `.po/.mo`.

#### 1) Установка зависимостей (dev)
```bash
source venv/bin/activate && pip install Flask-Babel Babel | cat
```

#### 2) Инициализация в коде
В `app.py` уже подключён Babel. Ключевые моменты:
- Инициализация: `babel = Babel(app)`
- Селектор локали (пример):
```python
from flask_babel import Babel, gettext as _

babel = Babel(app)

@babel.locale_selector
def get_locale():
    # возвращает 'ru', 'en', 'zh' по сессии/заголовкам
    return session.get('language', 'ru')
```

#### 3) Использование в шаблонах и коде
- В шаблонах Jinja2:
```html
{{ _('Добавить сервер') }}
{{ ngettext('%(num)d запись', '%(num)d записей', num) % {'num': num} }}
```
- В Python:
```python
from flask_babel import gettext as _, ngettext
flash(_('Успех'), 'success')
```

#### 4) Структура переводов
```
translations/
  en/LC_MESSAGES/messages.po
  zh/LC_MESSAGES/messages.po
  ru/LC_MESSAGES/messages.po  # опционально
```

#### 5) Переключатель языка
В `app.py` уже есть маршрут, который меняет язык в `session` и делает redirect. В UI добавьте ссылки на `/language/en`, `/language/ru`, `/language/zh`.

#### 6) Компиляция переводов
После редактирования `.po` обязательно компилируйте:
```bash
source venv/bin/activate && pybabel compile -d translations | cat
```

#### 7) Рекомендации
- Все тексты, видимые пользователю, оборачивайте в `_(...)`
- Для множественных форм используйте `ngettext(...)`
- Сохраняйте плейсхолдеры вида `%(name)s` — они должны совпадать во всех переводах 