"""Экспорт/импорт .enc не должен глотать `%` в паролях."""

from cryptography.fernet import Fernet

from app.services.data_manager_service import DataManagerService

PERCENT_SECRET = "aguJ#%z&g}&%:"


def test_save_load_roundtrip_keeps_percent_in_ssh_password(tmp_path):
    key = Fernet.generate_key().decode()
    manager = DataManagerService(key, str(tmp_path))
    servers = [
        {
            "id": 1,
            "name": "vps45379",
            "ssh_credentials": {
                "user": "root",
                "password": manager.encrypt_data(PERCENT_SECRET),
                "port": 22,
                "root_password": manager.encrypt_data(PERCENT_SECRET),
                "root_login_allowed": True,
            },
        }
    ]
    path = tmp_path / "servers.enc"
    manager.save_servers(servers, str(path))

    loaded = manager.load_servers({"active_data_file": str(path)})
    ssh = loaded[0]["ssh_credentials"]
    assert ssh["password_decrypted"] == PERCENT_SECRET
    assert ssh["root_password_decrypted"] == PERCENT_SECRET
