#!/usr/bin/env python3
"""
Generate SECRET_KEY for VPN Server Manager
"""

from cryptography.fernet import Fernet
import os

def generate_key():
    """Generate and save SECRET_KEY to .env file"""
    key = Fernet.generate_key()
    
    with open('.env', 'w') as f:
        f.write(f'SECRET_KEY={key.decode()}')
    
    print("Key successfully generated and saved in .env file.")
    print("IMPORTANT: If you overwrote an existing key, restart the server and recreate password records.")

if __name__ == "__main__":
    generate_key() 