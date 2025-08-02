# Active Context: VPN Server Manager Project

## Current Task Status: No Active Tasks - Ready for New Development

## Project Overview
VPN Server Manager - десктопное приложение для управления VPN-серверами с гибридной архитектурой (Flask + PyWebView).

## Recent Achievement (v3.3.4)
Успешно исправлена критическая проблема с управлением ключами шифрования:
- ✅ Исправлена ошибка "Read-only file system" при смене ключей в упакованном .app
- ✅ Оптимизированы зависимости (удален ненужный Qt) 
- ✅ Очищена структура проекта
- ✅ Полностью восстановлена функциональность управления ключами

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
1. Build and test new v3.3.4 distribution with key management fixes
2. Consider implementing automated tests for key management functionality  
3. Monitor user feedback on improved key management experience
4. Plan next feature development cycle

## Memory Bank Status
- **Current Tasks**: None (ready for new task)
- **Last Archive**: .env File Write Error & Dependency Cleanup v3.3.4 (16.01.2025)
- **Ready for**: VAN Mode to initialize next task
