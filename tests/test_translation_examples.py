import re

import pytest
from babel.messages.pofile import read_po


def catalog(lang):
    with open(f'translations/{lang}/LC_MESSAGES/messages.po', 'rb') as handle:
        return read_po(handle)


@pytest.mark.parametrize('lang', ['en', 'zh'])
def test_examples_and_placeholders_survive_translation(lang):
    """«Например, 1.2.3.4» must not become «For example, Ubuntu 22.04»; {name}/%(name)s must be kept."""
    broken = []
    for message in catalog(lang):
        if not isinstance(message.id, str) or not message.string:
            continue
        example = re.fullmatch(r'Например, (.+)', message.id)
        if example and re.fullmatch(r'[A-Za-z0-9 .,_:/@()+-]+', example.group(1)) \
                and example.group(1) not in message.string:
            broken.append(message.id)
        for placeholder in re.findall(r'%\(\w+\)s|\{\w+\}', message.id):
            if placeholder not in message.string:
                broken.append(message.id)
    assert broken == []


@pytest.mark.parametrize('lang,terms', [
    ('en', ('stop', 'start', 'disable', 'receipt', 'hint')),
    ('zh', ('停止', '启动', '禁用', '收据', '提示')),
])
def test_action_and_receipt_meanings_are_not_swapped(lang, terms):
    """Protect reviewed meanings: stop != install/restart; receipt != server/hint."""
    messages = catalog(lang)
    stop, start, disable, receipt, hint = terms
    for source in ('Остановить службу:', 'Остановить контейнер:', 'Остановить NGINX:'):
        assert stop in messages[source].string.lower()
    assert start in messages['Запустить службу:'].string.lower()
    assert disable in messages['Отключить автозапуск службы:'].string.lower()
    for source in ('Управление чеками', 'Добавить новый чек', 'Описание чека',
                   'Вы уверены, что хотите удалить этот чек? Это действие необратимо.'):
        assert receipt in messages[source].string.lower()
        assert hint not in messages[source].string.lower()
    assert hint in messages['Управление подсказками'].string.lower()
    assert messages['Остановить службу:'].string != messages['Перезапустить службу:'].string
