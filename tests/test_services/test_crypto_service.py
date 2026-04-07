import pytest
import tempfile
import os
from app.services.crypto_service import CryptoService
from app.exceptions import CryptoError

class TestCryptoService:
    """Тесты для CryptoService"""
    
    def test_generate_key(self):
        """Тест генерации ключа"""
        key = CryptoService.generate_key()
        assert isinstance(key, bytes)
        assert len(key) > 0
    
    def test_generate_key_from_password(self):
        """Тест генерации ключа из пароля"""
        password = "test_password_123"
        key = CryptoService.generate_key_from_password(password)
        assert isinstance(key, bytes)
        assert len(key) > 0
        
        # Тест с солью
        salt = os.urandom(16)
        key_with_salt = CryptoService.generate_key_from_password(password, salt)
        assert isinstance(key_with_salt, bytes)
        assert len(key_with_salt) > 0
        assert key != key_with_salt  # Ключи должны быть разными
    
    def test_encrypt_decrypt(self):
        """Тест шифрования и дешифрования"""
        key = CryptoService.generate_key()
        original_data = "This is a test message with special chars: !@#$%^&*()"
        
        # Шифрование
        encrypted = CryptoService.encrypt(original_data, key)
        assert isinstance(encrypted, str)
        assert encrypted != original_data
        
        # Дешифрование
        decrypted = CryptoService.decrypt(encrypted, key)
        assert decrypted == original_data
    
    def test_encrypt_decrypt_with_invalid_key(self):
        """Тест с неверным ключом"""
        key1 = CryptoService.generate_key()
        key2 = CryptoService.generate_key()
        original_data = "Test message"
        
        encrypted = CryptoService.encrypt(original_data, key1)
        
        # Попытка дешифровать с другим ключом
        with pytest.raises(CryptoError):
            CryptoService.decrypt(encrypted, key2)
    
    def test_encrypt_decrypt_file(self):
        """Тест шифрования и дешифрования файла"""
        key = CryptoService.generate_key()
        original_content = "This is test file content with unicode: привет мир!"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(original_content)
            original_file = f.name
        
        try:
            # Шифрование файла
            encrypted_file = CryptoService.encrypt_file(original_file, key)
            assert os.path.exists(encrypted_file)
            assert encrypted_file != original_file
            
            # Дешифрование файла
            decrypted_file = CryptoService.decrypt_file(encrypted_file, key)
            assert os.path.exists(decrypted_file)
            
            # Проверка содержимого
            with open(decrypted_file, 'r', encoding='utf-8') as f:
                decrypted_content = f.read()
            assert decrypted_content == original_content
            
        finally:
            # Очистка временных файлов
            for file_path in [original_file, encrypted_file, decrypted_file]:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    def test_save_load_key(self):
        """Тест сохранения и загрузки ключа"""
        key = CryptoService.generate_key()
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            key_file = f.name
        
        try:
            # Сохранение ключа
            CryptoService.save_key_to_file(key, key_file)
            assert os.path.exists(key_file)
            
            # Загрузка ключа
            loaded_key = CryptoService.load_key_from_file(key_file)
            assert loaded_key == key
            
        finally:
            if os.path.exists(key_file):
                os.unlink(key_file)
    
    def test_load_nonexistent_key(self):
        """Тест загрузки несуществующего ключа"""
        with pytest.raises(CryptoError):
            CryptoService.load_key_from_file("nonexistent_key_file")
    
    def test_validate_key(self):
        """Тест валидации ключа"""
        # Валидный ключ
        valid_key = CryptoService.generate_key()
        assert CryptoService.validate_key(valid_key) is True
        
        # Невалидный ключ
        invalid_key = b"invalid_key"
        assert CryptoService.validate_key(invalid_key) is False
        
        # Пустой ключ
        assert CryptoService.validate_key(b"") is False
    
    def test_encrypt_empty_string(self):
        """Тест шифрования пустой строки"""
        key = CryptoService.generate_key()
        encrypted = CryptoService.encrypt("", key)
        decrypted = CryptoService.decrypt(encrypted, key)
        assert decrypted == ""
    
    def test_encrypt_large_data(self):
        """Тест шифрования больших данных"""
        key = CryptoService.generate_key()
        large_data = "A" * 10000  # 10KB данных
        
        encrypted = CryptoService.encrypt(large_data, key)
        decrypted = CryptoService.decrypt(encrypted, key)
        assert decrypted == large_data
