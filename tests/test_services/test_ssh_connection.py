"""Shared endpoint, credential and trusted-client setup for SSH operations."""
from unittest.mock import Mock

import paramiko
import pytest

from app.services import ssh_connection
from app.services.ssh_service import SSHService


class DataManager:
    def __init__(self, servers):
        self.servers = servers

    def load_servers(self, config):
        assert config == {"active_data_file": "/tmp/servers.enc"}
        return self.servers

    @staticmethod
    def decrypt_data(value):
        return value.removeprefix("enc::")


def test_resolve_server_credentials_uses_card_endpoint_and_decrypted_auth(monkeypatch):
    monkeypatch.setattr(ssh_connection, "ssh_address", lambda server, port: "192.0.2.11")
    server = {
        "id": 7,
        "ip_address": "192.0.2.10",
        "ssh_credentials": {
            "user": "operator", "port": "2222", "password": "enc::pw",
            "private_key": "enc::key-text", "key_passphrase": "enc::phrase",
        },
    }

    actual_server, creds = ssh_connection.resolve_server_ssh_credentials(
        "7", DataManager([server]), {"active_data_file": "/tmp/servers.enc"}
    )

    assert actual_server is server
    assert creds == {
        "ip": "192.0.2.11", "user": "operator", "port": "2222", "password": "pw",
        "key": "key-text", "key_passphrase": "phrase",
    }


def test_resolve_server_credentials_returns_none_for_missing_or_undecryptable(monkeypatch):
    manager = DataManager([{"id": "present", "ip_address": "192.0.2.12"}])
    config = {"active_data_file": "/tmp/servers.enc"}
    assert ssh_connection.resolve_server_ssh_credentials("missing", manager, config) == (None, None)

    manager.decrypt_data = Mock(side_effect=ValueError("secret detail"))
    server = {"id": "present", "ip_address": "192.0.2.12",
              "ssh_credentials": {"password": "enc::bad"}}
    manager.servers = [server]
    assert ssh_connection.resolve_server_ssh_credentials("present", manager, config) == (None, None)


def test_connect_card_client_sets_trust_before_connect_and_limits_local_auth(monkeypatch):
    events = []
    client = Mock()

    def load_trust(target):
        events.append(("load_trust", target))

    def connect_kwargs(password, key, passphrase, *, use_local_keys):
        events.append(("auth", password, key, passphrase, use_local_keys))
        return {"password": password, "look_for_keys": use_local_keys, "allow_agent": use_local_keys}

    def connect_managed(target, **kwargs):
        events.append(("connect", target, kwargs))

    monkeypatch.setattr(ssh_connection, "load_known_hosts", load_trust)
    monkeypatch.setattr(ssh_connection, "connect_kwargs", connect_kwargs)
    monkeypatch.setattr(SSHService, "connect_managed", connect_managed)

    ssh_connection.connect_card_client(client, {
        "ip": "192.0.2.20", "port": 2222, "user": "operator", "password": "card-password",
    })

    assert events[0] == ("load_trust", client)
    assert isinstance(client.set_missing_host_key_policy.call_args.args[0], paramiko.RejectPolicy)
    assert events[1] == ("auth", "card-password", None, None, False)
    assert events[2][0] == "connect"
    assert events[2][2]["hostname"] == "192.0.2.20"
    assert events[2][2]["port"] == 2222
    assert events[2][2]["username"] == "operator"


def test_connect_card_client_uses_card_auth_only_unless_fallback_is_explicit(monkeypatch):
    local_modes = []
    monkeypatch.setattr(ssh_connection, "load_known_hosts", lambda _client: None)
    monkeypatch.setattr(ssh_connection, "connect_kwargs", lambda *args, use_local_keys: (
        local_modes.append(use_local_keys) or {"look_for_keys": use_local_keys}
    ))
    monkeypatch.setattr(SSHService, "connect_managed", lambda *_args, **_kwargs: None)

    empty_card = {"ip": "192.0.2.20", "port": 22, "user": "root"}
    ssh_connection.connect_card_client(Mock(), empty_card)
    ssh_connection.connect_card_client(Mock(), empty_card, local_keys_when_card_empty=True)
    ssh_connection.connect_card_client(Mock(), {
        "ip": "192.0.2.20", "port": 22, "user": "root", "key": "card-key",
    }, local_keys_when_card_empty=True)

    assert local_modes == [False, True, False]


def test_connect_card_client_propagates_connection_failures(monkeypatch):
    client = Mock()
    monkeypatch.setattr(ssh_connection, "load_known_hosts", lambda _client: None)
    monkeypatch.setattr(ssh_connection, "connect_kwargs", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(SSHService, "connect_managed",
                        Mock(side_effect=paramiko.SSHException("private connection detail")))

    with pytest.raises(paramiko.SSHException):
        ssh_connection.connect_card_client(client, {
            "ip": "192.0.2.20", "port": 22, "user": "root", "password": "pw",
        })

    client.close.assert_not_called()
