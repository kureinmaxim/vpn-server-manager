import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.ssh_service import SSHService
from app.exceptions import SSHConnectionError, AuthenticationError


def _stream_channel(stdout_data=b'', stderr_data=b'', status=0):
    channel = Mock()
    channel.recv_ready.side_effect = [bool(stdout_data), False]
    channel.recv.return_value = stdout_data
    channel.recv_stderr_ready.side_effect = [bool(stderr_data), False]
    channel.recv_stderr.return_value = stderr_data
    channel.exit_status_ready.return_value = True
    channel.recv_exit_status.return_value = status
    return channel


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
        mock_client.connect.assert_called_once()

        # Проверяем значимые параметры, а не полную сигнатуру вызова: точные
        # значения таймаутов — деталь реализации, их подкрутка не должна ронять тест.
        kwargs = mock_client.connect.call_args.kwargs
        assert kwargs['hostname'] == 'localhost'
        assert kwargs['username'] == 'testuser'
        assert kwargs['password'] == 'testpass'
        assert kwargs['key_filename'] is None
        assert kwargs['port'] == 22
        assert kwargs['timeout'] > 0
        # Подключение не должно втихую подхватывать ключи из ~/.ssh или ssh-agent
        assert kwargs['look_for_keys'] is False
        assert kwargs['allow_agent'] is False

    @patch('app.services.ssh_service.paramiko.SSHClient')
    def test_connect_with_key_file(self, mock_ssh_client):
        """Тест подключения с ключом"""
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client

        service = SSHService()
        service.connect('localhost', 'testuser', key_filename='/path/to/key')

        mock_client.connect.assert_called_once()

        kwargs = mock_client.connect.call_args.kwargs
        assert kwargs['hostname'] == 'localhost'
        assert kwargs['username'] == 'testuser'
        assert kwargs['password'] is None
        assert kwargs['key_filename'] == '/path/to/key'
        assert kwargs['port'] == 22

    def test_connect_preserves_card_key_passphrase(self, monkeypatch):
        from app.services import ssh_connection

        seen = []
        client = Mock()

        def auth_kwargs(password, key, passphrase, *, use_local_keys):
            seen.append((password, key, passphrase, use_local_keys))
            return {}

        monkeypatch.setattr('app.services.ssh_service.paramiko.SSHClient', lambda: client)
        monkeypatch.setattr(ssh_connection, 'prepare_trusted_client', lambda _client: None)
        monkeypatch.setattr(ssh_connection, 'connect_kwargs', auth_kwargs)
        monkeypatch.setattr(SSHService, 'connect_managed', lambda *_args, **_kwargs: None)

        SSHService().connect('192.0.2.10', 'operator', key='card-key', key_passphrase='card-phrase')

        assert seen == [(None, 'card-key', 'card-phrase', False)]
    
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
        
        # Мокаем клиентов. Ссылки держим локально: disconnect() обнуляет атрибуты,
        # поэтому проверять вызовы через service.* после него уже нельзя.
        mock_sftp = Mock()
        mock_client = Mock()
        service.sftp_client = mock_sftp
        service.client = mock_client

        service.disconnect()

        # Проверяем, что клиенты закрыты
        mock_sftp.close.assert_called_once()
        mock_client.close.assert_called_once()
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
        mock_stdout.channel = _stream_channel(stdout_data=b'output data')
        
        service.client = Mock()
        service.client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        result = service.execute_command('ls -la')
        
        assert result['exit_status'] == 0
        assert result['stdout'] == 'output data'
        assert result['stderr'] == ''
        service.client.exec_command.assert_called_once_with('ls -la', timeout=30)
    
    def test_execute_command_not_connected(self):
        """Тест выполнения команды без подключения"""
        service = SSHService()
        
        with pytest.raises(SSHConnectionError):
            service.execute_command('ls -la')

    def test_execute_remote_command_uses_bounded_job_service(self):
        service = SSHService()
        client = Mock()
        stdin, stdout, stderr = Mock(), Mock(), Mock()
        stdout.channel = _stream_channel(stdout_data=b'EXISTS\n')
        client.exec_command.return_value = stdin, stdout, stderr
        service.get_connection_pooled = Mock(return_value=client)

        result = service.execute_remote_command(
            '192.0.2.1', 'operator', 'fixture-password', '[ -f /tmp/x ]', timeout=8
        )

        assert result == {'success': True, 'output': 'EXISTS\n', 'error': '', 'exit_status': 0}
        client.exec_command.assert_called_once_with('[ -f /tmp/x ]', timeout=8)

    def test_execute_remote_command_returns_safe_error_code(self):
        from paramiko import SSHException
        service = SSHService()
        client = Mock()
        client.exec_command.side_effect = SSHException('private remote path')
        service.get_connection_pooled = Mock(return_value=client)

        result = service.execute_remote_command('192.0.2.1', 'operator', 'pw', 'true')

        assert result == {'success': False, 'output': '', 'error': 'exec_failed', 'exit_status': -1}

    def test_execute_command_does_not_leak_remote_exception(self):
        from paramiko import SSHException
        service = SSHService()
        service.client = Mock()
        service.client.exec_command.side_effect = SSHException('private remote path')

        with pytest.raises(SSHConnectionError) as caught:
            service.execute_command('true')

        assert 'private remote path' not in str(caught.value)
    
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
        
        # Мокаем SFTP клиента. client тоже нужен: upload_file идёт через
        # get_sftp_client(), а тот падает с SSHConnectionError без SSH-подключения.
        mock_sftp = Mock()
        service.client = Mock()
        service.sftp_client = mock_sftp

        service.upload_file('/local/path', '/remote/path')
        
        mock_sftp.put.assert_called_once_with('/local/path', '/remote/path')
    
    def test_download_file(self):
        """Тест скачивания файла"""
        service = SSHService()
        
        # Мокаем SFTP клиента
        mock_sftp = Mock()
        service.client = Mock()
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
        service.client = Mock()
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

    @staticmethod
    def _tools_client(ufw_status, uid='0'):
        client = Mock(spec=['exec_command'])

        def make_result(output: str):
            stdout = Mock()
            stdout.read.return_value = output.encode('utf-8')
            return Mock(), stdout, Mock()

        # Матчим по подстроке, а не по точной команде: код детекта утилит уже
        # переезжал с `which` на `command -v` с явным PATH, и точное сравнение
        # молча превращало тест в проверку ветки «утилита не установлена».
        def exec_side_effect(command, timeout=None):
            if command == 'id -u':
                return make_result(uid + '\n')
            if 'ufw status' in command:
                return make_result(ufw_status)
            if 'systemctl is-active vnstat' in command:
                return make_result('active\n')
            for name, path in (
                ('vnstat', '/usr/bin/vnstat'),
                ('jq', '/usr/bin/jq'),
                ('ufw', '/usr/sbin/ufw'),
                ('netstat', '/usr/bin/netstat'),
            ):
                if 'command -v %s ' % name in command:
                    return make_result('%s\n' % path)
            return make_result('')

        client.exec_command.side_effect = exec_side_effect
        return client

    def _check_tools(self, client, port=2222):
        service = SSHService()
        with patch.object(service, 'get_connection_pooled', return_value=client):
            return service.check_required_tools(ip='127.0.0.1', user='root', password='secret', port=port)

    def test_ufw_warns_only_when_the_ssh_port_has_no_allow_rule(self):
        """UFW включён, а правила для SSH-порта карточки нет — предупреждение с этим портом."""
        result = self._check_tools(self._tools_client('Status: active\n\n443/tcp  ALLOW  Anywhere\n'))
        ufw_tool = result['tools']['ufw']
        # Страховка от тихой деградации: если детект утилиты снова разъедется с
        # моком, тест должен падать здесь, а не проверять не ту ветку кода.
        assert ufw_tool['installed'] is True and ufw_tool['enabled'] is True
        assert ufw_tool['ssh_allowed'] is False
        assert '2222' in ufw_tool['warning']
        # root: команда без sudo (на многих VPS его нет)
        assert ufw_tool['fix_cmd'] == 'ufw allow 2222/tcp && ufw status numbered'
        assert result['all_ok'] is False

    def test_ufw_with_ssh_rule_or_disabled_is_not_a_warning(self):
        allowed = self._check_tools(self._tools_client('Status: active\n\n2222/tcp  ALLOW  Anywhere  # SSH\n'))
        assert allowed['tools']['ufw']['ssh_allowed'] is True and 'warning' not in allowed['tools']['ufw']
        assert allowed['all_ok'] is True
        disabled = self._check_tools(self._tools_client('Status: inactive\n'))
        assert disabled['tools']['ufw']['enabled'] is False and 'warning' not in disabled['tools']['ufw']

    def test_non_root_commands_keep_sudo_and_never_wait_for_a_password(self):
        client = self._tools_client('Status: active\n', uid='1000')
        service = SSHService()
        assert service._as_root(client, 'sudo ufw status') == 'sudo -n ufw status'
        root = self._tools_client('', uid='0')
        assert service._as_root(root, 'sudo journalctl -u x | sudo grep y') == 'journalctl -u x | grep y'
        assert service._as_root(root, 'echo pw | sudo -S true') == 'echo pw | sudo -S true'

    @pytest.mark.parametrize('status,port,expected', [
        ('22542/tcp                  ALLOW       Anywhere                   # SSH', 22542, True),
        ('22542/tcp (v6)             ALLOW       Anywhere (v6)', 22542, True),
        ('Anywhere on tailscale0     ALLOW       Anywhere', 22, False),
        ('22/tcp                     ALLOW IN    Anywhere', 22, True),
        ('OpenSSH                    ALLOW       Anywhere', 22, True),
        ('20000:30000/tcp            ALLOW       Anywhere', 22542, True),
        ('Anywhere                   REJECT      116.177.172.108', 22, False),
        ('22/tcp                     DENY        Anywhere', 22, False),
    ])
    def test_ufw_allows_port(self, status, port, expected):
        assert SSHService.ufw_allows_port('Status: active\n\n' + status, port) is expected

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

    def test_collect_stack_status_keeps_missing_units(self):
        """Статус показывает и запущенное, и то, чего на сервере нет."""
        service = SSHService()
        client = Mock()
        probe = "\n".join([
            "Id=telegramonly.service",
            "LoadState=loaded",
            "ActiveState=active",
            "",
            "Id=mita.service",
            "LoadState=not-found",
            "ActiveState=inactive",
            "",
        ])

        def fake_read(_client, command, timeout=30):
            if command.startswith("systemctl show"):
                return probe
            return ""

        with patch.object(service, "_read_command_output", side_effect=fake_read):
            rows = service._collect_stack_status(client, docker_names=[])

        by_name = {row["name"]: row for row in rows}
        assert by_name["telegramonly"]["status"] == "active"
        assert by_name["telegramonly"]["hint"] == ""
        assert by_name["mita"]["status"] == "not_installed"
        assert "install_mieru" in by_name["mita"]["hint"]
        assert by_name["headscale"]["status"] == "not_installed"
        assert by_name["headplane"]["group"] == "docker"

    def test_security_brief_hides_secrets_and_states_the_attack(self):
        """Разбор называет перебор SSH и не тащит секреты в промпт."""
        service = SSHService()
        samples = service._summarize_journal_errors(
            "Sep 23 12:00:01 host sshd[10]: Failed password for root from 198.51.100.50\n"
            "Sep 23 12:00:02 host app[11]: token=super-secret-value failed\n"
        )
        assert samples
        assert all("super-secret-value" not in item["message"] for item in samples)

        brief = service.build_security_brief(
            {
                "ssh_failures_24h": 6892,
                "top_failed_ips": [{"ip": "198.51.100.50", "count": 6892}],
                "failed_units": ["nginx.service"],
                "journal_samples": samples,
                "error_events_24h": 119,
                "fail2ban_banned": 0,
                "fail2ban_installed": False,
                "apt_update_known": False,
                "days_since_update": None,
                "security_updates_available": 0,
                "sshd": {
                    "password_authentication": "yes",
                    "permit_root_login": "yes",
                    "port": "22",
                },
            },
            server_name="srv",
            server_ip="198.51.100.80",
        )
        assert brief["has_incident"] is True
        assert "198.51.100.50" in brief["summary"]
        assert "nginx.service" in brief["summary"]
        assert "PasswordAuthentication" in brief["summary"]
        assert "Не предлагай атаки" in brief["prompt"]
        assert "super-secret-value" not in brief["prompt"]

    def test_load_diagnosis_asks_for_htop_when_both_tools_missing(self):
        service = SSHService()
        sample = "LOAD 0.02 0.08 0.10\nPROC sshd 1.2\n"
        with patch.object(service, "_read_command_output", return_value=sample):
            diagnosis = service._read_load_diagnosis(Mock(), 87.1)
        assert diagnosis["need_tools"] is True
        assert diagnosis["load"] == ["0.02", "0.08", "0.10"]
        assert diagnosis["top"][0]["cmd"] == "sshd"

        sample_with_tool = sample + "TOOL btop\n"
        with patch.object(service, "_read_command_output", return_value=sample_with_tool):
            diagnosis = service._read_load_diagnosis(Mock(), 12.0)
        assert diagnosis["need_tools"] is False
        assert diagnosis["btop"] is True


def _output_client(outputs):
    """Mock SSH client: the first matching substring decides the output."""
    client = Mock(spec=['exec_command'])

    def run(command, timeout=None):
        stdout = Mock()
        text = next((out for key, out in outputs if key in command), '')
        stdout.read.return_value = text.encode('utf-8')
        return Mock(), stdout, Mock()

    client.exec_command.side_effect = run
    return client


def test_cpu_sample_excludes_steal_and_reports_processes_now():
    # 200 jiffies in total: user 10 + system 10 = 10 %, steal 40 = 20 % shown apart, not as load.
    client = _output_client([('id -u', '0'), ('/proc/stat', 'CPU 200 10 10 0 40\nPROC 4.5 xray\nPROC 1.0 tailscaled\n')])
    sample = SSHService()._sample_cpu(client)
    assert sample == {'used': 10.0, 'steal': 20.0, 'top': [{'cmd': 'xray', 'cpu': '4.5'}, {'cmd': 'tailscaled', 'cpu': '1.0'}]}
    assert SSHService()._sample_cpu(_output_client([('id -u', '0')])) is None


def test_cpu_sample_script_skips_its_own_processes():
    script = SSHService._CPU_SAMPLE
    assert '$2 == self || $3 == self || $2 == parent { next }' in script
    assert script.count('/proc/stat') == 2 and 'sleep 1' in script


def test_security_events_count_each_ssh_attempt_once():
    commands = []
    client = _output_client([('id -u', '0'), ('wc -l', '14'), ('uniq -c', '     14 45.198.224.51'),
                             ('systemctl --failed', 'ifup@ens3.service\n'), ('grep -vc', '3'),
                             ('Start-Date', '2026-10-24  17:24:20')])
    original = client.exec_command.side_effect
    client.exec_command.side_effect = lambda command, timeout=None: (commands.append(command), original(command))[1]
    service = SSHService()
    with patch.object(service, 'get_connection_pooled', return_value=client), \
            patch.object(service, '_get_listening_ports', return_value=[]):
        events = service.get_security_events('127.0.0.1', 'root', 'x')
    assert events['ssh_failures_24h'] == 14 and events['top_failed_ips'] == [{'ip': '45.198.224.51', 'count': 14}]
    assert events['failed_units'] == ['ifup@ens3.service'] and events['failed_services'] == 1
    assert events['last_upgrade'] == '2026-10-24 17:24'
    ssh_commands = [c for c in commands if 'Failed (password' in c]
    # sshd lines only: PAM repeats every attempt, and the journal records our own sudo command line.
    assert ssh_commands and all('_COMM=sshd' in c and 'authentication failure' not in c for c in ssh_commands)
    # root: no sudo at all (vps45379 has none, every command used to fail silently)
    assert not any(c.startswith('sudo ') or ' sudo ' in c for c in commands)


@pytest.mark.parametrize('output, state', [('ok', 'ok'), ('outdated', 'outdated'), ('absent', 'absent'), ('', 'unknown')])
def test_history_script_state(output, state):
    client = _output_client([('id -u', '0'), ('update-metrics-history.sh', output)])
    assert SSHService()._history_script_state(client) == state


def test_repo_history_script_uses_proc_stat():
    from app.routes.api import METRICS_HISTORY_SCRIPT
    assert '/proc/stat' in METRICS_HISTORY_SCRIPT and 'CPU_USAGE=$(top' not in METRICS_HISTORY_SCRIPT


def test_services_are_probed_in_one_command():
    descriptors = [
        {'name': 'xray', 'display_name': 'Xray', 'group': 'proxy', 'unit_candidates': ['xray', 'xray-core']},
        {'name': 'nginx', 'display_name': 'Nginx', 'group': 'system', 'unit_candidates': ['nginx']},
        {'name': 'gone', 'display_name': 'Gone', 'group': 'system', 'unit_candidates': ['gone']},
    ]
    output = ('UPTIME=90000.50\n\n'
              'Id=xray.service\nLoadState=not-found\nActiveState=inactive\nUnitFileState=\nActiveEnterTimestampMonotonic=0\n\n'
              'Id=xray-core.service\nLoadState=loaded\nActiveState=active\nUnitFileState=enabled\nActiveEnterTimestampMonotonic=500000000\n\n'
              'Id=nginx.service\nLoadState=loaded\nActiveState=failed\nUnitFileState=disabled\nActiveEnterTimestampMonotonic=0\n\n'
              'Id=gone.service\nLoadState=not-found\nActiveState=inactive\nUnitFileState=\nActiveEnterTimestampMonotonic=0\n')
    client = _output_client([('id -u', '0'), ('systemctl show', output)])
    xray, nginx, gone = SSHService()._probe_services(client, descriptors)
    # 90000 − 500 с = 89500 с = 1 д 0 ч
    assert (xray['status'], xray['unit_name'], xray['enabled'], xray['uptime']) == ('active', 'xray-core', 'enabled', '1d 0h')
    assert (nginx['status'], nginx['enabled'], nginx['uptime']) == ('failed', 'disabled', 'stopped')
    assert gone['status'] == 'not_installed' and gone['unit_name'] is None
    commands = [call.args[0] for call in client.exec_command.call_args_list if 'systemctl' in call.args[0]]
    assert len(commands) == 1


def test_security_brief_keeps_password_login_advice_for_password_cards():
    # Разбор sshd -T не должен затирать аргумент key: иначе совет «можно выключить пароль» отрежет приложение
    service = SSHService()
    client = _output_client([('id -u', '0'), ('sshd -T', 'passwordauthentication yes\npermitrootlogin yes\nport 22542'),
                             ('fail2ban-client', 'no')])
    with patch.object(service, 'get_security_events', return_value={}), \
            patch.object(service, 'get_connection_pooled', return_value=client):
        brief = service.get_security_brief('192.0.2.4', 'root', 'fixture', port=22542)
    assert 'можно выключить' not in brief['prompt']
    assert 'приложение сейчас входит паролем' in brief['prompt']
