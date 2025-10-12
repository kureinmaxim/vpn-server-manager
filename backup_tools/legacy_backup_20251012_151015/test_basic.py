#!/usr/bin/env python3
"""
Basic tests for VPN Server Manager v4.0.3 with new modular architecture
"""

import os
import sys
import json
from pathlib import Path

def test_config():
    """Test configuration"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        assert 'app_info' in config
        assert 'service_urls' in config
        assert 'secret_pin' in config
        print("OK: Configuration loads correctly")
        return True
    except Exception as e:
        print(f"ERROR: Configuration error: {e}")
        return False

def test_imports():
    """Test module imports"""
    try:
        # Test new modular architecture
        from app import create_app
        print("OK: app module imports successfully")
        
        from app.services import registry
        print("OK: services module imports successfully")
        
        from app.routes import main_bp, api_bp
        print("OK: routes module imports successfully")
        
        from app.models.server import Server
        print("OK: models module imports successfully")
        
        from app.utils.validators import Validators
        print("OK: utils module imports successfully")
        
        from desktop.window import DesktopApp
        print("OK: desktop module imports successfully")
        
        # Test legacy modules (if they exist)
        try:
            import pin_auth
            print("OK: pin_auth.py imports successfully (legacy)")
        except ImportError:
            print("INFO: pin_auth.py not found (expected in new architecture)")
        
        import decrypt_tool
        print("OK: decrypt_tool.py imports successfully")
        
        import build_macos
        print("OK: build_macos.py imports successfully")
        
        return True
    except Exception as e:
        print(f"ERROR: Import error: {e}")
        return False

def test_files():
    """Test required files presence"""
    required_files = [
        'run.py',                    # New entry point
        'config.json',               # Legacy config
        'requirements.txt',
        'README.md',
        'CHANGELOG.md',
        'LICENSE',
        '.gitignore',
        'static/images/icon.png',
        'templates/index.html',
        'data/hints.json',
        'app/__init__.py',           # New app structure
        'app/config.py',
        'app/exceptions.py',
        'app/services/__init__.py',
        'app/routes/__init__.py',
        'app/models/__init__.py',
        'app/utils/__init__.py',
        'desktop/__init__.py',       # Desktop layer
        'desktop/window.py',
        'tests/__init__.py',         # Tests
        'tests/conftest.py',
        'env.example',               # Environment example
        'setup.py',                  # Package setup
        'Makefile',                  # Development tools
        'Dockerfile',                # Containerization
        'docker-compose.yml',
        'pytest.ini'                 # Test configuration
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"ERROR: Missing files: {missing_files}")
        return False
    else:
        print("OK: All required files present")
        return True

def test_env():
    """Test environment variables"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        secret_key = os.environ.get('SECRET_KEY')
        if secret_key:
            print("OK: SECRET_KEY found")
            return True
        else:
            print("WARNING: SECRET_KEY not found (but this is normal for CI)")
            return True
    except Exception as e:
        print(f"ERROR: Environment error: {e}")
        return False

def test_new_architecture():
    """Test new modular architecture"""
    try:
        # Test Application Factory
        from app import create_app
        app = create_app('testing')
        print("OK: Application Factory works")
        
        # Test Service Registry
        from app.services import registry
        from app.services.ssh_service import SSHService
        from app.services.crypto_service import CryptoService
        from app.services.api_service import APIService
        
        registry.register('ssh', SSHService())
        registry.register('crypto', CryptoService())
        registry.register('api', APIService())
        
        ssh_service = registry.get('ssh')
        crypto_service = registry.get('crypto')
        api_service = registry.get('api')
        
        assert ssh_service is not None
        assert crypto_service is not None
        assert api_service is not None
        
        print("OK: Service Registry works")
        
        # Test Models
        from app.models.server import Server
        server = Server(
            id='test-1',
            name='Test Server',
            hostname='192.168.1.1',
            username='testuser'
        )
        assert server.is_valid()
        print("OK: Models work")
        
        # Test Validators
        from app.utils.validators import Validators
        assert Validators.validate_ip_address('192.168.1.1')
        assert not Validators.validate_ip_address('invalid-ip')
        print("OK: Validators work")
        
        return True
    except Exception as e:
        print(f"ERROR: New architecture test failed: {e}")
        return False

def main():
    """Main testing function"""
    print("Running basic tests for VPN Server Manager v4.0.0...")
    print("=" * 60)
    
    tests = [
        test_files,
        test_config,
        test_imports,
        test_env,
        test_new_architecture
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All tests passed successfully!")
        return 0
    else:
        print("FAILED: Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 