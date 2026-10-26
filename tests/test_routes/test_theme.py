import re


def _login(client):
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, csrf_token='test-csrf')


def _html_tag(client, theme=None):
    if theme is not None:
        client.set_cookie('theme', theme)
    _login(client)
    page = client.get('/settings').get_data(as_text=True)
    return re.search(r'<html[^>]*>', page).group(0), page


def test_minecraft_skin_sits_on_top_of_the_dark_theme(client):
    tag, page = _html_tag(client, 'minecraft')
    assert 'data-bs-theme="dark"' in tag and 'data-skin="minecraft"' in tag
    assert "setTheme('minecraft', event)" in page and 'css/theme_minecraft.css' in page


def test_light_and_dark_themes_are_unchanged(client):
    for theme in ('light', 'dark'):
        tag, _ = _html_tag(client, theme)
        assert f'data-bs-theme="{theme}"' in tag and 'data-skin' not in tag


def test_default_theme_is_dark_without_skin(client):
    tag, _ = _html_tag(client)
    assert 'data-bs-theme="dark"' in tag and 'data-skin' not in tag


def test_minecraft_styles_apply_only_with_the_skin_attribute():
    from pathlib import Path
    css = Path('static/css/theme_minecraft.css').read_text(encoding='utf-8')
    rules = re.findall(r'^([^{}/\n][^{}]*)\{', css, re.M)
    assert rules and all('[data-skin="minecraft"]' in rule for rule in rules)
