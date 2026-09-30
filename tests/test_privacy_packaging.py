from pathlib import Path
from tools.check_public_files import is_private


def test_sensitive_names_blocked():
    for name in ('data/servers.json.enc', 'data/hints.json', '.env', '.env.production', 'docs/private.key', 'client_secret_example.json'):
        assert is_private(name)
    for name in ('env.example', 'config/config.json.template', 'config/hints.json.template', 'docs/README.md'):
        assert not is_private(name)


def test_windows_uses_empty_template_not_local_notes():
    source = Path('vpn-manager-installer.iss').read_text(encoding='utf-8')
    assert 'Source: "data\\hints.json"' not in source
    assert 'Source: "config\\hints.json.template"' in source
    assert 'Flags: onlyifdoesntexist' in source
    assert Path('config/hints.json.template').read_text().strip() == '[]'


def test_macos_does_not_bundle_user_data():
    assert '"data:data"' not in Path('build_macos.py').read_text(encoding='utf-8')
