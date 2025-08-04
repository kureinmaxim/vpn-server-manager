#!/usr/bin/env python3
"""
Basic tests for VPN Server Manager without GUI
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
        print("✅ Configuration loads correctly")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_imports():
    """Test module imports"""
    try:
        import app
        print("✅ app.py imports successfully")
        
        import pin_auth
        print("✅ pin_auth.py imports successfully")
        
        import decrypt_tool
        print("✅ decrypt_tool.py imports successfully")
        
        import build_macos
        print("✅ build_macos.py imports successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_files():
    """Test required files presence"""
    required_files = [
        'app.py',
        'config.json',
        'requirements.txt',
        'README.md',
        'CHANGELOG.md',
        'LICENSE',
        '.gitignore',
        'static/images/icon.png',
        'templates/index.html',
        'data/hints.json'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_env():
    """Test environment variables"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        secret_key = os.environ.get('SECRET_KEY')
        if secret_key:
            print("✅ SECRET_KEY found")
            return True
        else:
            print("⚠️ SECRET_KEY not found (but this is normal for CI)")
            return True
    except Exception as e:
        print(f"❌ Environment error: {e}")
        return False

def main():
    """Main testing function"""
    print("🧪 Running basic tests for VPN Server Manager...")
    print("=" * 50)
    
    tests = [
        test_files,
        test_config,
        test_imports,
        test_env
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed successfully!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 