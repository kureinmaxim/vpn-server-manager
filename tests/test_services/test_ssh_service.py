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

    def test_parse_listener_ports(self):
        """Парсинг портов из ss/netstat вывода"""
        service = SSHService()

        output = "\n".join([
            "tcp|0.0.0.0:22",
            "tcp|127.0.0.1:5432",
            "udp|*:1194",
            "tcp|[::]:443",
            "tcp|0.0.0.0:22",
        ])

        assert service._parse_listener_ports(output) == ['22', '443', '1194', '5432']

    def test_get_listening_ports_falls_back_to_netstat(self):
        """Если ss пустой, используется netstat fallback"""
        service = SSHService()
        client = Mock()

        with patch.object(service, '_read_command_output', side_effect=['', 'tcp|0.0.0.0:80\nudp|0.0.0.0:53']):
            assert service._get_listening_ports(client) == ['53', '80']

    def test_parse_top_processes_skips_monitoring_helper_commands(self):
        """Служебные процессы самой команды мониторинга не должны попадать в топ."""
        service = SSHService()

        output = "\n".join([
            "PID COMMAND %CPU %MEM",
            "18647 ps 133 0.4",
            "18646 bash 50.0 0.3",
            "18239 sshd 0.6 1.1",
            "17103 python 0.3 9.3",
            "15727 xray 0.1 3.9",
            "99999 head 0.1 0.1",
        ])

        assert service._parse_top_processes(output) == [
            {'pid': '18239', 'cmd': 'sshd', 'cpu': '0.6', 'mem': '1.1'},
            {'pid': '17103', 'cmd': 'python', 'cpu': '0.3', 'mem': '9.3'},
            {'pid': '15727', 'cmd': 'xray', 'cpu': '0.1', 'mem': '3.9'},
        ]

    def test_check_required_tools_uses_server_ssh_port_in_ufw_warning(self):
        """UFW warning must reference actual server SSH port."""
        service = SSHService()
        client = Mock()

        def make_result(output: str):
            stdin = Mock()
            stdout = Mock()
            stderr = Mock()
            stdout.read.return_value = output.encode('utf-8')
            return stdin, stdout, stderr

        def exec_side_effect(command):
            mapping = {
                'which vnstat': '/usr/bin/vnstat\n',
                'which jq': '/usr/bin/jq\n',
                'which ufw': '/usr/sbin/ufw\n',
                'which netstat': '/usr/bin/netstat\n',
                'systemctl is-active vnstat 2>/dev/null': 'active\n',
                'sudo ufw status 2>/dev/null | grep "Status:" | awk \'{print $2}\'': 'active\n',
            }
            return make_result(mapping.get(command, ''))

        client.exec_command.side_effect = exec_side_effect

        with patch.object(service, 'get_connection_pooled', return_value=client):
            result = service.check_required_tools(
                ip='127.0.0.1',
                user='root',
                password='secret',
                port=22542,
            )

        ufw_tool = result['tools']['ufw']
        assert ufw_tool['warning'] == '⚠️ UFW включен! Убедитесь что SSH-порт 22542 разрешен!'
        assert ufw_tool['fix_cmd'] == 'sudo ufw allow 22542/tcp && sudo ufw status numbered'

    def test_parse_cpu_used_pct_handles_decimal_comma(self):
        """Парсер CPU должен корректно работать с локалями, где дроби идут через запятую."""
        service = SSHService()

        assert service._parse_cpu_used_pct('%Cpu(s):  1,8 us,  0,8 sy,  0,0 ni, 97,4 id,  0,0 wa,  0,0 hi,  0,0 si,  0,0 st') == 2.6
        assert service._parse_cpu_used_pct('%Cpu(s):  1.8 us,  0.8 sy,  0.0 ni, 97.4 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st') == 2.6
        assert service._parse_cpu_used_pct('%Cpu(s):  1.8%us,  0.8%sy,  0.0%ni, 97.4%id,  0.0%wa,  0.0%hi,  0.0%si,  0.0%st') == 2.6

    def test_get_cpu_used_pct_prefers_proc_stat_delta(self):
        """При наличии /proc/stat используем его как основной источник CPU."""
        service = SSHService()
        client = Mock()

        with patch.object(service, '_read_command_output', side_effect=['2.7']):
            assert service._get_cpu_used_pct(client) == 2.7

    def test_get_cpu_used_pct_falls_back_to_vmstat(self):
        """Если top не дал распарсить CPU, используется vmstat fallback."""
        service = SSHService()
        client = Mock()

        with patch.object(service, '_read_command_output', side_effect=['oops', '', '', '97.0']):
            assert service._get_cpu_used_pct(client) == 3.0
