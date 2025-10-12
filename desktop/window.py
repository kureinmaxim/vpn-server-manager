import webview
import threading
import logging
import sys
import os
import signal
import time
from wsgiref.simple_server import make_server
from app import create_app

logger = logging.getLogger(__name__)

# Глобальные переменные для управления сервером
SERVER_PORT = None
_WSGI_SERVER = None

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
        """Запуск Flask сервера в отдельном потоке с динамическим портом"""
        global SERVER_PORT, _WSGI_SERVER
        
        try:
            if self.app:
                # Используем порт 0 для автоматического выделения свободного порта ОС
                _WSGI_SERVER = make_server('127.0.0.1', 0, self.app)
                SERVER_PORT = _WSGI_SERVER.server_port
                
                logger.info(f"🚀 Flask сервер запущен на http://127.0.0.1:{SERVER_PORT}")
                print(f"🚀 Flask сервер запущен на http://127.0.0.1:{SERVER_PORT}")
                
                _WSGI_SERVER.serve_forever()
        except Exception as e:
            logger.error(f"Error starting Flask server: {str(e)}")
    
    def start(self):
        """Запуск desktop приложения"""
        global SERVER_PORT
        
        try:
            # Создаем Flask приложение
            self.create_flask_app()
            
            # Запускаем Flask сервер в отдельном потоке
            self.server_thread = threading.Thread(target=self.start_flask_server, daemon=True)
            self.server_thread.start()
            
            # Ожидание инициализации сервера (до 5 секунд)
            for _ in range(100):
                if SERVER_PORT:
                    break
                time.sleep(0.05)
            
            if not SERVER_PORT:
                raise RuntimeError("Failed to start Flask server: SERVER_PORT not initialized")
            
            logger.info(f"Server initialized on port {SERVER_PORT}")
            
            # Создаем окно pywebview с динамическим URL
            logger.info(f"Creating pywebview window for http://127.0.0.1:{SERVER_PORT}")
            print(f"🪟 Creating pywebview window for http://127.0.0.1:{SERVER_PORT}")
            
            self.window = webview.create_window(
                'VPN Server Manager - Clean',
                f'http://127.0.0.1:{SERVER_PORT}',
                width=1200,
                height=880,  # Увеличено на 10% (800 * 1.1 = 880)
                resizable=True,
                min_size=(800, 600),
                shadow=True,
                on_top=False,
                text_select=True,
                confirm_close=False  # Отключаем нативный диалог, используем свой JavaScript
            )
            
            # Обработчик закрытия окна
            self.window.events.closing += self.on_closing
            
            logger.info("Starting pywebview...")
            print("🚀 Starting pywebview...")
            
            # Настройки окна
            webview.start(
                debug=False,
                http_server=False,
                private_mode=True,  # Приватный режим - не сохраняет сессии между запусками
                gui='cocoa'  # Явно указываем Cocoa для macOS
            )
            
            logger.info("PyWebView closed")
            print("✅ PyWebview closed")
            
        except Exception as e:
            logger.error(f"Error starting desktop app: {str(e)}")
            raise
    
    def on_closing(self):
        """Обработчик закрытия окна с подтверждением"""
        global SERVER_PORT, _WSGI_SERVER
        
        # Проверяем статус аутентификации через Flask endpoint
        try:
            if self.window and SERVER_PORT:
                import requests
                try:
                    # Проверяем, аутентифицирован ли пользователь
                    check_url = f'http://127.0.0.1:{SERVER_PORT}/pin/check_auth'
                    response = requests.get(check_url, timeout=1)
                    if response.ok:
                        data = response.json()
                        if data.get('authenticated'):
                            # Показываем диалог подтверждения
                            result = self.window.evaluate_js(
                                "confirm('Вы уверены, что хотите закрыть приложение?')"
                            )
                            if not result:
                                logger.info("User cancelled window closing")
                                return False  # Отменяем закрытие
                    # Если не аутентифицирован или ошибка - закрываем без вопросов
                except Exception as e:
                    logger.warning(f"Could not check auth status: {e}")
                    # Если ошибка проверки - закрываем без вопросов
        except Exception as e:
            logger.warning(f"Could not show confirmation dialog: {e}")
        
        logger.info("Окно закрывается, отправка запроса на выключение...")
        print("Окно закрывается, отправка запроса на выключение...")
        
        try:
            if SERVER_PORT:
                import requests
                # Выполняем выход из системы для сброса сессии
                try:
                    logout_url = f'http://127.0.0.1:{SERVER_PORT}/pin/logout'
                    requests.post(logout_url, timeout=2)
                    logger.info("Logout request sent to clear session.")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Could not send logout request: {e}")

            if _WSGI_SERVER:
                # Останавливаем WSGI сервер
                shutdown_thread = threading.Thread(target=_WSGI_SERVER.shutdown)
                shutdown_thread.start()
                logger.info("WSGI server shutdown initiated.")
        except Exception as e:
            logger.error(f"Error in on_closing: {str(e)}")
        
        return True  # Разрешаем закрытие
    
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
