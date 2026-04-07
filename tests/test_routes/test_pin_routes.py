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
