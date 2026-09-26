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
