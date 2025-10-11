#!/usr/bin/env python3
"""
Generate SECRET_KEY for VPN Server Manager v4.0.0
"""

from cryptography.fernet import Fernet
import os

def generate_key():
    """Generate and save SECRET_KEY to .env file"""
    key = Fernet.generate_key()
    
    with open('.env', 'w') as f:
        f.write(f'SECRET_KEY={key.decode()}')
    
    print("Key successfully generated and saved in .env file.")
    print("IMPORTANT: If you overwrote an existing key, restart the application and recreate password records.")
    print("For v4.0.0: Use 'python run.py' to start the application.")

if __name__ == "__main__":
    generate_key() 