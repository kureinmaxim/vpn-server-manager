#!/usr/bin/env python3
"""
Generate SECRET_KEY for VPN Server Manager v4.0.5
"""

from cryptography.fernet import Fernet
import os
import shutil

def generate_key():
    """Generate and save SECRET_KEY to .env file"""
    key = Fernet.generate_key()
    env_file = '.env'
    env_example = 'env.example'
    
    # Если .env не существует, копируем из env.example
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            shutil.copy(env_example, env_file)
            print(f"Created {env_file} from {env_example}")
        else:
            print(f"Warning: {env_example} not found. Creating new {env_file}")
    
    # Читаем существующий .env
    lines = []
    key_updated = False
    
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Обновляем строку SECRET_KEY
        for i, line in enumerate(lines):
            if line.strip().startswith('SECRET_KEY='):
                lines[i] = f'SECRET_KEY={key.decode()}\n'
                key_updated = True
                break
    
    # Если SECRET_KEY не найден, добавляем в начало
    if not key_updated:
        lines.insert(0, f'SECRET_KEY={key.decode()}\n')
    
    # Записываем обновленный файл
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✅ Key successfully generated and saved in .env file.")
    print("⚠️  IMPORTANT: If you overwrote an existing key, restart the application and recreate password records.")
    print("🚀 To start the application, use: python run.py")

if __name__ == "__main__":
    generate_key() 