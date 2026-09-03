"""Default UI language after a fresh session (installed app)."""


def test_fresh_session_defaults_to_english_not_browser_locale(client):
    response = client.get(
        '/locked',
        headers={'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'},
    )
    assert response.status_code == 200
    assert b'Access Restricted' in response.data
    assert b'lang="en"' in response.data
    with client.session_transaction() as sess:
        assert sess.get('language') == 'en'


def test_change_language_to_russian_persists(client):
    client.get('/change_language/ru')
    response = client.get('/locked')
    assert response.status_code == 200
    assert 'Доступ ограничен'.encode('utf-8') in response.data
    with client.session_transaction() as sess:
        assert sess.get('language') == 'ru'
