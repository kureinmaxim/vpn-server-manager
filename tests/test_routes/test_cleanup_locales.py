import pytest
from .test_reset import reset_client


@pytest.mark.parametrize('lang,expected', [('en', ['TelegramOnly cleanup', 'Cleanup archives', 'Disk usage']), ('zh', ['清理 TelegramOnly', '清理备份', '磁盘用量']), ('ru', ['Очистка TelegramOnly', 'Архивы очистки', 'Место на диске'])])
def test_new_page_locales(reset_client, lang, expected):
    pages = ['/servers/one/reset', '/servers/one/reset/archives', '/servers/one/disk-usage']
    for path, title in zip(pages, expected):
        response = reset_client.get(path + '?lang=' + lang)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert title in html
        if lang != 'ru':
            assert 'Проверяю сервер.' not in html
            assert 'Читаю список архивов' not in html
            assert 'Проверяю диск.' not in html


def test_cleanup_api_uses_selected_language(reset_client):
    reset_client.get('/servers/one/reset?lang=en')
    response = reset_client.post('/api/servers/one/reset/plan', json={'components': []}, headers={'X-CSRF-Token': 'test-csrf'})
    assert response.json['error'] == 'Select components from the list'
