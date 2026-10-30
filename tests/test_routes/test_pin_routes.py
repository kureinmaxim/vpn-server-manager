import json
import os


def write_runtime_config(app, current_pin='1234', setup_completed=False):
    config_path = os.path.join(app.config['APP_DATA_DIR'], 'config.json')
    payload = {
        'secret_pin': {
            'default_pin': '1234',
            'current_pin': current_pin,
            'last_changed': '',
            'setup_completed': setup_completed,
        }
    }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return config_path


class TestPinRoutes:
    def test_check_first_setup_allowed_for_clean_install(self, client, app):
        write_runtime_config(app, setup_completed=False)

        response = client.get('/pin/check_first_setup_allowed')

        assert response.status_code == 200
        data = response.get_json()
        assert data['allowed'] is True
        assert data['default_pin'] == '1234'

    def test_check_first_setup_disallowed_when_data_exists(self, client, app):
        write_runtime_config(app, setup_completed=False)
        servers_path = os.path.join(app.config['DATA_DIR'], app.config['SERVERS_FILE'])
        with open(servers_path, 'wb') as f:
            f.write(b'test-data')

        response = client.get('/pin/check_first_setup_allowed')

        assert response.status_code == 200
        data = response.get_json()
        assert data['allowed'] is False
        assert data['reason'] == 'Data already exists'

    def test_first_time_setup_uses_default_pin_when_empty(self, client, app):
        write_runtime_config(app, setup_completed=False)

        response = client.post('/pin/first_time_setup', data={})

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['used_default_pin'] is True

        config_path = os.path.join(app.config['APP_DATA_DIR'], 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        assert config['secret_pin']['current_pin'] == '1234'
        assert config['secret_pin']['setup_completed'] is True

        with client.session_transaction() as sess:
            assert sess['pin_authenticated'] is True
            assert sess['authenticated'] is True
            assert sess['pin_verified'] is True

    def test_first_time_setup_saves_custom_pin(self, client, app):
        write_runtime_config(app, setup_completed=False)

        response = client.post('/pin/first_time_setup', data={'new_pin': '5678'})

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['used_default_pin'] is False

        config_path = os.path.join(app.config['APP_DATA_DIR'], 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        assert config['secret_pin']['current_pin'] == '5678'

    def test_login_ajax_uses_saved_runtime_pin(self, client, app):
        write_runtime_config(app, current_pin='5678', setup_completed=True)

        response = client.post('/pin/login_ajax', json={'pin': '5678'})

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        with client.session_transaction() as sess:
            assert sess['pin_authenticated'] is True


def test_long_pin_can_be_set_changed_and_used_in_login(client, app):
    from html.parser import HTMLParser
    write_runtime_config(app)
    assert client.post('/pin/first_time_setup', data={'new_pin': 'test-pin-123'}).status_code == 200
    assert client.post('/pin/change_ajax', json={
        'old_pin': 'test-pin-123', 'new_pin': 'test-pin-456'}).status_code == 200
    client.post('/pin/logout')
    assert client.post('/pin/login_ajax', json={'pin': 'test-pin-456'}).status_code == 200

    class Inputs(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'input' and attrs.get('type') == 'password':
                assert 'maxlength' not in attrs or int(attrs['maxlength']) >= len('test-pin-456')
    Inputs().feed(client.get('/locked').text)


def test_setup_refuses_existing_vault_without_removing_it(client, app):
    from pathlib import Path
    write_runtime_config(app)
    vault = Path(app.config['DATA_DIR']) / app.config['SERVERS_FILE']
    vault.write_bytes(b'preserve-original-fixture')
    assert client.post('/pin/first_time_setup', data={'new_pin': 'new-pin'}).status_code == 403
    assert vault.read_bytes() == b'preserve-original-fixture'


def test_help_pin_claims_and_headings_match_current_behavior(client):
    from flask_babel import force_locale
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True)
    with force_locale('ru'):
        help_text = client.get('/help').text
        assert 'PIN хранится открытым текстом' in help_text
        assert 'После 3 неверных попыток' in help_text
        assert '10 запросов' in help_text
        assert 'PIN хранится в зашифрованном виде' not in help_text
        assert 'все существующие данные будут удалены' not in help_text
        for url in ('/help', '/add_server', '/manage_hints'):
            response = client.get(url)
            assert response.status_code == 200
            assert "{ _('" not in response.text
