"""Вход по SSH-ключу из карточки сервера: чтение ключа, параметры paramiko, пул."""
import base64
import hashlib
from unittest.mock import Mock

import paramiko
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

from app.services import ssh_auth
from app.services.ssh_auth import SshKeyError, connect_kwargs, fingerprint, has_ssh_auth, load_private_key
from app.services.ssh_service import SSHService
from app.utils.credentials import sanitize_private_key


def ed25519_key():
    """Новый ключ Ed25519 в формате OpenSSH и строка его открытой части."""
    key = ed25519.Ed25519PrivateKey.generate()
    text = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH, serialization.NoEncryption()
    ).decode()
    public = key.public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    ).decode()
    return text, public


def rsa_pem_encrypted(passphrase):
    """RSA в старом PEM с шифрованием: внутри есть заголовки и пустая строка."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.BestAvailableEncryption(passphrase.encode()),
    ).decode()


def expected_fingerprint(public_line):
    kind, blob = public_line.split()[:2]
    digest = base64.b64encode(hashlib.sha256(base64.b64decode(blob)).digest()).decode().rstrip("=")
    return f"{kind} SHA256:{digest}"


class TestLoadPrivateKey:
    def test_pasted_ed25519_text(self):
        text, public = ed25519_key()
        key = load_private_key(text)
        assert isinstance(key, paramiko.Ed25519Key)
        assert fingerprint(key) == expected_fingerprint(public)

    def test_path_with_home_expansion(self, tmp_path, monkeypatch):
        text, public = ed25519_key()
        (tmp_path / ".ssh").mkdir()
        (tmp_path / ".ssh" / "id_ed25519").write_text(text)
        monkeypatch.setenv("HOME", str(tmp_path))
        key = load_private_key("~/.ssh/id_ed25519")
        assert fingerprint(key) == expected_fingerprint(public)

    def test_encrypted_key_needs_the_right_passphrase(self):
        text = rsa_pem_encrypted("correct horse")
        assert isinstance(load_private_key(text, "correct horse"), paramiko.RSAKey)
        with pytest.raises(SshKeyError):
            load_private_key(text)
        with pytest.raises(SshKeyError):
            load_private_key(text, "wrong")

    @pytest.mark.parametrize("value", ["/nonexistent/id_ed25519", "-----BEGIN OPENSSH PRIVATE KEY-----\ngarbage\n"])
    def test_unreadable_key_is_an_auth_error(self, value):
        with pytest.raises(SshKeyError) as caught:
            load_private_key(value)
        # Существующие обработчики ловят AuthenticationException и не показывают ключ.
        assert isinstance(caught.value, paramiko.AuthenticationException)
        assert "garbage" not in str(caught.value)


class TestConnectKwargs:
    def test_password_only_never_uses_local_keys(self):
        kwargs = connect_kwargs("secret")
        assert kwargs == {"password": "secret", "look_for_keys": False, "allow_agent": False}

    def test_key_from_card_becomes_pkey_and_keeps_password_as_fallback(self):
        text, _ = ed25519_key()
        kwargs = connect_kwargs("secret", text)
        assert isinstance(kwargs["pkey"], paramiko.Ed25519Key)
        assert kwargs["password"] == "secret"
        assert kwargs["look_for_keys"] is False and kwargs["allow_agent"] is False

    def test_local_keys_only_on_request(self):
        kwargs = connect_kwargs(None, use_local_keys=True)
        assert kwargs["password"] is None
        assert kwargs["look_for_keys"] is True and kwargs["allow_agent"] is True

    def test_has_ssh_auth(self):
        assert has_ssh_auth({"password": "x"})
        assert has_ssh_auth({"password": "", "key": "~/.ssh/id_ed25519"})
        assert not has_ssh_auth({"password": "", "key": ""})
        assert not has_ssh_auth(None)


class TestSanitizePrivateKey:
    def test_keeps_lines_and_inner_blank_line(self):
        text = rsa_pem_encrypted("pw")
        pasted = "​  " + text.replace("\n", "\r\n") + "\r\n\r\n"
        cleaned = sanitize_private_key(pasted)
        assert cleaned == text
        assert "\n\n" in cleaned  # пустая строка после DEK-Info осталась
        assert isinstance(load_private_key(cleaned, "pw"), paramiko.RSAKey)

    def test_path_is_trimmed(self):
        assert sanitize_private_key("  ~/.ssh/id_ed25519 \n") == "~/.ssh/id_ed25519"
        assert sanitize_private_key("") == ""
        assert sanitize_private_key(None) == ""


class TestSshServiceWithKey:
    def test_pool_logs_in_with_key_from_card(self, monkeypatch):
        monkeypatch.setattr(SSHService, "_connection_pool", {})
        monkeypatch.setattr(SSHService, "_connection_locks", {})
        client = Mock()
        monkeypatch.setattr("app.services.ssh_service.paramiko.SSHClient", Mock(return_value=client))
        text, _ = ed25519_key()
        SSHService.get_connection_pooled("key-host", 22, "root", None, key=text)
        kwargs = client.connect.call_args.kwargs
        assert isinstance(kwargs["pkey"], paramiko.Ed25519Key)
        assert kwargs["password"] is None
        assert kwargs["look_for_keys"] is False and kwargs["allow_agent"] is False

    def test_bad_key_closes_client_without_connecting(self, monkeypatch):
        monkeypatch.setattr(SSHService, "_connection_pool", {})
        monkeypatch.setattr(SSHService, "_connection_locks", {})
        client = Mock()
        monkeypatch.setattr("app.services.ssh_service.paramiko.SSHClient", Mock(return_value=client))
        with pytest.raises(paramiko.AuthenticationException):
            SSHService.get_connection_pooled("bad-key-host", 22, "root", None, key="/nonexistent/key")
        client.connect.assert_not_called()
        client.close.assert_called_once()
        assert not SSHService._connection_pool

    def test_monitoring_methods_pass_the_key_to_the_pool(self, monkeypatch):
        service = SSHService()
        pooled = Mock(side_effect=RuntimeError("stop after the call"))
        monkeypatch.setattr(service, "get_connection_pooled", pooled)
        with pytest.raises(Exception):
            service.get_load_snapshot("192.0.2.1", "root", None, key="KEY", key_passphrase="PP")
        assert pooled.call_args.kwargs["key"] == "KEY"
        assert pooled.call_args.kwargs["key_passphrase"] == "PP"

    def test_connect_accepts_key_text(self, monkeypatch):
        client = Mock()
        monkeypatch.setattr("app.services.ssh_service.paramiko.SSHClient", Mock(return_value=client))
        text, _ = ed25519_key()
        SSHService().connect("localhost", "root", key=text)
        kwargs = client.connect.call_args.kwargs
        assert isinstance(kwargs["pkey"], paramiko.Ed25519Key)
        assert kwargs["key_filename"] is None


class TestSecurityAdvice:
    FACTS = {
        "ssh_failures_24h": 0,
        "sshd": {"password_authentication": "yes", "permit_root_login": "yes", "port": "22"},
        "apt_update_known": True,
        "days_since_update": 1,
    }

    def test_password_app_is_warned_before_disabling_passwords(self):
        brief = SSHService.build_security_brief(self.FACTS, app_uses_key=False, app_user="root")
        assert "PasswordAuthentication" in brief["summary"]
        assert "потеряет доступ" in brief["summary"]
        assert "сначала задайте SSH-ключ в карточке" in brief["summary"]

    def test_key_app_may_disable_passwords(self):
        brief = SSHService.build_security_brief(self.FACTS, app_uses_key=True, app_user="root")
        assert "PasswordAuthentication можно выключить" in brief["summary"]
        assert "потеряет доступ" not in brief["summary"]
        assert "сначала задайте SSH-ключ" not in brief["summary"]


def test_supported_key_types_exclude_dsa():
    assert paramiko.Ed25519Key in ssh_auth.KEY_CLASSES
    assert all(cls.__name__ != "DSSKey" for cls in ssh_auth.KEY_CLASSES)
