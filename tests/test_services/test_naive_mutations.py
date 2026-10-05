import pytest

from app.services.naive_mutations import change_naive, parse_caddyfile, replace_port


RAW = b'''{
    email admin@example.com
    order forward_proxy before file_server
}

:443, example.com:443 {
    forward_proxy {
        basic_auth "naive-user" "fixture-password"
    }
}
'''


def test_parse_and_change_port_preserves_credentials():
    runtime = parse_caddyfile(RAW)
    manager = {'domain':'example.com','port':443,'username':'naive-user','password':'fixture-password'}
    updated, changed = change_naive(manager, runtime, {'kind':'port','port':8443})
    assert updated['port'] == 8443 and changed['port'] == 8443
    result = replace_port(RAW, 'example.com', 443, 8443)
    assert parse_caddyfile(result)['password'] == 'fixture-password'
    assert b':8443, example.com:8443 {' in result


def test_client_changes_are_blocked_for_shared_account():
    runtime = parse_caddyfile(RAW)
    manager = {'domain':'example.com','port':443,'username':'naive-user','password':'fixture-password'}
    with pytest.raises(ValueError, match='shared_password'):
        change_naive(manager, runtime, {'kind':'add_client','name':'alice'})


@pytest.mark.parametrize('raw', [b':443, other.example:443 {\n}', b':443, example.com:444 {\n}', b'basic_auth "u" "p"\n'])
def test_unexpected_caddyfile_is_rejected(raw):
    with pytest.raises(ValueError): parse_caddyfile(raw)


def test_manager_and_runtime_mismatch_is_rejected():
    runtime = parse_caddyfile(RAW)
    manager = {'domain':'example.com','port':443,'username':'other','password':'fixture-password'}
    with pytest.raises(ValueError, match='config_mismatch'):
        change_naive(manager, runtime, {'kind':'port','port':8443})
