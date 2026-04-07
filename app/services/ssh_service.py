import paramiko
from typing import Optional, Dict, List
from paramiko.ssh_exception import SSHException, AuthenticationException
from ..exceptions import SSHConnectionError, AuthenticationError
import logging
import re
import threading

logger = logging.getLogger(__name__)

class SSHService:
    """Сервис для работы с SSH/SFTP с connection pooling"""
    
    # Кэш подключений
    _connection_pool = {}
    _pool_lock = threading.Lock()
    _process_exclusions = {'ps', 'head', 'bash', 'sh', 'sudo', 'timeout'}
    _known_port_labels = {
        '22': 'SSH',
        '80': 'HTTP',
        '443': 'HTTPS / Xray / Hysteria2',
        '465': 'MTProto / SMTPS',
        '993': 'MTProto / IMAPS',
        '8000': 'TelegramSimple API',
        '8501': 'Dockhand',
    }
    _service_catalog = [
        {'name': 'mtproto-proxy', 'display_name': 'MTProto Proxy', 'group': 'proxy', 'unit_candidates': ['mtproto-proxy']},
        {'name': 'xray', 'display_name': 'Xray', 'group': 'proxy', 'unit_candidates': ['xray']},
        {'name': 'sing-box', 'display_name': 'Sing-box', 'group': 'proxy', 'unit_candidates': ['sing-box', 'singbox']},
        {'name': 'hysteria', 'display_name': 'Hysteria2', 'group': 'proxy', 'unit_candidates': ['hysteria-server', 'hysteria']},
        {'name': 'nginx', 'display_name': 'Nginx', 'group': 'system', 'unit_candidates': ['nginx']},
        {'name': 'apache2', 'display_name': 'Apache', 'group': 'system', 'unit_candidates': ['apache2']},
        {'name': 'ssh', 'display_name': 'OpenSSH', 'group': 'system', 'unit_candidates': ['ssh', 'sshd']},
        {'name': 'postgresql', 'display_name': 'PostgreSQL', 'group': 'system', 'unit_candidates': ['postgresql']},
        {'name': 'mysql', 'display_name': 'MySQL', 'group': 'system', 'unit_candidates': ['mysql', 'mariadb']},
        {'name': 'docker', 'display_name': 'Docker', 'group': 'system', 'unit_candidates': ['docker']},
        {'name': 'redis-server', 'display_name': 'Redis', 'group': 'system', 'unit_candidates': ['redis-server']},
    ]
    
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp_client: Optional[paramiko.SFTPClient] = None

    @staticmethod
    def _sort_ports(ports: List[str]) -> List[str]:
        return sorted(ports, key=lambda p: (not p.isdigit(), int(p) if p.isdigit() else p))

    @classmethod
    def _parse_listener_ports(cls, output: str) -> List[str]:
        ports = set()
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            endpoint = line.split('|', 1)[-1].strip()
            match = re.search(r':(\d+)$', endpoint)
            if match:
                ports.add(match.group(1))

        return cls._sort_ports(list(ports))

    @classmethod
    def _parse_top_processes(cls, output: str, limit: int = 5) -> List[Dict[str, str]]:
        processes: List[Dict[str, str]] = []

        for idx, raw_line in enumerate(output.splitlines()):
            line = raw_line.strip()
            if not line:
                continue
            if idx == 0 and 'PID' in line and '%CPU' in line:
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            cmd = parts[1].strip()
            if cmd in cls._process_exclusions:
                continue

            processes.append({
                'pid': parts[0],
                'cmd': cmd,
                'cpu': parts[2],
                'mem': parts[3],
            })

            if len(processes) >= limit:
                break

        return processes

    def _read_command_output(self, client, command: str, timeout: int = 30) -> str:
        _, stdout, _ = client.exec_command(command, timeout=timeout)
        return stdout.read().decode('utf-8').strip()

    @classmethod
    def _label_port(cls, port: str) -> str:
        label = cls._known_port_labels.get(str(port), '')
        return f"{port} ({label})" if label else str(port)

    @classmethod
    def _label_ports(cls, ports: List[str]) -> List[str]:
        return [cls._label_port(port) for port in ports]

    def _probe_service(self, client, descriptor: Dict) -> Dict:
        """Проверить наличие и статус systemd unit по набору candidate names."""
        matched_name = None
        for candidate in descriptor.get('unit_candidates', []):
            output = self._read_command_output(
                client,
                f'systemctl list-unit-files --type=service 2>/dev/null | grep -E "^{candidate}\\.service\\s"',
                timeout=10
            )
            if output:
                matched_name = candidate
                break

        if not matched_name:
            return {
                'name': descriptor['name'],
                'display_name': descriptor['display_name'],
                'group': descriptor['group'],
                'status': 'not_installed',
                'enabled': 'not-found',
                'uptime': '-',
                'unit_name': None,
            }

        status = self._read_command_output(client, f'systemctl is-active {matched_name} 2>/dev/null', timeout=10) or 'unknown'
        enabled = self._read_command_output(client, f'systemctl is-enabled {matched_name} 2>/dev/null', timeout=10) or 'unknown'
        uptime_str = 'stopped'

        if status == 'active':
            try:
                import time
                timestamp_line = self._read_command_output(
                    client,
                    f'systemctl show {matched_name} --property=ActiveEnterTimestamp',
                    timeout=10
                )
                if timestamp_line and '=' in timestamp_line:
                    timestamp_str = timestamp_line.split('=', 1)[1].strip()
                    if timestamp_str:
                        start_time = self._read_command_output(
                            client,
                            f'date -d "{timestamp_str}" +%s',
                            timeout=10
                        )
                        if start_time.isdigit():
                            seconds = int(time.time()) - int(start_time)
                            days = seconds // 86400
                            hours = (seconds % 86400) // 3600
                            mins = (seconds % 3600) // 60
                            if days > 0:
                                uptime_str = f"{days}d {hours}h"
                            elif hours > 0:
                                uptime_str = f"{hours}h {mins}m"
                            else:
                                uptime_str = f"{mins}m"
            except Exception:
                uptime_str = 'active'

        return {
            'name': descriptor['name'],
            'display_name': descriptor['display_name'],
            'group': descriptor['group'],
            'status': status,
            'enabled': enabled,
            'uptime': uptime_str,
            'unit_name': matched_name,
        }

    @staticmethod
    def _parse_cpu_used_pct(cpu_line: str) -> float:
        normalized = (cpu_line or '').replace(',', '.')
        match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*%?\s*id\b', normalized)
        if not match:
            return 0.0

        idle_pct = float(match.group(1))
        return round(max(0.0, min(100.0, 100.0 - idle_pct)), 1)

    def _get_cpu_used_pct(self, client, timeout: int = 30) -> float:
        proc_stat_used = self._read_command_output(
            client,
            "sh -c 'read cpu u n s i io irq sirq st rest < /proc/stat; total1=$((u+n+s+i+io+irq+sirq+st)); idle1=$((i+io)); sleep 1; read cpu u n s i io irq sirq st rest < /proc/stat; total2=$((u+n+s+i+io+irq+sirq+st)); idle2=$((i+io)); dt=$((total2-total1)); di=$((idle2-idle1)); awk \"BEGIN { if ($dt > 0) printf \\\"%.1f\\\", (100*($dt-$di)/$dt); else print 0 }\"'",
            timeout=max(timeout, 5)
        )
        try:
            cpu_used = float((proc_stat_used or '0').replace(',', '.'))
            if 0.0 <= cpu_used <= 100.0:
                return round(cpu_used, 1)
        except ValueError:
            pass

        cpu_line = self._read_command_output(
            client,
            "LANG=C LC_ALL=C top -bn1 | sed -n 's/^%\\?Cpu(s)\\?:\\s*//p' | head -n1",
            timeout=timeout
        )
        cpu_used = self._parse_cpu_used_pct(cpu_line)
        if cpu_used > 0:
            return cpu_used

        cpu_line = self._read_command_output(
            client,
            "top -bn1 | sed -n 's/^%\\?Cpu(s)\\?:\\s*//p' | head -n1",
            timeout=timeout
        )
        cpu_used = self._parse_cpu_used_pct(cpu_line)
        if cpu_used > 0:
            return cpu_used

        idle_raw = self._read_command_output(
            client,
            "LANG=C LC_ALL=C vmstat 1 2 | tail -1 | awk '{print $15}'",
            timeout=timeout
        )
        try:
            idle_pct = float((idle_raw or '0').replace(',', '.'))
        except ValueError:
            return 0.0

        return round(max(0.0, min(100.0, 100.0 - idle_pct)), 1)

    def _get_listening_ports(self, client) -> List[str]:
        output = self._read_command_output(
            client,
            "ss -tulnH 2>/dev/null | awk '{print $1 \"|\" $5}'",
            timeout=15
        )

        ports = self._parse_listener_ports(output)
        if ports:
            return ports

        output = self._read_command_output(
            client,
            "netstat -tuln 2>/dev/null | awk 'NR>2 {print $1 \"|\" $4}'",
            timeout=15
        )
        return self._parse_listener_ports(output)
    
    @classmethod
    def get_connection_pooled(cls, hostname: str, port: int, username: str, password: Optional[str] = None, connection_timeout: int = 30):
        """Получить или создать SSH подключение (с переиспользованием)"""
        key = f"{hostname}:{port}:{username}"
        
        with cls._pool_lock:
            # Проверяем есть ли живое подключение
            if key in cls._connection_pool:
                conn = cls._connection_pool[key]
                try:
                    if conn.get_transport() and conn.get_transport().is_active():
                        # Проверяем что подключение работает
                        conn.exec_command('echo test', timeout=5)
                        logger.info(f"♻️ Reusing existing connection to {hostname}")
                        return conn
                    else:
                        logger.info(f"💀 Old connection dead, removing")
                        del cls._connection_pool[key]
                except Exception as e:
                    logger.warning(f"Connection check failed: {e}")
                    if key in cls._connection_pool:
                        del cls._connection_pool[key]
            
            # Создаем новое подключение
            logger.info(f"🔌 Creating new SSH connection to {hostname} (timeout: {connection_timeout}s)")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                # Для быстрых проверок используем короткие таймауты
                banner_timeout = min(connection_timeout * 2, 60)
                auth_timeout = min(connection_timeout, 30)
                
                ssh.connect(
                    hostname,
                    port=port,
                    username=username,
                    password=password,
                    timeout=connection_timeout,     # Настраиваемый таймаут
                    banner_timeout=banner_timeout,  # Динамический на основе connection_timeout
                    auth_timeout=auth_timeout,      # Динамический на основе connection_timeout
                    look_for_keys=False,            # Не искать SSH ключи (быстрее)
                    allow_agent=False               # Не использовать SSH agent
                )
                
                cls._connection_pool[key] = ssh
                logger.info(f"✅ New connection created and pooled: {hostname}")
                return ssh
                
            except Exception as e:
                logger.error(f"Failed to connect to {hostname}: {e}")
                raise
    
    @classmethod
    def close_all(cls):
        """Закрыть все подключения (вызывать при остановке приложения)"""
        logger.info("Closing all SSH connections...")
        with cls._pool_lock:
            for key, conn in list(cls._connection_pool.items()):
                try:
                    logger.info(f"Closing connection: {key}")
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection {key}: {e}")
            cls._connection_pool.clear()
        logger.info("All SSH connections closed")
    
    def connect(self, hostname: str, username: str, 
                password: Optional[str] = None,
                key_filename: Optional[str] = None,
                port: int = 22,
                timeout: int = 30) -> None:  # Увеличен с 10 до 30
        """Установка SSH соединения"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info(f"Connecting to {hostname}:{port} as {username}")
            
            self.client.connect(
                hostname=hostname,
                username=username,
                password=password,
                key_filename=key_filename,
                port=port,
                timeout=timeout,
                banner_timeout=60,    # Время ожидания SSH banner
                auth_timeout=30,      # Время на аутентификацию
                look_for_keys=False,  # Не искать SSH ключи (быстрее)
                allow_agent=False     # Не использовать SSH agent
            )
            
            logger.info(f"Successfully connected to {hostname}")
            
        except AuthenticationException as e:
            logger.error(f"Authentication failed for {username}@{hostname}: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")
        except SSHException as e:
            logger.error(f"SSH connection failed to {hostname}: {str(e)}")
            raise SSHConnectionError(f"SSH connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to {hostname}: {str(e)}")
            raise SSHConnectionError(f"Failed to connect: {str(e)}")
    
    def disconnect(self) -> None:
        """Закрытие соединения"""
        try:
            if self.sftp_client:
                self.sftp_client.close()
                self.sftp_client = None
                
            if self.client:
                self.client.close()
                self.client = None
                
            logger.info("SSH connection closed")
        except Exception as e:
            logger.error(f"Error closing SSH connection: {str(e)}")
    
    def execute_command(self, command: str) -> Dict[str, str]:
        """Выполнение команды на удаленном сервере"""
        if not self.client:
            raise SSHConnectionError("Not connected to SSH server")
        
        try:
            logger.info(f"Executing command: {command}")
            stdin, stdout, stderr = self.client.exec_command(command)
            
            exit_status = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            return {
                'exit_status': exit_status,
                'stdout': stdout_data,
                'stderr': stderr_data
            }
        except Exception as e:
            logger.error(f"Error executing command '{command}': {str(e)}")
            raise SSHConnectionError(f"Command execution failed: {str(e)}")
    
    def execute_remote_command(self, ip: str, user: str, password: str, command: str, 
                               port: int = 22, timeout: int = 30, connection_timeout: int = None) -> Dict:
        """Выполнение команды на удаленном сервере (без предварительного подключения)"""
        try:
            # Если connection_timeout не указан, используем timeout для подключения
            if connection_timeout is None:
                connection_timeout = timeout
            
            # Используем connection pooling с настраиваемым таймаутом
            client = self.get_connection_pooled(ip, port, user, password, connection_timeout=connection_timeout)
            
            logger.info(f"Executing remote command on {ip}: {command}")
            _, stdout, stderr = client.exec_command(command, timeout=timeout)
            
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            exit_status = stdout.channel.recv_exit_status()
            
            return {
                'success': exit_status == 0,
                'output': output,
                'error': error,
                'exit_status': exit_status
            }
        except Exception as e:
            logger.error(f"Error executing remote command on {ip}: {str(e)}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_status': -1
            }
    
    def get_sftp_client(self) -> paramiko.SFTPClient:
        """Получение SFTP клиента"""
        if not self.client:
            raise SSHConnectionError("Not connected to SSH server")
        
        if not self.sftp_client:
            try:
                self.sftp_client = self.client.open_sftp()
                logger.info("SFTP client created")
            except Exception as e:
                logger.error(f"Error creating SFTP client: {str(e)}")
                raise SSHConnectionError(f"SFTP client creation failed: {str(e)}")
        
        return self.sftp_client
    
    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Загрузка файла на сервер"""
        sftp = self.get_sftp_client()
        try:
            logger.info(f"Uploading {local_path} to {remote_path}")
            sftp.put(local_path, remote_path)
            logger.info("File uploaded successfully")
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise SSHConnectionError(f"File upload failed: {str(e)}")
    
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Скачивание файла с сервера"""
        sftp = self.get_sftp_client()
        try:
            logger.info(f"Downloading {remote_path} to {local_path}")
            sftp.get(remote_path, local_path)
            logger.info("File downloaded successfully")
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise SSHConnectionError(f"File download failed: {str(e)}")
    
    def list_directory(self, remote_path: str = '.') -> List[Dict]:
        """Получение списка файлов в директории"""
        sftp = self.get_sftp_client()
        try:
            logger.info(f"Listing directory: {remote_path}")
            files = sftp.listdir_attr(remote_path)
            
            result = []
            for file_attr in files:
                result.append({
                    'filename': file_attr.filename,
                    'size': file_attr.st_size,
                    'permissions': oct(file_attr.st_mode)[-3:],
                    'modified': file_attr.st_mtime
                })
            
            return result
        except Exception as e:
            logger.error(f"Error listing directory: {str(e)}")
            raise SSHConnectionError(f"Directory listing failed: {str(e)}")
    
    def get_server_stats(self, ip: str, user: str, password: str, port: int = 22, timeout: int = 30) -> Dict:
        """Получение статистики сервера через SSH"""
        stats = {}
        
        try:
            # Используем connection pooling
            client = self.get_connection_pooled(ip, port, user, password)
            
            # Uptime
            try:
                _, stdout, _ = client.exec_command('uptime -p 2>/dev/null || uptime')
                uptime_output = stdout.read().decode('utf-8').strip()
                stats['uptime'] = uptime_output
            except:
                stats['uptime'] = 'N/A'
            
            # OS Info
            try:
                _, stdout, _ = client.exec_command('cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d \'"\'')
                os_name = stdout.read().decode('utf-8').strip()
                stats['os'] = os_name if os_name else 'Linux'
            except:
                stats['os'] = 'Linux'
            
            # CPU Info
            try:
                _, stdout, _ = client.exec_command('nproc')
                cores = stdout.read().decode('utf-8').strip()

                _, stdout, _ = client.exec_command('uname -r')
                kernel = stdout.read().decode('utf-8').strip()
                
                stats['cpu'] = {
                    'cores': int(cores) if cores else 0,
                    'used_pct': self._get_cpu_used_pct(client, timeout=timeout),
                    'kernel': kernel
                }
            except:
                stats['cpu'] = {'cores': 0, 'used_pct': 0.0, 'kernel': 'N/A'}
            
            # Memory Info
            try:
                _, stdout, _ = client.exec_command('free -m | grep Mem')
                mem_line = stdout.read().decode('utf-8').strip().split()
                total_mem = int(mem_line[1])
                used_mem = int(mem_line[2])
                
                stats['mem'] = {
                    'total_mb': total_mem,
                    'used_mb': used_mem,
                    'used_pct': round((used_mem / total_mem * 100), 1) if total_mem > 0 else 0
                }
            except:
                stats['mem'] = {'total_mb': 0, 'used_mb': 0, 'used_pct': 0}
            
            # Swap Info
            try:
                _, stdout, _ = client.exec_command('free -m | grep Swap')
                swap_line = stdout.read().decode('utf-8').strip().split()
                total_swap = int(swap_line[1])
                used_swap = int(swap_line[2])
                
                stats['swap'] = {
                    'total_mb': total_swap,
                    'used_mb': used_swap,
                    'used_pct': round((used_swap / total_swap * 100), 1) if total_swap > 0 else 0
                }
            except:
                stats['swap'] = {'total_mb': 0, 'used_mb': 0, 'used_pct': 0}
            
            # Load Average
            try:
                _, stdout, _ = client.exec_command('cat /proc/loadavg')
                load_line = stdout.read().decode('utf-8').strip().split()
                stats['load'] = {
                    '1m': load_line[0] if len(load_line) > 0 else '0',
                    '5m': load_line[1] if len(load_line) > 1 else '0',
                    '15m': load_line[2] if len(load_line) > 2 else '0'
                }
            except:
                stats['load'] = {'1m': '0', '5m': '0', '15m': '0'}
            
            # Disk Info
            try:
                _, stdout, _ = client.exec_command('df -h | grep -E "^/dev/" | head -10')
                disk_lines = stdout.read().decode('utf-8').strip().split('\n')
                disks = []
                for line in disk_lines:
                    if line:
                        parts = line.split()
                        if len(parts) >= 6:
                            disks.append({
                                'device': parts[0],
                                'size': parts[1],
                                'used': parts[2],
                                'avail': parts[3],
                                'used_pct': parts[4].replace('%', ''),
                                'mount': parts[5]
                            })
                stats['disks'] = disks
            except:
                stats['disks'] = []
            
            # Processes (Top 5 by CPU)
            try:
                _, stdout, _ = client.exec_command('ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 15')
                ps_output = stdout.read().decode('utf-8').strip()
                stats['processes'] = self._parse_top_processes(ps_output)
            except:
                stats['processes'] = []
            
            # Network interfaces
            try:
                _, stdout, _ = client.exec_command('ip -o addr show')
                ip_lines = stdout.read().decode('utf-8').strip().split('\n')
                networks = []
                for line in ip_lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            networks.append({
                                'interface': parts[1],
                                'family': parts[2],
                                'address': parts[3]
                            })
                stats['net'] = networks
            except:
                stats['net'] = []
            
            # Docker Info
            try:
                _, stdout, _ = client.exec_command('docker --version 2>/dev/null')
                docker_version = stdout.read().decode('utf-8').strip()
                
                _, stdout, _ = client.exec_command('docker ps --format "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}" 2>/dev/null')
                containers_output = stdout.read().decode('utf-8').strip().split('\n')
                containers = []
                for line in containers_output:
                    if line:
                        parts = line.split('|')
                        if len(parts) >= 4:
                            containers.append({
                                'id': parts[0],
                                'name': parts[1],
                                'status': parts[2],
                                'image': parts[3]
                            })
                
                stats['docker'] = {
                    'present': bool(docker_version),
                    'version': docker_version.replace('Docker version ', '') if docker_version else '',
                    'running': len(containers),
                    'names': [c['name'] for c in containers],
                    'containers': containers
                }
            except:
                stats['docker'] = {'present': False, 'version': '', 'running': 0, 'names': [], 'containers': []}
            
            logger.info(f"Successfully collected stats from {ip}")
            return stats
            
        except paramiko.AuthenticationException as e:
            logger.error(f"SSH authentication failed for {user}@{ip}: {str(e)}")
            raise SSHConnectionError(f"SSH authentication failed for {user}@{ip}. Please check username and password.")
        except paramiko.SSHException as e:
            logger.error(f"SSH connection error to {ip}: {str(e)}")
            if "Error reading SSH protocol banner" in str(e):
                raise SSHConnectionError(
                    f"Server {ip} is not responding or SSH service is not running. "
                    f"Please check if the server is online and SSH port ({port}) is accessible."
                )
            else:
                raise SSHConnectionError(f"SSH connection failed to {ip}: {str(e)}")
        except paramiko.socket.timeout as e:
            logger.error(f"SSH connection timeout to {ip}: {str(e)}")
            raise SSHConnectionError(f"Connection timeout to {ip}. Server may be slow or unreachable.")
        except Exception as e:
            logger.error(f"Error collecting stats from {ip}: {str(e)}")
            raise SSHConnectionError(f"Failed to collect stats from {ip}: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    @property
    def is_connected(self) -> bool:
        """Проверка состояния соединения"""
        return self.client is not None and self.client.get_transport() is not None
    
    def get_network_stats(self, ip: str, user: str, password: str, port: int = 22, timeout: int = 30) -> Dict:
        """Получение статистики сетевого трафика (суммарно со всех интерфейсов)"""
        import time
        
        try:
            # Используем connection pooling
            client = self.get_connection_pooled(ip, port, user, password)
            
            # Получаем список всех активных сетевых интерфейсов (кроме lo - loopback)
            # Включаем физические (eth0, ens3) и виртуальные VPN-интерфейсы (tun0, wg0, tap0)
            _, stdout, _ = client.exec_command(
                "ls /sys/class/net/ | grep -v '^lo$' | grep -E '^(eth|ens|eno|enp|wlan|wlp|tun|tap|wg|ppp|ipsec)'"
            )
            interfaces = stdout.read().decode('utf-8').strip().split('\n')
            interfaces = [i.strip() for i in interfaces if i.strip()]
            
            if not interfaces:
                # Fallback на eth0, если ничего не найдено
                interfaces = ['eth0']
            
            logger.info(f"Monitoring network traffic on interfaces: {', '.join(interfaces)}")
            
            # Получаем начальные значения для всех интерфейсов
            total_rx1 = 0
            total_tx1 = 0
            
            for iface in interfaces:
                try:
                    _, stdout, _ = client.exec_command(
                        f"cat /sys/class/net/{iface}/statistics/rx_bytes /sys/class/net/{iface}/statistics/tx_bytes 2>/dev/null"
                    )
                    data = stdout.read().decode('utf-8').strip().split('\n')
                    if len(data) >= 2:
                        total_rx1 += int(data[0])
                        total_tx1 += int(data[1])
                except:
                    # Пропускаем интерфейсы, которые не удалось прочитать
                    continue
            
            time1 = time.time()
            
            # Ждем 1 секунду
            time.sleep(1)
            
            # Получаем конечные значения для всех интерфейсов
            total_rx2 = 0
            total_tx2 = 0
            
            for iface in interfaces:
                try:
                    _, stdout, _ = client.exec_command(
                        f"cat /sys/class/net/{iface}/statistics/rx_bytes /sys/class/net/{iface}/statistics/tx_bytes 2>/dev/null"
                    )
                    data = stdout.read().decode('utf-8').strip().split('\n')
                    if len(data) >= 2:
                        total_rx2 += int(data[0])
                        total_tx2 += int(data[1])
                except:
                    continue
            
            time2 = time.time()
            
            # Вычисляем скорость
            time_diff = time2 - time1
            rx_speed = (total_rx2 - total_rx1) / time_diff / 1048576  # MB/s
            tx_speed = (total_tx2 - total_tx1) / time_diff / 1048576  # MB/s
            
            # Получаем суточную статистику (если vnstat установлен)
            # Для vnstat используем основной интерфейс или сумму всех
            _, stdout, _ = client.exec_command('which vnstat')
            has_vnstat = bool(stdout.read().decode('utf-8').strip())
            
            daily_rx = "N/A"
            daily_tx = "N/A"
            if has_vnstat:
                try:
                    # Пытаемся получить суммарную статистику за 24 часа
                    # vnstat может показывать общую статистику через --json (если поддерживается)
                    _, stdout, _ = client.exec_command('vnstat --json 2>/dev/null')
                    vnstat_json = stdout.read().decode('utf-8').strip()
                    
                    if vnstat_json:
                        # Если есть JSON поддержка - парсим её
                        import json
                        try:
                            vnstat_data = json.loads(vnstat_json)
                            # Суммируем трафик за сегодня по всем интерфейсам
                            total_rx_bytes = 0
                            total_tx_bytes = 0
                            
                            for iface_data in vnstat_data.get('interfaces', []):
                                traffic = iface_data.get('traffic', {})
                                days = traffic.get('day', [])
                                if days:
                                    # Берем последний день (сегодня)
                                    today = days[-1]
                                    total_rx_bytes += today.get('rx', 0)
                                    total_tx_bytes += today.get('tx', 0)
                            
                            # Конвертируем в удобные единицы
                            if total_rx_bytes >= 1073741824:  # >= 1 GiB
                                daily_rx = f"{total_rx_bytes / 1073741824:.2f} GiB"
                            else:
                                daily_rx = f"{total_rx_bytes / 1048576:.2f} MiB"
                            
                            if total_tx_bytes >= 1073741824:  # >= 1 GiB
                                daily_tx = f"{total_tx_bytes / 1073741824:.2f} GiB"
                            else:
                                daily_tx = f"{total_tx_bytes / 1048576:.2f} MiB"
                                
                        except (json.JSONDecodeError, KeyError):
                            pass
                    
                    # Если JSON не сработал, пробуем старый формат для основного интерфейса
                    if daily_rx == "N/A":
                        main_interface = interfaces[0] if interfaces else 'eth0'
                        _, stdout, _ = client.exec_command(f'vnstat -i {main_interface} --oneline 2>/dev/null')
                        vnstat_output = stdout.read().decode('utf-8').strip()
                        if vnstat_output:
                            parts = vnstat_output.split(';')
                            if len(parts) > 5:
                                daily_rx = parts[3].strip()
                                daily_tx = parts[4].strip()
                except Exception as e:
                    logger.debug(f"Could not get vnstat data: {e}")
                    pass
            
            return {
                'interface': f"all ({len(interfaces)} interfaces)",
                'interfaces': interfaces,
                'current': {
                    'download': f"{rx_speed:.2f}",
                    'upload': f"{tx_speed:.2f}",
                    'unit': 'MB/s'
                },
                'daily': {
                    'download': daily_rx,
                    'upload': daily_tx
                },
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error getting network stats from {ip}: {str(e)}")
            return {
                'interface': 'N/A',
                'current': {'download': '0.00', 'upload': '0.00', 'unit': 'MB/s'},
                'daily': {'download': 'N/A', 'upload': 'N/A'},
                'timestamp': int(time.time()),
                'error': str(e)
            }
    
    def get_firewall_stats(self, ip: str, user: str, password: str, port: int = 22, timeout: int = 30) -> Dict:
        """Получение статистики брандмауэра и listening ports"""
        import datetime
        
        try:
            # Используем connection pooling
            client = self.get_connection_pooled(ip, port, user, password)

            listening_ports = self._get_listening_ports(client)
            open_ports = ', '.join(listening_ports) if listening_ports else 'none'
            labeled_open_ports = ', '.join(self._label_ports(listening_ports)) if listening_ports else 'none'

            backend = 'none'
            status = 'inactive'
            firewall_ports = 'none'
            blocked_24h = 0
            last_block_line = ''

            ufw_installed = bool(self._read_command_output(client, 'command -v ufw', timeout=10))
            if ufw_installed:
                backend = 'ufw'
                status = self._read_command_output(
                    client,
                    'sudo ufw status 2>/dev/null | grep "Status:" | awk \'{print $2}\'',
                    timeout=10
                ) or 'inactive'
                firewall_ports_output = self._read_command_output(
                    client,
                    'sudo ufw status numbered 2>/dev/null | grep -E "^\\[" | awk \'{print $3}\' | cut -d\'/\' -f1 | sort -u',
                    timeout=10
                )
                firewall_ports_list = [p for p in firewall_ports_output.split('\n') if p]
                firewall_ports = ', '.join(firewall_ports_list) if firewall_ports_list else 'none'

                today = datetime.datetime.now().strftime('%b %e')
                blocked_output = self._read_command_output(
                    client,
                    f'sudo grep "UFW BLOCK" /var/log/ufw.log 2>/dev/null | grep "{today}" | wc -l',
                    timeout=10
                )
                blocked_24h = int(blocked_output) if blocked_output.isdigit() else 0
                last_block_line = self._read_command_output(
                    client,
                    'sudo grep "UFW BLOCK" /var/log/ufw.log 2>/dev/null | tail -1',
                    timeout=10
                )
            else:
                firewalld_state = self._read_command_output(client, 'systemctl is-active firewalld 2>/dev/null', timeout=10)
                if firewalld_state in {'active', 'inactive', 'failed'}:
                    backend = 'firewalld'
                    status = 'active' if firewalld_state == 'active' else 'inactive'
                else:
                    nft_rules = self._read_command_output(client, 'sudo nft list ruleset 2>/dev/null | head -20', timeout=10)
                    if nft_rules:
                        backend = 'nftables'
                        status = 'active'
                    else:
                        iptables_rules = self._read_command_output(client, 'sudo iptables -S 2>/dev/null | head -20', timeout=10)
                        if iptables_rules:
                            backend = 'iptables'
                            status = 'active'

            last_blocked_ip = 'none'
            last_blocked_port = '0'
            if last_block_line:
                ip_match = re.search(r'SRC=([0-9.]+)', last_block_line)
                port_match = re.search(r'DPT=([0-9]+)', last_block_line)
                if ip_match:
                    last_blocked_ip = ip_match.group(1)
                if port_match:
                    last_blocked_port = port_match.group(1)

            return {
                'status': status,
                'backend': backend,
                'open_ports': open_ports,
                'open_ports_labeled': labeled_open_ports,
                'open_ports_details': [
                    {'port': p, 'label': self._known_port_labels.get(str(p), '')}
                    for p in listening_ports
                ],
                'firewall_ports': firewall_ports,
                'listening_ports_count': len(listening_ports),
                'blocked_24h': blocked_24h,
                'last_blocked': {
                    'ip': last_blocked_ip,
                    'port': last_blocked_port,
                    'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting firewall stats from {ip}: {str(e)}")
            return {
                'status': 'unknown',
                'backend': 'none',
                'open_ports': 'N/A',
                'open_ports_labeled': 'N/A',
                'open_ports_details': [],
                'firewall_ports': 'N/A',
                'listening_ports_count': 0,
                'blocked_24h': 0,
                'last_blocked': {'ip': 'none', 'port': '0', 'time': 'N/A'},
                'error': str(e)
            }
    
    def get_services_stats(self, ip: str, user: str, password: str, port: int = 22, timeout: int = 30) -> List[Dict]:
        """Получение статистики системных сервисов"""
        try:
            # Используем connection pooling
            client = self.get_connection_pooled(ip, port, user, password)
            services = []
            for descriptor in self._service_catalog:
                services.append(self._probe_service(client, descriptor))
            
            return services
            
        except Exception as e:
            logger.error(f"Error getting services stats from {ip}: {str(e)}")
            return [{'name': 'error', 'status': 'unknown', 'enabled': 'unknown', 'uptime': str(e)}]
    
    def get_security_events(self, ip: str, user: str, password: str, port: int = 22, timeout: int = 30) -> Dict:
        """Получение событий безопасности"""
        import time
        
        try:
            # Используем connection pooling
            client = self.get_connection_pooled(ip, port, user, password)
            
            ssh_failures_output = self._read_command_output(
                client,
                'sudo journalctl --since "24 hours ago" --no-pager 2>/dev/null | grep -E "Failed password|authentication failure" | wc -l',
                timeout=15
            )
            if not ssh_failures_output.isdigit():
                ssh_failures_output = self._read_command_output(
                    client,
                    'sudo grep "Failed password" /var/log/auth.log 2>/dev/null | tail -1000 | wc -l',
                    timeout=15
                )
            ssh_failures = int(ssh_failures_output) if ssh_failures_output.isdigit() else 0

            top_failed_output = self._read_command_output(
                client,
                'sudo journalctl --since "24 hours ago" --no-pager 2>/dev/null | grep -E "Failed password|authentication failure" | grep -oE "from [0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+" | awk \'{print $2}\' | sort | uniq -c | sort -rn | head -3',
                timeout=15
            )
            if not top_failed_output:
                top_failed_output = self._read_command_output(
                    client,
                    'sudo grep "Failed password" /var/log/auth.log 2>/dev/null | tail -1000 | grep -oE "from [0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+" | awk \'{print $2}\' | sort | uniq -c | sort -rn | head -3',
                    timeout=15
                )

            top_ips_output = top_failed_output.split('\n')
            top_failed_ips = []
            for line in top_ips_output:
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        top_failed_ips.append({
                            'ip': parts[1],
                            'count': int(parts[0])
                        })
            
            # Проверяем обновления безопасности
            _, stdout, _ = client.exec_command('apt list --upgradable 2>/dev/null | grep -i security | wc -l')
            security_updates = stdout.read().decode('utf-8').strip()
            security_updates = int(security_updates) if security_updates.isdigit() else 0
            
            # Последнее обновление системы
            _, stdout, _ = client.exec_command('stat -c %Y /var/lib/apt/periodic/update-success-stamp 2>/dev/null')
            last_update_timestamp = stdout.read().decode('utf-8').strip()
            days_since_update = 0
            if last_update_timestamp.isdigit():
                days_since_update = (int(time.time()) - int(last_update_timestamp)) // 86400
            
            fail2ban_output = self._read_command_output(
                client,
                'sudo fail2ban-client status sshd 2>/dev/null | grep "Currently banned:" | awk \'{print $4}\'',
                timeout=10
            )
            fail2ban_banned = int(fail2ban_output) if fail2ban_output.isdigit() else 0

            failed_services_output = self._read_command_output(
                client,
                'systemctl --failed --no-legend --plain 2>/dev/null | wc -l',
                timeout=10
            )
            failed_services = int(failed_services_output) if failed_services_output.isdigit() else 0

            error_events_output = self._read_command_output(
                client,
                'sudo journalctl --since "24 hours ago" -p err..alert --no-pager 2>/dev/null | wc -l',
                timeout=15
            )
            error_events_24h = int(error_events_output) if error_events_output.isdigit() else 0

            # Проверяем новые открытые порты
            baseline_file = '/var/tmp/open_ports_baseline.txt'
            baseline_exists = self._read_command_output(
                client,
                f'test -f {baseline_file} && echo "exists" || echo "not_exists"',
                timeout=10
            ) == 'exists'

            current_ports = self._get_listening_ports(client)
            
            new_open_ports = 0
            if not baseline_exists:
                # Создаем baseline
                ports_str = '\n'.join(current_ports)
                client.exec_command(f'echo "{ports_str}" > {baseline_file}')
            else:
                # Сравниваем с baseline
                _, stdout, _ = client.exec_command(f'cat {baseline_file}')
                baseline_ports = stdout.read().decode('utf-8').strip().split('\n')
                new_ports = set(current_ports) - set(baseline_ports)
                new_open_ports = len(new_ports)
            
            return {
                'ssh_failures_24h': ssh_failures,
                'top_failed_ips': top_failed_ips,
                'security_updates_available': security_updates,
                'days_since_update': days_since_update,
                'new_open_ports': new_open_ports,
                'fail2ban_banned': fail2ban_banned,
                'failed_services': failed_services,
                'error_events_24h': error_events_24h,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error getting security events from {ip}: {str(e)}")
            return {
                'ssh_failures_24h': 0,
                'top_failed_ips': [],
                'security_updates_available': 0,
                'days_since_update': 0,
                'new_open_ports': 0,
                'fail2ban_banned': 0,
                'failed_services': 0,
                'error_events_24h': 0,
                'timestamp': int(time.time()),
                'error': str(e)
            }
    
    def get_metrics_history(self, ip: str, user: str, password: str, port: int = 22, timeout: int = 30) -> List[Dict]:
        """Получение истории метрик CPU/Memory"""
        import time
        
        try:
            # Используем connection pooling
            client = self.get_connection_pooled(ip, port, user, password)
            
            history_file = '/var/tmp/metrics_history.json'
            max_points = 60
            
            # Получаем текущие метрики
            cpu_usage = self._get_cpu_used_pct(client, timeout=timeout)
            
            _, stdout, _ = client.exec_command('free | grep Mem | awk \'{printf "%.1f", $3/$2 * 100}\'')
            mem_usage = stdout.read().decode('utf-8').strip()
            mem_usage = float(mem_usage) if mem_usage else 0.0
            
            timestamp = int(time.time())
            
            # Проверяем, установлен ли jq
            _, stdout, _ = client.exec_command('which jq')
            has_jq = bool(stdout.read().decode('utf-8').strip())
            
            # Читаем существующую историю
            _, stdout, _ = client.exec_command(f'test -f {history_file} && cat {history_file} || echo "[]"')
            history_json = stdout.read().decode('utf-8').strip() or '[]'
            
            if has_jq:
                # Используем jq для обновления истории
                new_point = f'{{"timestamp":{timestamp},"cpu":{cpu_usage},"memory":{mem_usage}}}'
                cmd = f'echo \'{history_json}\' | jq ". += [{new_point}] | .[-{max_points}:]" > {history_file} && cat {history_file}'
                _, stdout, _ = client.exec_command(cmd)
                result = stdout.read().decode('utf-8').strip()
                
                import json
                history = json.loads(result) if result else []
            else:
                # Без jq - используем Python для парсинга
                import json
                try:
                    history = json.loads(history_json) if history_json != '[]' else []
                except:
                    history = []
                
                history.append({
                    'timestamp': timestamp,
                    'cpu': cpu_usage,
                    'memory': mem_usage
                })
                
                # Оставляем только последние max_points точек
                history = history[-max_points:]
                
                # Сохраняем обратно
                history_str = json.dumps(history)
                client.exec_command(f'echo \'{history_str}\' > {history_file}')
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting metrics history from {ip}: {str(e)}")
            # Возвращаем хотя бы текущие данные
            import time
            return [{
                'timestamp': int(time.time()),
                'cpu': 0.0,
                'memory': 0.0,
                'error': str(e)
            }]
    
    def check_required_tools(self, ip: str, user: str, password: str, port: int = 22, timeout: int = 30) -> Dict:
        """Проверка наличия необходимых утилит для мониторинга"""
        
        try:
            # Используем connection pooling
            client = self.get_connection_pooled(ip, port, user, password)
            
            tools = {
                'vnstat': {
                    'name': 'vnstat',
                    'description': 'Статистика сетевого трафика за 24 часа',
                    'install_cmd': 'sudo apt-get install -y vnstat && sudo systemctl enable vnstat && sudo systemctl start vnstat',
                    'category': 'optional',
                    'installed': False
                },
                'jq': {
                    'name': 'jq',
                    'description': 'JSON процессор для графиков истории',
                    'install_cmd': 'sudo apt-get install -y jq',
                    'category': 'optional',
                    'installed': False
                },
                'ufw': {
                    'name': 'ufw',
                    'description': 'Брандмауэр для мониторинга безопасности (НЕ РЕКОМЕНДУЕТСЯ включать)',
                    'install_cmd': 'sudo apt-get install -y ufw',
                    'category': 'optional',
                    'installed': False,
                    'warning': '⚠️ НЕ включайте UFW! Мониторинг работает и без него. Включение UFW без правильной настройки заблокирует SSH доступ!'
                },
                'netstat': {
                    'name': 'netstat',
                    'description': 'Статистика сетевых соединений',
                    'install_cmd': 'sudo apt-get install -y net-tools',
                    'category': 'recommended',
                    'installed': False
                }
            }
            
            # Проверяем каждую утилиту
            for tool_key, tool_info in tools.items():
                _, stdout, _ = client.exec_command(f'which {tool_info["name"]}')
                tool_path = stdout.read().decode('utf-8').strip()
                tools[tool_key]['installed'] = bool(tool_path)
                if tool_path:
                    tools[tool_key]['path'] = tool_path
            
            # Проверяем, запущен ли vnstat
            if tools['vnstat']['installed']:
                _, stdout, _ = client.exec_command('systemctl is-active vnstat 2>/dev/null')
                vnstat_status = stdout.read().decode('utf-8').strip()
                tools['vnstat']['running'] = vnstat_status == 'active'
                if vnstat_status != 'active':
                    tools['vnstat']['warning'] = 'Установлен, но не запущен'
                    tools['vnstat']['fix_cmd'] = 'sudo systemctl enable vnstat && sudo systemctl start vnstat'
            
            # Проверяем, включен ли UFW
            if tools['ufw']['installed']:
                _, stdout, _ = client.exec_command('sudo ufw status 2>/dev/null | grep "Status:" | awk \'{print $2}\'')
                ufw_status = stdout.read().decode('utf-8').strip()
                tools['ufw']['enabled'] = ufw_status.lower() == 'active'
                if ufw_status.lower() != 'active':
                    tools['ufw']['warning'] = '⚠️ UFW выключен (это ПРАВИЛЬНО! Оставьте выключенным)'
                    tools['ufw']['fix_cmd'] = '# НЕ включайте UFW! Команда: sudo ufw disable'
                else:
                    tools['ufw']['warning'] = f'⚠️ UFW включен! Убедитесь что SSH-порт {port} разрешен!'
                    tools['ufw']['fix_cmd'] = f'sudo ufw allow {port}/tcp && sudo ufw status numbered'
            
            # Подсчитываем статистику
            total = len(tools)
            installed = sum(1 for t in tools.values() if t['installed'])
            missing = [t for t in tools.values() if not t['installed']]
            warnings = [t for t in tools.values() if t.get('warning')]
            
            # Генерируем команду для установки всех недостающих
            if missing:
                install_all_cmd = 'sudo apt-get update && ' + ' && '.join([t['install_cmd'] for t in missing])
            else:
                install_all_cmd = None
            
            return {
                'total': total,
                'installed': installed,
                'missing_count': len(missing),
                'tools': tools,
                'missing': missing,
                'warnings': warnings,
                'install_all_cmd': install_all_cmd,
                'all_ok': installed == total and not warnings
            }
            
        except Exception as e:
            logger.error(f"Error checking tools on {ip}: {str(e)}")
            return {
                'total': 0,
                'installed': 0,
                'missing_count': 0,
                'tools': {},
                'missing': [],
                'warnings': [],
                'install_all_cmd': None,
                'all_ok': False,
                'error': str(e)
            }