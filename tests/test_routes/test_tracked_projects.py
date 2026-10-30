from app.services.project_stats import load_projects


def login(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_authenticated=True, pin_verified=True, csrf_token='token')


def test_page_starts_empty_and_offers_generic_examples(app, client):
    assert client.get('/settings/projects').status_code in (302, 401)
    login(client)
    html = client.get('/settings/projects').get_data(as_text=True)
    assert load_projects(app) == []
    assert 'value="Web application example"' in html and 'value="Background worker example"' in html
    assert 'id="import-project-examples"' in html and 'data-project-example=' in html
    assert '/Users/' not in html and 'BotCriptoM' not in html


def test_save_add_remove_and_reset(app, client, all_features):
    login(client)
    form = {'csrf_token': 'token', 'name': ['Example project', 'Blog', 'Manual process'],
            'units': ['example-app', 'ghost.service', ''], 'containers': ['', 'ghost-db', ''],
            'processes': ['', '', 'worker']}
    assert client.post('/settings/projects', data=form).status_code == 302
    assert [(p['name'], p['units'], p['containers'], p['processes']) for p in load_projects(app)] == [
        ('Example project', ['example-app'], [], []), ('Blog', ['ghost'], ['ghost-db'], []),
        ('Manual process', [], [], ['worker'])]
    assert '>worker</textarea>' in client.get('/settings/projects').get_data(as_text=True)
    assert 'Blog' in client.get('/').get_data(as_text=True)
    client.post('/settings/projects', data={'csrf_token': 'token', 'action': 'reset'})
    assert load_projects(app) == []


def test_invalid_input_is_rejected_and_kept_in_the_form(app, client):
    login(client)
    response = client.post('/settings/projects', data={'csrf_token': 'token', 'name': ['Evil'],
                                                       'units': ['x; reboot'], 'containers': [''], 'processes': ['']})
    assert response.status_code == 400
    assert '>x; reboot</textarea>' in response.get_data(as_text=True)
    assert load_projects(app) == []


def test_csrf_is_required(app, client):
    login(client)
    client.post('/settings/projects', data={'name': ['Blog'], 'units': ['ghost'], 'containers': [''], 'processes': ['']}, csrf=False)
    assert 'Blog' not in [p['name'] for p in load_projects(app)]
