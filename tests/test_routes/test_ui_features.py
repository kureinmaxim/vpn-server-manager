from app.services.ui_preferences import load_ui_features, save_ui_features, save_ui_preferences


def _login(client):
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, csrf_token='test-csrf')


def test_new_install_hides_personal_tools(app, client):
    assert load_ui_features(app) == {'dns': True, 'load': True, 'projects': False, 'bots': False}
    _login(client)
    page = client.get('/').get_data(as_text=True)
    assert 'data-bs-target="#loadCheckModal"' in page
    assert 'data-bs-target="#projectsCheckModal"' not in page and 'id="projectsCheckModal"' not in page
    assert 'data-bs-target="#botsCheckModal"' not in page and 'id="botsCheckModal"' not in page


def test_settings_switches_tools_and_keeps_language(app, client):
    save_ui_preferences(app, language='en', zoom='100')
    _login(client)
    assert client.post('/settings/features', data={'features': ['bots']}).status_code in (302, 403)
    response = client.post('/settings/features', data={'csrf_token': 'test-csrf', 'features': ['bots', 'unknown']})
    assert response.status_code == 302
    assert load_ui_features(app) == {'dns': False, 'load': False, 'projects': False, 'bots': True}
    page = client.get('/').get_data(as_text=True)
    assert 'data-bs-target="#botsCheckModal"' in page and 'data-bs-target="#loadCheckModal"' not in page
    # Сохранение языка и масштаба не стирает выбор кнопок
    save_ui_preferences(app, zoom='60')
    assert load_ui_features(app)['bots'] is True


def test_settings_page_lists_switches(app, client):
    _login(client)
    page = client.get('/settings').get_data(as_text=True)
    for name in ('dns', 'load', 'projects', 'bots'):
        assert f'id="feature-{name}"' in page
    save_ui_features(app, ['projects'])
    assert 'id="feature-projects" checked' in client.get('/settings').get_data(as_text=True)
