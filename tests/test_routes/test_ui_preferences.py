"""Persistent UI language and zoom across app restarts."""

import json
import os


def _read_ui(app):
    path = os.path.join(app.config['APP_DATA_DIR'], 'config.json')
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle).get('ui', {})


def test_change_language_persists_to_profile_config(client, app):
    client.get('/change_language/zh')
    prefs = _read_ui(app)
    assert prefs.get('language') == 'zh'

    with client.session_transaction() as sess:
        sess.clear()

    response = client.get('/locked')
    assert response.status_code == 200
    assert b'lang="zh"' in response.data

    # A brand-new client still picks the saved profile language after restart.
    fresh = app.test_client()
    fresh_response = fresh.get('/locked')
    assert fresh_response.status_code == 200
    assert b'lang="zh"' in fresh_response.data


def test_zoom_preference_persists_to_profile_and_templates(client, app):
    response = client.post(
        '/ui_preferences',
        json={'zoom': '60'},
        headers={'Accept': 'application/json'},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['ui']['zoom'] == '60'
    assert _read_ui(app).get('zoom') == '60'

    page = client.get('/locked')
    assert page.status_code == 200
    assert b'const serverZoom = "60"' in page.data


def test_ui_preferences_reject_invalid_values(client):
    bad_zoom = client.post('/ui_preferences', json={'zoom': '33'})
    assert bad_zoom.status_code == 400
    bad_lang = client.post('/ui_preferences', json={'language': 'fr'})
    assert bad_lang.status_code == 400


def test_zoom_accepts_every_step(client, app):
    from app.services.ui_preferences import ZOOM_STEPS
    assert ZOOM_STEPS[0] == '50' and ZOOM_STEPS[-1] == '200' and '100' in ZOOM_STEPS
    response = client.post('/ui_preferences', json={'zoom': '125'}, headers={'Accept': 'application/json'})
    assert response.status_code == 200
    assert _read_ui(app).get('zoom') == '125'


def test_zoom_menu_has_steps_buttons_and_keys(client):
    html = client.get('/locked?lang=en').get_data(as_text=True)
    assert 'const allowedZooms = ["50", "60", "70", "80", "90", "100", "110", "125", "150", "175", "200"]' in html
    assert 'onclick="stepZoom(1, event)"' in html and 'onclick="stepZoom(-1, event)"' in html
    assert 'data-zoom-step="125"' in html and 'Actual size' in html
    assert 'window.vpnZoom' in html and "addEventListener('keydown'" in html
    assert 'Масштаб изменён' not in html


def test_new_profile_defaults_to_actual_size_without_replacing_saved_zoom(client, app):
    from app.services.ui_preferences import load_ui_preferences
    assert load_ui_preferences(app)['zoom'] == '100'
    assert 'const serverZoom = "100"' in client.get('/locked').text
    client.post('/ui_preferences', json={'zoom': '80'})
    fresh = app.test_client()
    assert 'const serverZoom = "80"' in fresh.get('/locked').text
    assert _read_ui(app)['zoom'] == '80'


def test_large_zoom_persists_across_sessions(client, app):
    for zoom in ('175', '200'):
        response = client.post('/ui_preferences', json={'zoom': zoom})
        assert response.status_code == 200
        fresh = app.test_client()
        assert f'const serverZoom = "{zoom}"' in fresh.get('/locked').text
        assert _read_ui(app)['zoom'] == zoom
