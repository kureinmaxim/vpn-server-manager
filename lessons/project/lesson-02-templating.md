# Урок 2: Шаблонизация и Динамический Контент

## 🎯 Цели урока

К концу этого урока вы будете понимать:
- Историю развития шаблонизации в веб-разработке
- Принципы работы Jinja2
- Синтаксис шаблонов и фильтры
- Наследование шаблонов и компоненты
- Контекстные процессоры и глобальные переменные

## 📚 Историческая справка

### Эволюция шаблонизации

```mermaid
timeline
    title История развития систем шаблонизации
    
    1995 : Server-Side Includes (SSI)
         : <!--#include virtual="header.html" -->
         : Простое включение файлов
    
    1999 : PHP Templates
         : Смешивание HTML и PHP кода
         : <?php echo $variable; ?>
    
    2003 : Smarty (PHP)
         : Разделение логики и представления
         : {$variable} синтаксис
    
    2005 : Django Templates
         : {{ variable }} и {% tag %}
         : Автоэкранирование HTML
    
    2008 : Jinja2
         : Armin Ronacher создает Jinja2
         : Вдохновлен Django Templates
    
    2010 : Mustache
         : Логикаless шаблоны
         : Кроссплатформенность
    
    2013 : React JSX
         : Компонентный подход
         : JavaScript в HTML
    
    2020 : Modern Era
         : Компонентные фреймворки
         : Server-Side Rendering (SSR)
```

### История Jinja2

**Jinja2** был создан **Армином Ронахером** в 2008 году как улучшенная версия оригинального Jinja. Основные принципы:

1. **Безопасность** — автоматическое экранирование HTML
2. **Производительность** — компиляция в Python-код
3. **Гибкость** — богатая система фильтров и функций
4. **Читаемость** — понятный синтаксис

**Философия Jinja2**: "Мощность Python с безопасностью шаблонов"

## 🏗️ Архитектура шаблонизации

### Принцип работы системы шаблонов

```mermaid
graph TD
    A[Шаблон .html] -->|Парсинг| B[AST - Абстрактное синтаксическое дерево]
    B -->|Компиляция| C[Python код]
    C -->|Кэширование| D[Скомпилированный шаблон]
    E[Данные контекста] -->|Передача| D
    D -->|Рендеринг| F[HTML результат]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fce4ec
    style F fill:#f1f8e9
```

### Компоненты Jinja2

```mermaid
graph TB
    subgraph "Jinja2 Engine"
        A[Environment]
        B[Loader]
        C[Template]
        D[Context]
        E[Filters]
        F[Functions]
        G[Tests]
    end
    
    A --> B
    A --> E
    A --> F
    A --> G
    B --> C
    C --> D
    D --> H[Rendered Output]
    
    subgraph "Template Types"
        I[Base Templates]
        J[Child Templates]
        K[Macros]
        L[Includes]
    end
    
    C --> I
    C --> J
    C --> K
    C --> L
    
    style A fill:#4caf50,color:white
    style H fill:#2196f3,color:white
```

## 💻 Синтаксис Jinja2

### Базовые конструкции

```html
<!-- Переменные -->
{{ variable_name }}
{{ user.name }}
{{ items[0] }}

<!-- Теги управления -->
{% if condition %}
    <p>Условие истинно</p>
{% elif other_condition %}
    <p>Другое условие</p>
{% else %}
    <p>Все условия ложны</p>
{% endif %}

<!-- Циклы -->
{% for item in items %}
    <li>{{ item.name }}</li>
{% endfor %}

<!-- Комментарии -->
{# Это комментарий, не попадет в HTML #}
```

### Фильтры в Jinja2

```html
<!-- Встроенные фильтры -->
{{ name|upper }}                    <!-- JOHN -->
{{ price|round(2) }}               <!-- 19.99 -->
{{ content|safe }}                 <!-- Без экранирования HTML -->
{{ items|length }}                 <!-- Количество элементов -->
{{ date|strftime('%Y-%m-%d') }}    <!-- Форматирование даты -->

<!-- Цепочки фильтров -->
{{ text|lower|replace(' ', '_')|title }}
```

### Наследование шаблонов

**Базовый шаблон (`base.html`):**
```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}VPN Server Manager{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
    <header>
        <nav>
            {% block navigation %}
            <ul>
                <li><a href="{{ url_for('index') }}">Главная</a></li>
                <li><a href="{{ url_for('add_server') }}">Добавить</a></li>
            </ul>
            {% endblock %}
        </nav>
    </header>
    
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <footer>
        {% block footer %}
        <p>&copy; 2024 VPN Server Manager</p>
        {% endblock %}
    </footer>
    
    {% block scripts %}{% endblock %}
</body>
</html>
```

**Дочерний шаблон (`servers.html`):**
```html
{% extends "base.html" %}

{% block title %}Список серверов - {{ super() }}{% endblock %}

{% block content %}
<h1>Мои VPN серверы</h1>

{% if servers %}
    <div class="servers-grid">
    {% for server in servers %}
        <div class="server-card">
            <h3>{{ server.name }}</h3>
            <p>IP: {{ server.ip }}</p>
            <p>Статус: 
                {% if server.status == 'active' %}
                    <span class="status-active">Активен</span>
                {% else %}
                    <span class="status-inactive">Неактивен</span>
                {% endif %}
            </p>
        </div>
    {% endfor %}
    </div>
{% else %}
    <p class="no-servers">Серверы не найдены.</p>
{% endif %}
{% endblock %}

{% block scripts %}
<script>
    console.log('Загружено серверов: {{ servers|length }}');
</script>
{% endblock %}
```

## 🔧 Продвинутые возможности

### Макросы в Jinja2

```html
<!-- Определение макроса -->
{% macro render_server_card(server) %}
<div class="server-card" data-id="{{ server.id }}">
    <div class="server-header">
        <h3>{{ server.name }}</h3>
        {% if server.icon %}
            <img src="{{ url_for('uploaded_file', filename=server.icon) }}" 
                 alt="{{ server.name }}" class="server-icon">
        {% endif %}
    </div>
    
    <div class="server-info">
        <p><strong>IP:</strong> {{ server.ip }}</p>
        <p><strong>Провайдер:</strong> {{ server.provider or 'Неизвестно' }}</p>
        
        {% if server.last_check %}
            <p><strong>Последняя проверка:</strong> 
               {{ server.last_check|format_datetime }}</p>
        {% endif %}
    </div>
    
    <div class="server-actions">
        <a href="{{ url_for('edit_server', server_id=server.id) }}" 
           class="btn btn-primary">Редактировать</a>
        <button class="btn btn-danger" 
                onclick="deleteServer({{ server.id }})">Удалить</button>
    </div>
</div>
{% endmacro %}

<!-- Использование макроса -->
{% for server in servers %}
    {{ render_server_card(server) }}
{% endfor %}
```

### Включения (Includes)

```html
<!-- _server_card.html -->
<div class="server-card">
    <h3>{{ server.name }}</h3>
    <p>{{ server.ip }}</p>
</div>

<!-- main.html -->
{% for server in servers %}
    {% include '_server_card.html' %}
{% endfor %}
```

### Условные выражения

```html
<!-- Тернарный оператор -->
<span class="status {{ 'online' if server.online else 'offline' }}">
    {{ 'Онлайн' if server.online else 'Офлайн' }}
</span>

<!-- Сложные условия -->
{% if server.provider and server.provider.lower() in ['aws', 'digitalocean'] %}
    <span class="cloud-provider">☁️ Облачный</span>
{% elif server.ip.startswith('192.168.') %}
    <span class="local-server">🏠 Локальный</span>
{% else %}
    <span class="dedicated-server">🖥️ Выделенный</span>
{% endif %}
```

## 🎨 Кастомные фильтры

### Создание собственных фильтров

```python
# app.py
from datetime import datetime
import re

def format_datetime_filter(iso_str):
    """Форматирует ISO строку в читаемый формат."""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime('%d.%m.%Y %H:%M')
    except (ValueError, TypeError):
        return iso_str

def mask_sensitive_filter(text, chars_to_show=4):
    """Маскирует чувствительную информацию."""
    if not text or len(text) <= chars_to_show:
        return text
    return text[:chars_to_show] + '*' * (len(text) - chars_to_show)

def file_size_filter(bytes_count):
    """Конвертирует байты в читаемый формат."""
    if bytes_count == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    
    while bytes_count >= 1024 and i < len(units) - 1:
        bytes_count /= 1024.0
        i += 1
    
    return f"{bytes_count:.1f} {units[i]}"

# Регистрация фильтров
app.jinja_env.filters['format_datetime'] = format_datetime_filter
app.jinja_env.filters['mask_sensitive'] = mask_sensitive_filter
app.jinja_env.filters['file_size'] = file_size_filter
```

### Использование кастомных фильтров

```html
<!-- В шаблонах -->
<p>Создан: {{ server.created_at|format_datetime }}</p>
<p>Пароль: {{ server.password|mask_sensitive(3) }}</p>
<p>Размер лога: {{ log_file_size|file_size }}</p>
```

## 🌍 Контекстные процессоры

### Глобальные переменные в шаблонах

```python
# app.py
@app.context_processor
def inject_app_info():
    """Добавляет информацию о приложении во все шаблоны."""
    return {
        'app_info': app.config.get('app_info', {}),
        'current_year': datetime.now().year,
        'version': app.config.get('version', 'Unknown')
    }

@app.context_processor
def inject_service_urls():
    """Добавляет URL сервисов во все шаблоны."""
    return {
        'service_urls': app.config.get('service_urls', {}),
        'active_data_file': app.config.get('active_data_file')
    }

@app.context_processor
def inject_navigation():
    """Добавляет навигационное меню."""
    navigation_items = [
        {'url': url_for('index'), 'title': 'Серверы', 'icon': '🖥️'},
        {'url': url_for('add_server'), 'title': 'Добавить', 'icon': '➕'},
        {'url': url_for('settings'), 'title': 'Настройки', 'icon': '⚙️'},
        {'url': url_for('help'), 'title': 'Справка', 'icon': '❓'},
    ]
    return {'navigation_items': navigation_items}
```

## 📊 Анализ шаблонов в проекте

### Базовый шаблон (`layout.html`)

```html
<!-- layout.html - основа всех страниц -->
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}VPN Server Manager{% endblock %}</title>
    
    <!-- Динамические мета-теги -->
    {% block meta %}{% endblock %}
    
    <!-- CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block styles %}{% endblock %}
</head>
<body data-theme="{{ request.cookies.get('theme', 'light') }}">
    <!-- Навигация -->
    <nav class="navbar">
        <div class="nav-brand">
            <h1>🔐 VPN Manager</h1>
            <span class="version">v{{ app_info.version }}</span>
        </div>
        
        <ul class="nav-menu">
            {% for item in navigation_items %}
            <li class="nav-item">
                <a href="{{ item.url }}" 
                   class="nav-link {{ 'active' if request.endpoint == item.endpoint }}">
                    {{ item.icon }} {{ item.title }}
                </a>
            </li>
            {% endfor %}
        </ul>
        
        <!-- Масштабирование UI -->
        <div class="ui-scale-control">
            <select onchange="changeUIScale(this.value)">
                <option value="80">80%</option>
                <option value="90">90%</option>
                <option value="100" selected>100%</option>
            </select>
        </div>
    </nav>
    
    <!-- Основной контент -->
    <main class="main-content">
        <!-- Flash сообщения -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash-messages">
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
                </div>
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </main>
    
    <!-- Футер -->
    <footer class="footer">
        <p>&copy; {{ current_year }} {{ app_info.developer or 'VPN Server Manager' }}</p>
        {% if app_info.last_updated %}
            <p>Обновлено: {{ app_info.last_updated|format_datetime }}</p>
        {% endif %}
    </footer>
    
    <!-- JavaScript -->
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Шаблон списка серверов (`index.html`)

```html
{% extends "layout.html" %}

{% block title %}Список серверов{% endblock %}

{% block content %}
<div class="servers-container">
    <div class="servers-header">
        <h2>Мои VPN серверы ({{ servers|length }})</h2>
        <a href="{{ url_for('add_server') }}" class="btn btn-primary">
            ➕ Добавить сервер
        </a>
    </div>
    
    {% if servers %}
        <div class="servers-grid">
        {% for server in servers %}
            <div class="server-card" data-server-id="{{ server.id }}">
                <!-- Иконка сервера -->
                <div class="server-icon">
                    {% if server.icon %}
                        <img src="{{ url_for('uploaded_file', filename=server.icon) }}" 
                             alt="{{ server.name }}">
                    {% else %}
                        <div class="default-icon">🖥️</div>
                    {% endif %}
                </div>
                
                <!-- Информация о сервере -->
                <div class="server-info">
                    <h3>{{ server.name }}</h3>
                    <p class="server-ip">{{ server.ip }}</p>
                    
                    {% if server.provider %}
                        <p class="server-provider">{{ server.provider }}</p>
                    {% endif %}
                    
                    <!-- Статус подключения -->
                    <div class="server-status" id="status-{{ server.id }}">
                        <span class="status-indicator">⏳</span>
                        <span class="status-text">Проверка...</span>
                    </div>
                </div>
                
                <!-- Действия -->
                <div class="server-actions">
                    <a href="{{ url_for('edit_server', server_id=server.id) }}" 
                       class="btn btn-sm btn-outline">Редактировать</a>
                    <button class="btn btn-sm btn-danger" 
                            onclick="deleteServer('{{ server.id }}')">Удалить</button>
                </div>
            </div>
        {% endfor %}
        </div>
    {% else %}
        <div class="empty-state">
            <div class="empty-icon">📡</div>
            <h3>Серверы не найдены</h3>
            <p>Добавьте свой первый VPN сервер</p>
            <a href="{{ url_for('add_server') }}" class="btn btn-primary">
                Добавить сервер
            </a>
        </div>
    {% endif %}
</div>
{% endblock %}

{% block scripts %}
<script>
// Проверка статуса серверов
document.addEventListener('DOMContentLoaded', function() {
    {% for server in servers %}
        checkServerStatus('{{ server.ip }}', '{{ server.id }}');
    {% endfor %}
});

function checkServerStatus(ip, serverId) {
    fetch(`/check_ip/${ip}`)
        .then(response => response.json())
        .then(data => {
            const statusElement = document.getElementById(`status-${serverId}`);
            const indicator = statusElement.querySelector('.status-indicator');
            const text = statusElement.querySelector('.status-text');
            
            if (data.error) {
                indicator.textContent = '❌';
                text.textContent = 'Недоступен';
                statusElement.className = 'server-status status-error';
            } else {
                indicator.textContent = '✅';
                text.textContent = 'Доступен';
                statusElement.className = 'server-status status-success';
                
                // Анализ хостинга
                const hostingQuality = analyzeHosting(data);
                statusElement.insertAdjacentHTML('beforeend', 
                    `<span class="hosting-quality ${hostingQuality.class}">
                        ${hostingQuality.text}
                     </span>`);
            }
        })
        .catch(error => {
            console.error('Ошибка проверки сервера:', error);
        });
}
</script>
{% endblock %}
```

## 🚀 Практические упражнения

### Упражнение 1: Базовые шаблоны

Создайте систему шаблонов:
1. Базовый шаблон с навигацией
2. Шаблон главной страницы
3. Шаблон страницы "О нас"

### Упражнение 2: Кастомные фильтры

Создайте фильтры:
1. `truncate_words(n)` — обрезание по словам
2. `plural(count, forms)` — склонение по числам
3. `highlight(query)` — подсветка текста

### Упражнение 3: Макросы

Создайте макросы:
1. Карточка товара
2. Форма с валидацией
3. Пагинация

## 📊 Диаграмма потока рендеринга

```mermaid
sequenceDiagram
    participant V as View Function
    participant F as Flask
    participant J as Jinja2
    participant T as Template
    participant C as Context
    participant R as Rendered HTML
    
    V->>F: render_template('index.html', servers=data)
    F->>J: Request template rendering
    J->>T: Load template file
    T->>J: Parse template syntax
    J->>C: Apply context data
    C->>J: Process filters & functions
    J->>R: Generate HTML output
    R->>F: Return rendered content
    F->>V: HTML response
```

## 🔒 Безопасность в шаблонах

### Автоэкранирование HTML

```html
<!-- Безопасное отображение пользовательского контента -->
<p>{{ user_input }}</p>  <!-- Автоматически экранируется -->

<!-- Отключение экранирования (опасно!) -->
<p>{{ trusted_html|safe }}</p>

<!-- Принудительное экранирование -->
<p>{{ potentially_safe_content|e }}</p>
```

### Защита от XSS

```html
<!-- ❌ Опасно -->
<script>var userName = "{{ user.name }}";</script>

<!-- ✅ Безопасно -->
<script>var userName = {{ user.name|tojson }};</script>

<!-- ✅ Еще лучше -->
<div data-user-name="{{ user.name }}"></div>
<script>
const userName = document.querySelector('[data-user-name]').dataset.userName;
</script>
```

## 🌟 Лучшие практики

### 1. Структура шаблонов
```
templates/
├── base.html              # Базовый шаблон
├── layout/
│   ├── navbar.html        # Навигация
│   └── footer.html        # Футер
├── components/
│   ├── server_card.html   # Компонент карточки
│   └── form_field.html    # Компонент поля формы
├── pages/
│   ├── index.html         # Страницы
│   └── about.html
└── emails/                # Email шаблоны
    └── welcome.html
```

### 2. Именование переменных
```html
<!-- ✅ Хорошо -->
{{ server.name }}
{{ user.email }}
{{ config.database_url }}

<!-- ❌ Плохо -->
{{ s.n }}
{{ data[0] }}
{{ cfg['db'] }}
```

### 3. Комментирование
```html
{# Карточка сервера - компонент для отображения информации о VPN сервере #}
{% macro server_card(server) %}
    {# Проверяем доступность основной информации #}
    {% if server.name and server.ip %}
        <div class="server-card">
            {# ... содержимое карточки ... #}
        </div>
    {% endif %}
{% endmacro %}
```

## 📚 Дополнительные материалы

### Полезные ссылки
- [Документация Jinja2](https://jinja.palletsprojects.com/)
- [Flask Templates Guide](https://flask.palletsprojects.com/en/2.3.x/templating/)
- [Jinja2 Extensions](https://github.com/pallets/jinja/tree/main/src/jinja2/ext)

### Расширения Jinja2
- **jinja2-time** — работа с датами и временем
- **jinja2-humanize** — человекочитаемые форматы
- **jinja2-markdown** — рендеринг Markdown

## 🎯 Контрольные вопросы

1. Как работает наследование шаблонов в Jinja2?
2. В чем разница между `{% include %}` и `{% extends %}`?
3. Когда использовать макросы вместо включений?
4. Как создать кастомный фильтр для форматирования?
5. Что такое контекстные процессоры и зачем они нужны?

## 🚀 Следующий урок

В следующем уроке мы изучим **работу с формами и обработку данных**, научимся валидировать пользовательский ввод и реализуем безопасную загрузку файлов.

---

*Этот урок является частью курса "VPN Server Manager: Архитектура и принципы разработки"*
