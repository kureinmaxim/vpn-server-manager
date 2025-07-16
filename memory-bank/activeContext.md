# Active Context: VPN Server Manager Project

## Current Task Status: Decryption Fix v3.2.6 - COMPLETED & ARCHIVED

## Project Overview
VPN Server Manager - десктопное приложение для управления VPN-серверами с гибридной архитектурой (Flask + PyWebView).

## Recent Achievement
Успешно исправлена критическая проблема расшифровки данных серверов. Все 4 сервера теперь корректно отображают учетные данные вместо зашифрованных строк. Созданы новые дистрибутивы v3.2.6 для продакшн использования.

## Key Technologies
- **Frontend**: HTML/CSS/JavaScript + Jinja2 templates
- **Backend**: Flask web framework  
- **GUI**: PyWebView for native desktop window
- **Security**: Cryptography library (Fernet encryption)
- **Data**: JSON with AES encryption
- **Threading**: Multi-threaded architecture
- **Platform**: Cross-platform (macOS/Windows/Linux)

## Architecture Pattern
Hybrid Desktop Application:
```
PyWebView (Native Window) -> Flask (Local Server) -> HTML Interface
                          -> Python Backend Logic
                          -> Encrypted JSON Storage
```

## Project Structure
- Main application: `app.py`
- Templates: `templates/` directory
- Static assets: `static/` directory  
- Educational content: `TEACHING_GUIDE.md` + `lessons/` directory
- Build system: `build_macos.py`
- Configuration: `config.json`

## Next Recommended Actions
1. Monitor user feedback on the new v3.2.6 distribution
2. Consider implementing automated tests for decryption functionality
3. Review potential security enhancements for encryption key management
4. Plan next feature development cycle

## Memory Bank Status
- **Current Tasks**: None (ready for new task)
- **Last Archive**: VPN Server Data Decryption Fix v3.2.6 (15.07.2025)
- **Ready for**: VAN Mode to initialize next task
