import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.ssh_service import SSHService
from app.exceptions import SSHConnectionError, AuthenticationError

class TestSSHService:
    """Тесты для SSHService"""
    
    def test_init(self):
        """Тест инициализации сервиса"""
        service = SSHService()
        assert service.client is None
        assert service.sftp_client is None
        assert service.is_connected is False
    
    @patch('app.services.ssh_service.paramiko.SSHClient')
    def test_connect_success(self, mock_ssh_client):
        """Тест успешного подключения"""
        # Настройка мока
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client
        
        service = SSHService()
        service.connect('localhost', 'testuser', password='testpass')
        
        # Проверки
        assert service.client == mock_client
        mock_client.set_missing_host_key_policy.assert_called_once()
        mock_client.connect.assert_called_once_with(
            hostname='localhost',
            username='testuser',
            password='testpass',
            key_filename=None,
            port=22,
            timeout=10
        )
    
    @patch('app.services.ssh_service.paramiko.SSHClient')
    def test_connect_with_key_file(self, mock_ssh_client):
        """Тест подключения с ключом"""
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client
        
        service = SSHService()
        service.connect('localhost', 'testuser', key_filename='/path/to/key')
        
        mock_client.connect.assert_called_once_with(
            hostname='localhost',
            username='testuser',
            password=None,
            key_filename='/path/to/key',
            port=22,
            timeout=10
        )
    
    @patch('app.services.ssh_service.paramiko.SSHClient')
    def test_connect_authentication_error(self, mock_ssh_client):
        """Тест ошибки аутентификации"""
        from paramiko.ssh_exception import AuthenticationException
        
        mock_client = Mock()
        mock_client.connect.side_effect = AuthenticationException("Auth failed")
        mock_ssh_client.return_value = mock_client
        
        service = SSHService()
        
        with pytest.raises(AuthenticationError):
            service.connect('localhost', 'testuser', password='wrongpass')
    
    @patch('app.services.ssh_service.paramiko.SSHClient')
    def test_connect_ssh_error(self, mock_ssh_client):
        """Тест SSH ошибки"""
        from paramiko.ssh_exception import SSHException
        
        mock_client = Mock()
        mock_client.connect.side_effect = SSHException("SSH error")
        mock_ssh_client.return_value = mock_client
        
        service = SSHService()
        
        with pytest.raises(SSHConnectionError):
            service.connect('localhost', 'testuser')
    
    def test_disconnect(self):
        """Тест отключения"""
        service = SSHService()
        
        # Мокаем клиентов
        service.sftp_client = Mock()
        service.client = Mock()
        
        service.disconnect()
        
        # Проверяем, что клиенты закрыты
        service.sftp_client.close.assert_called_once()
        service.client.close.assert_called_once()
        assert service.sftp_client is None
        assert service.client is None
    
    def test_disconnect_with_none_clients(self):
        """Тест отключения когда клиенты None"""
        service = SSHService()
        # Не должно вызывать исключений
        service.disconnect()
    
    def test_execute_command_success(self):
        """Тест успешного выполнения команды"""
        service = SSHService()
        
        # Мокаем клиента и результат выполнения команды
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b'output data'
        mock_stderr.read.return_value = b''
        
        service.client = Mock()
        service.client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        result = service.execute_command('ls -la')
        
        assert result['exit_status'] == 0
        assert result['stdout'] == 'output data'
        assert result['stderr'] == ''
        service.client.exec_command.assert_called_once_with('ls -la')
    
    def test_execute_command_not_connected(self):
        """Тест выполнения команды без подключения"""
        service = SSHService()
        
        with pytest.raises(SSHConnectionError):
            service.execute_command('ls -la')
    
    def test_get_sftp_client(self):
        """Тест получения SFTP клиента"""
        service = SSHService()
        
        # Мокаем SSH клиента и SFTP клиента
        mock_sftp = Mock()
        service.client = Mock()
        service.client.open_sftp.return_value = mock_sftp
        
        result = service.get_sftp_client()
        
        assert result == mock_sftp
        assert service.sftp_client == mock_sftp
        service.client.open_sftp.assert_called_once()
    
    def test_get_sftp_client_not_connected(self):
        """Тест получения SFTP клиента без подключения"""
        service = SSHService()
        
        with pytest.raises(SSHConnectionError):
            service.get_sftp_client()
    
    def test_upload_file(self):
        """Тест загрузки файла"""
        service = SSHService()
        
        # Мокаем SFTP клиента
        mock_sftp = Mock()
        service.sftp_client = mock_sftp
        
        service.upload_file('/local/path', '/remote/path')
        
        mock_sftp.put.assert_called_once_with('/local/path', '/remote/path')
    
    def test_download_file(self):
        """Тест скачивания файла"""
        service = SSHService()
        
        # Мокаем SFTP клиента
        mock_sftp = Mock()
        service.sftp_client = mock_sftp
        
        service.download_file('/remote/path', '/local/path')
        
        mock_sftp.get.assert_called_once_with('/remote/path', '/local/path')
    
    def test_list_directory(self):
        """Тест получения списка файлов"""
        service = SSHService()
        
        # Мокаем SFTP клиента и результат
        mock_sftp = Mock()
        mock_file_attr = Mock()
        mock_file_attr.filename = 'test.txt'
        mock_file_attr.st_size = 1024
        mock_file_attr.st_mode = 0o644
        mock_file_attr.st_mtime = 1234567890
        
        mock_sftp.listdir_attr.return_value = [mock_file_attr]
        service.sftp_client = mock_sftp
        
        result = service.list_directory('/remote/path')
        
        assert len(result) == 1
        assert result[0]['filename'] == 'test.txt'
        assert result[0]['size'] == 1024
        assert result[0]['permissions'] == '644'
        assert result[0]['modified'] == 1234567890
        
        mock_sftp.listdir_attr.assert_called_once_with('/remote/path')
    
    def test_context_manager(self):
        """Тест использования как контекстного менеджера"""
        with patch('app.services.ssh_service.paramiko.SSHClient'):
            with SSHService() as service:
                assert isinstance(service, SSHService)
            # После выхода из контекста должен быть вызван disconnect
            # (в реальном коде это проверить сложнее из-за моков)
    
    def test_is_connected_property(self):
        """Тест свойства is_connected"""
        service = SSHService()
        assert service.is_connected is False
        
        # Мокаем подключенного клиента
        service.client = Mock()
        service.client.get_transport.return_value = Mock()
        assert service.is_connected is True
        
        # Мокаем отключенного клиента
        service.client.get_transport.return_value = None
        assert service.is_connected is False
