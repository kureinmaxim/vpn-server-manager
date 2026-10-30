from app.services.bot_stats import load_bots
from app.services.project_stats import load_projects
from app.services.ui_preferences import (load_ui_features, save_ui_features, save_ui_preferences,
                                          ui_features_configured)


def _login(client):
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, csrf_token='test-csrf')


def test_new_install_hides_personal_tools(app, client):
    assert load_ui_features(app) == {'dns': True, 'load': True, 'projects': False, 'bots': False}
    _login(client)
    page = client.get('/').get_data(as_text=True)
    assert 'id="tracking-onboarding"' in page and 'What would you like to track?' in page
    assert 'data-bs-target="#loadCheckModal"' in page
    assert 'data-bs-target="#projectsCheckModal"' not in page and 'id="projectsCheckModal"' not in page
    assert 'data-bs-target="#botsCheckModal"' not in page and 'id="botsCheckModal"' not in page
    assert load_projects(app) == [] and load_bots(app) == []
    assert not ui_features_configured(app)


def test_onboarding_saves_only_the_selected_tools(app, client):
    _login(client)
    page = client.get('/').get_data(as_text=True)
    assert 'name="features" value="projects"' in page and 'name="features" value="bots"' in page
    response = client.post('/settings/features', data={
        'csrf_token': 'test-csrf', 'features': ['dns', 'load', 'projects']})
    assert response.status_code == 302
    assert load_ui_features(app) == {'dns': True, 'load': True, 'projects': True, 'bots': False}
    assert ui_features_configured(app)
    page = client.get('/').get_data(as_text=True)
    assert 'id="tracking-onboarding"' not in page
    assert 'data-bs-target="#projectsCheckModal"' in page
    assert 'id="botsCheckModal"' not in page


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


def test_unwritable_config_reports_error_instead_of_saved(app, client, monkeypatch):
    _login(client)
    monkeypatch.setattr('app.services.ui_preferences._write_config', lambda path, data: False)
    response = client.post('/settings/features', data={'csrf_token': 'test-csrf', 'features': ['bots']})
    assert response.status_code == 302
    with client.session_transaction() as state:
        flashed = state['_flashes']
    assert flashed[0][0] == 'danger' and 'config.json' in flashed[0][1]
    assert load_ui_features(app)['bots'] is False


def test_settings_page_lists_switches(app, client):
    _login(client)
    page = client.get('/settings').get_data(as_text=True)
    for name in ('dns', 'load', 'projects', 'bots'):
        assert f'id="feature-{name}"' in page
    save_ui_features(app, ['projects'])
    assert 'id="feature-projects" checked' in client.get('/settings').get_data(as_text=True)


def test_settings_page_has_working_actions_only(app, client):
    app.config['active_data_file'] = '/tmp/test_servers.enc'
    _login(client)
    page = client.get('/settings').get_data(as_text=True)
    # Ключ создаётся в браузере, PIN меняется через /pin/change_ajax; несуществующих адресов нет
    assert '/settings/generate-key' not in page and '/pin/reset_block' not in page
    assert 'crypto.getRandomValues' in page and '/pin/change_ajax' in page
    # Одна проверка совпадения ключей и настоящее окно Bootstrap для экспорта
    assert page.count('function confirmKeyChange') == 0 and "getElementById('changeKeyForm')" in page
    assert 'class="modal fade" id="exportInfoModal"' in page
    for anchor in ('id="ui-features"', 'id="settings-data"', 'id="settings-security"'):
        assert anchor in page


def test_inner_pages_lead_back_to_their_parent(app, client):
    _login(client)
    for path, parent in (('/settings/bots', '/settings'), ('/settings/projects', '/settings'),
                         ('/manage_hints', '/settings'), ('/settings', '/'), ('/net-tools/', '/')):
        page = client.get(path).get_data(as_text=True)
        assert 'class="page-crumbs"' in page, path
        assert f'class="btn btn-sm btn-outline-secondary page-back" href="{parent}"' in page, path
