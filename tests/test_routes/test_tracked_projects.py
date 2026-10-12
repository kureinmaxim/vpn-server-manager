from app.services.project_stats import load_projects


def login(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_authenticated=True, pin_verified=True, csrf_token='token')


def test_page_lists_defaults_and_requires_login(app, client):
    assert client.get('/settings/projects').status_code in (302, 401)
    login(client)
    html = client.get('/settings/projects').get_data(as_text=True)
    assert 'value="BotCriptoM"' in html and 'value="Dockhand"' in html
    assert 'value="botcriptom, botcriptom-dash' in html


def test_save_add_remove_and_reset(app, client):
    login(client)
    form = {'csrf_token': 'token', 'name': ['BotCriptoM', 'Blog'],
            'units': ['botcriptom', 'ghost.service'], 'containers': ['', 'ghost-db']}
    assert client.post('/settings/projects', data=form).status_code == 302
    assert [(p['name'], p['units'], p['containers']) for p in load_projects(app)] == [
        ('BotCriptoM', ['botcriptom'], []), ('Blog', ['ghost'], ['ghost-db'])]
    assert 'Blog' in client.get('/').get_data(as_text=True)
    client.post('/settings/projects', data={'csrf_token': 'token', 'action': 'reset'})
    assert 'Dockhand' in [p['name'] for p in load_projects(app)]


def test_invalid_input_is_rejected_and_kept_in_the_form(app, client):
    login(client)
    response = client.post('/settings/projects', data={'csrf_token': 'token', 'name': ['Evil'],
                                                       'units': ['x; reboot'], 'containers': ['']})
    assert response.status_code == 400
    assert 'value="x; reboot"' in response.get_data(as_text=True)
    assert 'Dockhand' in [p['name'] for p in load_projects(app)]


def test_csrf_is_required(app, client):
    login(client)
    client.post('/settings/projects', data={'name': ['Blog'], 'units': ['ghost'], 'containers': ['']})
    assert 'Blog' not in [p['name'] for p in load_projects(app)]
