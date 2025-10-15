#!/usr/bin/env python3
"""
Точка входа для VPN Server Manager - Clean
Поддерживает как web, так и desktop режимы
"""

import sys
import os
import logging
import socket
import atexit

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Graceful shutdown для SSH подключений
@atexit.register
def cleanup():
    """Очистка ресурсов при остановке приложения"""
    logger = logging.getLogger(__name__)
    logger.info("[CLEANUP] Cleaning up SSH connections...")
    try:
        from app.services.ssh_service import SSHService
        SSHService.close_all()
        logger.info("[OK] SSH connections closed")
    except Exception as e:
        logger.warning(f"[WARNING] Error during cleanup: {e}")

def find_free_port(start_port=5000, max_attempts=100):
    """Находит свободный порт, начиная с start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + max_attempts}")

def setup_basic_logging():
    """Базовая настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """Главная функция"""
    setup_basic_logging()
    logger = logging.getLogger(__name__)
    
    try:
        if '--desktop' in sys.argv:
            # Desktop режим
            logger.info("Starting in desktop mode")
            from desktop.window import DesktopApp
            
            config_name = 'development' if '--debug' in sys.argv else 'production'
            app = DesktopApp(config_name)
            app.start()
            
        else:
            # Web режим
            logger.info("Starting in web mode")
            from app import create_app
            
            config_name = 'development' if '--debug' in sys.argv else 'production'
            app = create_app(config_name)
            
            # Настройки для web режима
            host = '127.0.0.1'
            preferred_port = int(os.getenv('PORT', 5000))
            debug = config_name == 'development'
            
            # Поиск свободного порта
            try:
                port = find_free_port(preferred_port)
                if port != preferred_port:
                    logger.info(f"Port {preferred_port} is busy, using port {port}")
                else:
                    logger.info(f"Using preferred port {port}")
            except RuntimeError as e:
                logger.error(f"Could not find free port: {e}")
                sys.exit(1)
            
            # Получаем версию из конфигурации приложения
            version = app.config.get('app_info', {}).get('version', 'N/A')
            
            logger.info(f"Starting web server on {host}:{port}")
            print(f"\n[INFO] VPN Server Manager v{version}")
            print(f"[WEB] Web server: http://{host}:{port}")
            print(f"[MODE] Mode: {'Development' if debug else 'Production'}")
            print(f"[INFO] Press Ctrl+C to stop\n")
            
            # threaded=True позволяет обрабатывать несколько запросов одновременно
            # Это критично важно для SSH операций с долгими таймаутами
            app.run(host=host, port=port, debug=debug, threaded=True)
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
