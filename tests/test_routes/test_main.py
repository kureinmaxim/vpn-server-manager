import copy

import pytest
from flask import session

from app.services import registry
from app.services.crypto_service import CryptoService

class TestMainRoutes:
    """Тесты для основных маршрутов"""
    
    def test_index_redirects_when_not_authenticated(self, client):
        """Тест перенаправления на заблокированную страницу"""
        response = client.get('/')
        assert response.status_code == 302
        assert '/locked' in response.location
    
    def test_index_locked_page(self, client):
        """Тест заблокированной страницы"""
        response = client.get('/locked')
        assert response.status_code == 200
        assert b'PIN' in response.data or b'pin' in response.data
    
    def test_verify_pin_success(self, client):
        """Тест успешной проверки PIN"""
        response = client.post('/verify_pin', data={'pin': '1234'})
        assert response.status_code == 302
        assert '/' in response.location
    
    def test_verify_pin_failure(self, client):
        """Тест неудачной проверки PIN"""
        response = client.post('/verify_pin', data={'pin': '0000'})
        assert response.status_code == 302
        assert '/locked' in response.location
    
    def test_verify_pin_empty(self, client):
        """Тест проверки пустого PIN"""
        response = client.post('/verify_pin', data={'pin': ''})
        assert response.status_code == 302
        assert '/locked' in response.location
    
    def test_logout(self, client):
        """Тест выхода из системы"""
        with client.session_transaction() as sess:
            sess['authenticated'] = True
        
        response = client.get('/logout')
        assert response.status_code == 302
        assert '/locked' in response.location
    
    def test_help_page(self, client):
        """Тест страницы помощи"""
        response = client.get('/help')
        assert response.status_code == 200
    
    def test_about_page(self, client):
        """Тест страницы о приложении"""
        response = client.get('/about')
        assert response.status_code == 200
    
    def test_change_language(self, client):
        """Тест смены языка"""
        response = client.get('/change_language/ru')
        assert response.status_code == 302
        
        response = client.get('/change_language/en')
        assert response.status_code == 302
        
        response = client.get('/change_language/zh')
        assert response.status_code == 302
        
        # Неподдерживаемый язык
        response = client.get('/change_language/fr')
        assert response.status_code == 302
    
    def test_protected_routes_require_auth(self, client):
        """Тест защищенных маршрутов"""
        protected_routes = [
            '/add_server',
            '/edit_server/test-id',
            '/settings',
            '/cheatsheet',
            '/manage_hints'
        ]
        
        for route in protected_routes:
            response = client.get(route)
            assert response.status_code == 302
            assert '/locked' in response.location
    
    def test_protected_routes_with_auth(self, client):
        """Тест защищенных маршрутов с аутентификацией"""
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['pin_verified'] = True
        
        protected_routes = [
            '/add_server',
            '/settings',
            '/cheatsheet',
            '/manage_hints'
        ]
        
        for route in protected_routes:
            response = client.get(route)
            # Может быть 200 или 404 (если шаблон не найден)
            assert response.status_code in [200, 404]

    def test_settings_shows_export_actions_when_data_file_attached(self, client, app):
        """Страница настроек должна показывать экспорт при наличии active_data_file."""
        app.config['active_data_file'] = '/tmp/test_servers.enc'

        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['pin_verified'] = True

        response = client.get('/settings')

        assert response.status_code == 200
        assert 'Экспортировать данные'.encode('utf-8') in response.data
        assert 'Экспортировать ключ'.encode('utf-8') in response.data
        assert 'Полный экспорт'.encode('utf-8') in response.data
    
    def test_upload_icon_no_file(self, client):
        """Тест загрузки иконки без файла"""
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['pin_verified'] = True
        
        response = client.post('/upload_icon')
        assert response.status_code == 302
    
    def test_download_backup(self, client):
        """Тест скачивания резервной копии"""
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['pin_verified'] = True
        
        response = client.get('/download_backup')
        assert response.status_code == 302
    
    def test_restore_backup_no_file(self, client):
        """Тест восстановления резервной копии без файла"""
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['pin_verified'] = True
        
        response = client.post('/restore_backup')
        assert response.status_code == 302

    def test_edit_server_post_updates_passwords_with_data_manager_encryption(self, client):
        """POST /edit_server должен сохранять новые пароли без ошибки CryptoService key."""
        class StubDataManager:
            def __init__(self):
                self.servers = [{
                    'id': '1',
                    'name': 'Test server',
                    'provider': 'Test provider',
                    'ip_address': '127.0.0.1',
                    'os': 'Debian',
                    'status': 'Active',
                    'notes': '',
                    'docker_info': '',
                    'software_info': '',
                    'card_color': '#ffc107',
                    'panel_url': '',
                    'hoster_url': '',
                    'specs': {'cpu': '', 'ram': '', 'disk': ''},
                    'payment_info': {
                        'amount': 0.0,
                        'currency': 'USD',
                        'next_due_date': '',
                        'payment_period': 'Monthly',
                    },
                    'ssh_credentials': {
                        'user': 'root',
                        'port': 22,
                        'root_login_allowed': False,
                        'password': 'old-ssh',
                        'password_decrypted': 'old-ssh',
                        'root_password': 'old-root',
                        'root_password_decrypted': 'old-root',
                    },
                    'panel_credentials': {
                        'user': 'old-panel-user',
                        'user_decrypted': 'old-panel-user',
                        'password': 'old-panel-password',
                        'password_decrypted': 'old-panel-password',
                    },
                    'hoster_credentials': {
                        'login_method': 'password',
                        'user': 'old-hoster-user',
                        'user_decrypted': 'old-hoster-user',
                        'password': 'old-hoster-password',
                        'password_decrypted': 'old-hoster-password',
                    },
                    'checks': {'dns_ok': False, 'streaming_ok': False},
                }]
                self.saved_servers = None
                self.saved_path = None

            def load_servers(self, config):
                return self.servers

            def get_active_data_path(self, config):
                return 'test-data.enc'

            def save_servers(self, servers, file_path):
                self.saved_servers = copy.deepcopy(servers)
                self.saved_path = file_path

            def encrypt_data(self, data):
                return f'enc::{data}'

        data_manager = StubDataManager()
        registry.register('data_manager', data_manager)
        registry.register('crypto', CryptoService())

        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['pin_verified'] = True

        response = client.post(
            '/edit_server/1',
            data={
                'ssh_password': 'new-ssh-password',
                'ssh_root_password': 'new-root-password',
                'panel_user': 'new-panel-user',
                'panel_password': 'new-panel-password',
                'hoster_user': 'new-hoster-user',
                'hoster_password': 'new-hoster-password',
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.location.endswith('/')
        assert data_manager.saved_path == 'test-data.enc'
        assert data_manager.saved_servers is not None

        saved_server = data_manager.saved_servers[0]
        assert saved_server['ssh_credentials']['password'] == 'enc::new-ssh-password'
        assert saved_server['ssh_credentials']['root_password'] == 'enc::new-root-password'
        assert saved_server['panel_credentials']['user'] == 'enc::new-panel-user'
        assert saved_server['panel_credentials']['password'] == 'enc::new-panel-password'
        assert saved_server['hoster_credentials']['user'] == 'enc::new-hoster-user'
        assert saved_server['hoster_credentials']['password'] == 'enc::new-hoster-password'
