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
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    @property
    def is_connected(self) -> bool:
        """Проверка состояния соединения"""
        return self.client is not None and self.client.get_transport() is not None
