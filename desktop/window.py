import webview
import threading
import logging
import sys
import os
from app import create_app

logger = logging.getLogger(__name__)

class DesktopApp:
    """Desktop приложение с pywebview"""
    
    def __init__(self, config_name='production'):
        self.config_name = config_name
        self.app = None
        self.window = None
        self.server_thread = None
        
    def create_flask_app(self):
        """Создание Flask приложения"""
        try:
            self.app = create_app(self.config_name)
            logger.info("Flask app created successfully")
            return self.app
        except Exception as e:
            logger.error(f"Error creating Flask app: {str(e)}")
            raise
    
    def start_flask_server(self):
        """Запуск Flask сервера в отдельном потоке"""
        try:
            if self.app:
                self.app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Error starting Flask server: {str(e)}")
    
    def start(self):
        """Запуск desktop приложения"""
        try:
            # Создаем Flask приложение
            self.create_flask_app()
            
            # Запускаем Flask сервер в отдельном потоке
            self.server_thread = threading.Thread(target=self.start_flask_server, daemon=True)
            self.server_thread.start()
            
            # Ждем немного, чтобы сервер запустился
            import time
            time.sleep(1)
            
            # Создаем окно pywebview
            self.window = webview.create_window(
                'VPN Server Manager - Clean',
                'http://127.0.0.1:5000',
                width=1200,
                height=800,
                resizable=True,
                min_size=(800, 600),
                shadow=True,
                on_top=False,
                text_select=True
            )
            
            # Настройки окна
            webview.start(
                debug=False,
                http_server=False,
                private_mode=False
            )
            
        except Exception as e:
            logger.error(f"Error starting desktop app: {str(e)}")
            raise
    
    def stop(self):
        """Остановка desktop приложения"""
        try:
            if self.window:
                webview.destroy_window(self.window)
            logger.info("Desktop app stopped")
        except Exception as e:
            logger.error(f"Error stopping desktop app: {str(e)}")

def main():
    """Главная функция для запуска desktop приложения"""
    try:
        # Определяем конфигурацию
        config_name = 'development' if '--debug' in sys.argv else 'production'
        
        # Создаем и запускаем приложение
        app = DesktopApp(config_name)
        app.start()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
