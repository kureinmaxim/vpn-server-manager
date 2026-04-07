from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import logging
from typing import Optional
from ..exceptions import CryptoError

logger = logging.getLogger(__name__)

class CryptoService:
    """Сервис для криптографических операций"""
    
    @staticmethod
    def generate_key() -> bytes:
        """Генерация ключа шифрования"""
        try:
            key = Fernet.generate_key()
            logger.info("Generated new encryption key")
            return key
        except Exception as e:
            logger.error(f"Error generating key: {str(e)}")
            raise CryptoError(f"Key generation failed: {str(e)}")
    
    @staticmethod
    def generate_key_from_password(password: str, salt: Optional[bytes] = None) -> bytes:
        """Генерация ключа из пароля"""
        try:
            if salt is None:
                salt = os.urandom(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            logger.info("Generated key from password")
            return key
        except Exception as e:
            logger.error(f"Error generating key from password: {str(e)}")
            raise CryptoError(f"Key generation from password failed: {str(e)}")
    
    @staticmethod
    def encrypt(data: str, key: bytes) -> str:
        """Шифрование данных"""
        try:
            f = Fernet(key)
            encrypted = f.encrypt(data.encode())
            result = base64.b64encode(encrypted).decode()
            logger.info("Data encrypted successfully")
            return result
        except InvalidToken as e:
            logger.error(f"Invalid key for encryption: {str(e)}")
            raise CryptoError(f"Invalid encryption key: {str(e)}")
        except Exception as e:
            logger.error(f"Error encrypting data: {str(e)}")
            raise CryptoError(f"Encryption failed: {str(e)}")
    
    @staticmethod
    def decrypt(encrypted_data: str, key: bytes) -> str:
        """Дешифрование данных"""
        try:
            f = Fernet(key)
            encrypted_bytes = base64.b64decode(encrypted_data)
            decrypted = f.decrypt(encrypted_bytes)
            result = decrypted.decode()
            logger.info("Data decrypted successfully")
            return result
        except InvalidToken as e:
            logger.error(f"Invalid key or corrupted data: {str(e)}")
            raise CryptoError(f"Decryption failed - invalid key or corrupted data: {str(e)}")
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            raise CryptoError(f"Decryption failed: {str(e)}")
    
    @staticmethod
    def encrypt_file(file_path: str, key: bytes, output_path: Optional[str] = None) -> str:
        """Шифрование файла"""
        try:
            if output_path is None:
                output_path = file_path + '.enc'
            
            with open(file_path, 'rb') as f:
                data = f.read()
            
            f = Fernet(key)
            encrypted = f.encrypt(data)
            
            with open(output_path, 'wb') as f:
                f.write(encrypted)
            
            logger.info(f"File encrypted: {file_path} -> {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error encrypting file {file_path}: {str(e)}")
            raise CryptoError(f"File encryption failed: {str(e)}")
    
    @staticmethod
    def decrypt_file(encrypted_file_path: str, key: bytes, output_path: Optional[str] = None) -> str:
        """Дешифрование файла"""
        try:
            if output_path is None:
                if encrypted_file_path.endswith('.enc'):
                    output_path = encrypted_file_path[:-4]
                else:
                    output_path = encrypted_file_path + '.dec'
            
            with open(encrypted_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_data)
            
            with open(output_path, 'wb') as f:
                f.write(decrypted)
            
            logger.info(f"File decrypted: {encrypted_file_path} -> {output_path}")
            return output_path
        except InvalidToken as e:
            logger.error(f"Invalid key for file decryption: {str(e)}")
            raise CryptoError(f"File decryption failed - invalid key: {str(e)}")
        except Exception as e:
            logger.error(f"Error decrypting file {encrypted_file_path}: {str(e)}")
            raise CryptoError(f"File decryption failed: {str(e)}")
    
    @staticmethod
    def save_key_to_file(key: bytes, file_path: str) -> None:
        """Сохранение ключа в файл"""
        try:
            with open(file_path, 'wb') as f:
                f.write(key)
            logger.info(f"Key saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving key to {file_path}: {str(e)}")
            raise CryptoError(f"Key save failed: {str(e)}")
    
    @staticmethod
    def load_key_from_file(file_path: str) -> bytes:
        """Загрузка ключа из файла"""
        try:
            with open(file_path, 'rb') as f:
                key = f.read()
            logger.info(f"Key loaded from {file_path}")
            return key
        except FileNotFoundError:
            logger.error(f"Key file not found: {file_path}")
            raise CryptoError(f"Key file not found: {file_path}")
        except Exception as e:
            logger.error(f"Error loading key from {file_path}: {str(e)}")
            raise CryptoError(f"Key load failed: {str(e)}")
    
    @staticmethod
    def validate_key(key: bytes) -> bool:
        """Валидация ключа"""
        try:
            Fernet(key)
            return True
        except Exception:
            return False
