import paramiko
from typing import Optional, Dict, List
from paramiko.ssh_exception import SSHException, AuthenticationException
from ..exceptions import SSHConnectionError, AuthenticationError
import logging

logger = logging.getLogger(__name__)

class SSHService:
    """Сервис для работы с SSH/SFTP"""
    
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp_client: Optional[paramiko.SFTPClient] = None
    
    def connect(self, hostname: str, username: str, 
                password: Optional[str] = None,
                key_filename: Optional[str] = None,
                port: int = 22,
                timeout: int = 10) -> None:
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
                timeout=timeout
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
        client = None
        
        try:
            # Создаем новый SSH клиент для этого запроса
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info(f"Connecting to {ip}:{port} for stats collection")
            client.connect(
                hostname=ip,
                username=user,
                password=password,
                port=port,
                timeout=timeout
            )
            
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
                
                _, stdout, _ = client.exec_command('top -bn1 | grep "Cpu(s)" | sed "s/.*, *\\([0-9.]*\\)%* id.*/\\1/" | awk \'{print 100 - $1}\'')
                cpu_used = stdout.read().decode('utf-8').strip()
                
                _, stdout, _ = client.exec_command('uname -r')
                kernel = stdout.read().decode('utf-8').strip()
                
                stats['cpu'] = {
                    'cores': int(cores) if cores else 0,
                    'used_pct': float(cpu_used) if cpu_used else 0.0,
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
                _, stdout, _ = client.exec_command('ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 6')
                ps_lines = stdout.read().decode('utf-8').strip().split('\n')
                processes = []
                for line in ps_lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            processes.append({
                                'pid': parts[0],
                                'cmd': parts[1],
                                'cpu': parts[2],
                                'mem': parts[3]
                            })
                stats['processes'] = processes
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
                raise SSHConnectionError(f"Server {ip} is not responding or SSH service is not running. Please check if the server is online and SSH port (22) is accessible.")
            else:
                raise SSHConnectionError(f"SSH connection failed to {ip}: {str(e)}")
        except paramiko.socket.timeout as e:
            logger.error(f"SSH connection timeout to {ip}: {str(e)}")
            raise SSHConnectionError(f"Connection timeout to {ip}. Server may be slow or unreachable.")
        except Exception as e:
            logger.error(f"Error collecting stats from {ip}: {str(e)}")
            raise SSHConnectionError(f"Failed to collect stats from {ip}: {str(e)}")
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    @property
    def is_connected(self) -> bool:
        """Проверка состояния соединения"""
        return self.client is not None and self.client.get_transport() is not None
