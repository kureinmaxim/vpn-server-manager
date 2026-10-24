import pytest

from app.services import ssh_address as addresses
from app.services.ssh_address import AddressError, card_addresses, clean_addresses, forget

TNAS = {'id': 7, 'ip_address': '100.64.0.12',
        'extra_addresses': [{'address': '192.168.1.222', 'label': 'lan'}]}


@pytest.fixture(autouse=True)
def fresh():
    forget()
    yield
    forget()


def reachable(monkeypatch, answering):
    calls = []

    def probe(address, port, timeout):
        calls.append((address, port))
        return address in answering
    monkeypatch.setattr(addresses, '_reachable', probe)
    return calls


def test_clean_drops_empty_duplicates_and_unknown_labels():
    rows = [{'address': ' 192.168.1.222 ', 'label': 'lan'}, {'address': '', 'label': 'mesh'},
            {'address': '100.64.0.12', 'label': 'mesh'}, {'address': 'tnas.lan', 'label': 'weird'},
            {'address': '192.168.1.222', 'label': 'direct'}]
    assert clean_addresses(rows, main='100.64.0.12') == [
        {'address': '192.168.1.222', 'label': 'lan'}, {'address': 'tnas.lan', 'label': 'direct'}]


@pytest.mark.parametrize('address', ['1.2.3.4; reboot', '-oProxyCommand=x', 'host name', '$(id)'])
def test_clean_rejects_unsafe_addresses(address):
    with pytest.raises(AddressError):
        clean_addresses([{'address': address, 'label': 'lan'}])


def test_clean_limits_count():
    with pytest.raises(AddressError):
        clean_addresses([{'address': f'192.0.2.{i}'} for i in range(5)])


def test_card_addresses_main_first_and_corrupt_extras_ignored():
    assert card_addresses(TNAS) == ['100.64.0.12', '192.168.1.222']
    assert card_addresses({'ip_address': '192.0.2.1', 'extra_addresses': [{'address': 'a b'}]}) == ['192.0.2.1']


def test_single_address_is_not_probed(monkeypatch):
    calls = reachable(monkeypatch, set())
    assert addresses.ssh_address({'id': 1, 'ip_address': '192.0.2.1'}, 22) == '192.0.2.1'
    assert calls == []


def test_first_answering_address_wins_and_is_remembered(monkeypatch):
    calls = reachable(monkeypatch, {'192.168.1.222'})
    assert addresses.ssh_address(TNAS, 9222) == '192.168.1.222'
    assert calls == [('100.64.0.12', 9222), ('192.168.1.222', 9222)]
    calls.clear()
    assert addresses.ssh_address(TNAS, 9222) == '192.168.1.222'
    assert calls == [('192.168.1.222', 9222)]


def test_remembered_address_that_stops_answering_falls_back_in_order(monkeypatch):
    reachable(monkeypatch, {'192.168.1.222'})
    addresses.ssh_address(TNAS, 9222)
    calls = reachable(monkeypatch, {'100.64.0.12'})
    assert addresses.ssh_address(TNAS, 9222) == '100.64.0.12'
    assert calls == [('192.168.1.222', 9222), ('100.64.0.12', 9222)]


def test_nothing_answers_keeps_main_address(monkeypatch):
    reachable(monkeypatch, set())
    assert addresses.ssh_address(TNAS, 9222) == '100.64.0.12'
