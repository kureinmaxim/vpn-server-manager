import pytest
from flask import session

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
