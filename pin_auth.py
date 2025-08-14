import json
import os
import time
from datetime import datetime, timedelta
from flask import session, redirect, url_for
from flask_babel import gettext

class PinAuth:
    def __init__(self, config_file=None):
        # Определяем путь к config.json
        if config_file is None:
            # Используем тот же путь, что и в app.py
            import sys
            import os
            from pathlib import Path
            
            # Определяем, запущено ли приложение как пакет
            is_frozen = getattr(sys, 'frozen', False)
            
            # Имя директории приложения
            app_name = "VPNServerManager-Clean"
            
            if is_frozen:  # Приложение запущено как .app или .exe
                if sys.platform == 'darwin':  # macOS
                    app_data_dir = os.path.join(
                        os.path.expanduser("~"), 
                        "Library", "Application Support", 
                        app_name
                    )
                elif sys.platform == 'win32':  # Windows
                    app_data_dir = os.path.join(
                        os.environ.get('APPDATA', os.path.expanduser("~")),
                        app_name
                    )
                else:  # Linux и другие системы
                    app_data_dir = os.path.join(
                        os.path.expanduser("~"),
                        ".local", "share",
                        app_name
                    )
            else:
                # В режиме разработки используем локальные пути
                app_data_dir = os.path.join(os.getcwd())
            
            self.config_file = os.path.join(app_data_dir, 'config.json')
        else:
            self.config_file = config_file
            
        self.pin_attempts = 0
        self.pin_blocked_until = None
        self.pin_block_duration = 30  # секунд
        
        # Файл для хранения состояния блокировки
        self.block_state_file = os.path.join(os.path.dirname(self.config_file), 'pin_block_state.json')
        
        # Загружаем состояние блокировки при инициализации
        self._load_block_state()
    
    def _load_block_state(self):
        """Загружает состояние блокировки из файла."""
        try:
            if os.path.exists(self.block_state_file):
                with open(self.block_state_file, 'r') as f:
                    state = json.load(f)
                    blocked_until = state.get('blocked_until')
                    attempts = state.get('attempts', 0)
                    
                    # Проверяем, не истекла ли блокировка
                    if blocked_until:
                        blocked_until_time = datetime.fromisoformat(blocked_until)
                        if datetime.now() < blocked_until_time:
                            self.pin_blocked_until = blocked_until_time
                            print(f"🔒 Загружена активная блокировка до {blocked_until_time}")
                        else:
                            # Блокировка истекла, сбрасываем счетчик
                            self.pin_attempts = 0
                            self._save_block_state()
                            print("🔓 Загруженная блокировка уже истекла, сброс")
                    else:
                        self.pin_attempts = attempts
                        print(f"🔢 Загружено количество попыток: {attempts}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки состояния блокировки: {e}")
    
    def _save_block_state(self):
        """Сохраняет состояние блокировки в файл."""
        try:
            state = {
                'attempts': self.pin_attempts,
                'blocked_until': self.pin_blocked_until.isoformat() if self.pin_blocked_until else None
            }
            
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(self.block_state_file), exist_ok=True)
            
            with open(self.block_state_file, 'w') as f:
                json.dump(state, f)
                
            print(f"💾 Сохранено состояние блокировки: попытки={self.pin_attempts}, блокировка до={self.pin_blocked_until}")
        except Exception as e:
            print(f"⚠️ Ошибка сохранения состояния блокировки: {e}")
    
    def get_secret_pin(self):
        """Получает текущий секретный PIN из config.json."""
        try:
            # Сначала пробуем получить из Flask app.config
            from flask import current_app
            try:
                if current_app and 'secret_pin' in current_app.config:
                    return current_app.config['secret_pin'].get('current_pin', '1234')
            except:
                pass
            
            # Если не получилось, читаем из файла
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('secret_pin', {}).get('current_pin', '1234')
        except Exception as e:
            print(f"⚠️ Ошибка загрузки PIN из config.json: {e}")
            return '1234'
    
    def is_pin_login_blocked(self):
        """Проверяет, заблокирован ли вход по PIN."""
        if self.pin_blocked_until is None:
            return False
        
        now = datetime.now()
        if now >= self.pin_blocked_until:
            self.pin_blocked_until = None
            self.pin_attempts = 0
            self._save_block_state()
            return False
        
        return True
    
    def get_pin_block_remaining(self):
        """Возвращает оставшееся время блокировки в секундах."""
        if not self.is_pin_login_blocked():
            return 0
        
        now = datetime.now()
        remaining = (self.pin_blocked_until - now).total_seconds()
        return max(0, int(remaining))
    
    def block_pin_login(self):
        """Блокирует вход по PIN на заданное время."""
        # Дополнительная проверка перед блокировкой
        # Если попыток меньше 3, не блокируем
        if self.pin_attempts < 3:
            print(f"⚠️ Попытка блокировки при недостаточном количестве попыток: {self.pin_attempts}")
            return
            
        self.pin_blocked_until = datetime.now() + timedelta(seconds=self.pin_block_duration)
        print(f"🔒 Вход по PIN заблокирован на {self.pin_block_duration} секунд")
        self._save_block_state()
    
    def authenticate_pin(self, pin):
        """Аутентификация через PIN-код с защитой от перебора."""
        try:
            # Проверяем блокировку
            if self.is_pin_login_blocked():
                remaining = self.get_pin_block_remaining()
                print(f"🔒 Вход по PIN заблокирован, осталось {remaining} секунд")
                return False, f"Вход заблокирован на {remaining} секунд"
            
            # Получаем текущий PIN
            current_pin = self.get_secret_pin()
            
            # Проверяем PIN-код
            if pin == current_pin:
                # Успешная аутентификация - сбрасываем счетчик попыток
                self.pin_attempts = 0
                self.pin_blocked_until = None
                self._save_block_state()
                
                session['pin_authenticated'] = True
                session['pin_login_used'] = True
                print("🔐 Аутентификация по PIN успешна")
                return True, gettext("Аутентификация успешна")
            else:
                # Неудачная попытка - увеличиваем счетчик
                self.pin_attempts += 1
                print(f"❌ Неверный PIN-код (попытка {self.pin_attempts})")
                
                # Повторная проверка PIN перед блокировкой для избежания ошибок
                # Это защита от случаев, когда PIN мог измениться в другой сессии
                if self.pin_attempts >= 3:
                    # Перепроверяем текущий PIN из конфига (на случай если он изменился)
                    try:
                        with open(self.config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        fresh_pin = config.get('secret_pin', {}).get('current_pin', '1234')
                        
                        # Если PIN совпадает с актуальным из конфига, не блокируем
                        if pin == fresh_pin:
                            print("🔄 PIN совпадает с актуальным в конфиге, сбрасываем счетчик")
                            self.pin_attempts = 0
                            self._save_block_state()
                            
                            session['pin_authenticated'] = True
                            session['pin_login_used'] = True
                            return True, gettext("Аутентификация успешна")
                    except Exception as e:
                        print(f"⚠️ Ошибка при перепроверке PIN: {e}")
                    
                    # Если перепроверка не помогла, блокируем
                    self.block_pin_login()
                    self._save_block_state()
                    return False, f"Неверный PIN-код. Вход заблокирован на {self.pin_block_duration} секунд"
                else:
                    self._save_block_state()
                    return False, "Неверный PIN-код"
        except Exception as e:
            print(f"⚠️ Ошибка в authenticate_pin: {e}")
            return False, f"Ошибка аутентификации: {e}"
    
    def change_pin(self, old_pin, new_pin):
        """Сменяет PIN-код."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Проверяем старый PIN
            current_pin = config.get('secret_pin', {}).get('current_pin', '1234')
            if old_pin != current_pin:
                return False, "Старый PIN неверен"
            
            # Проверяем новый PIN
            if not new_pin or len(new_pin) < 4:
                return False, "Новый PIN должен содержать минимум 4 символа"
            
            if new_pin == old_pin:
                return False, "Новый PIN не должен совпадать со старым"
            
            # Обновляем конфигурацию
            if 'secret_pin' not in config:
                config['secret_pin'] = {}
            
            config['secret_pin']['current_pin'] = new_pin
            config['secret_pin']['last_changed'] = datetime.now().strftime('%Y-%m-%d')
            
            # Сохраняем
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Обновляем Flask app.config
            try:
                from flask import current_app
                if current_app:
                    current_app.config['secret_pin'] = config['secret_pin']
            except:
                pass
            
            return True, "PIN успешно изменён"
        except Exception as e:
            print(f"⚠️ Ошибка смены PIN: {e}")
            return False, f"Ошибка сохранения PIN: {e}"
    
    def change_pin_without_old(self, new_pin):
        """Создает новый PIN-код без проверки старого (для первого запуска)."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Проверяем новый PIN
            if not new_pin or len(new_pin) < 4:
                return False, "PIN должен содержать минимум 4 символа"
            
            # Обновляем конфигурацию
            if 'secret_pin' not in config:
                config['secret_pin'] = {}
            
            config['secret_pin']['current_pin'] = new_pin
            config['secret_pin']['last_changed'] = datetime.now().strftime('%Y-%m-%d')
            
            # Сохраняем
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Обновляем Flask app.config
            try:
                from flask import current_app
                if current_app:
                    current_app.config['secret_pin'] = config['secret_pin']
            except:
                pass
            
            return True, "PIN успешно создан"
        except Exception as e:
            print(f"⚠️ Ошибка создания PIN: {e}")
            return False, f"Ошибка сохранения PIN: {e}"
    
    def is_authenticated(self):
        """Проверяет, аутентифицирован ли пользователь по PIN."""
        return session.get('pin_authenticated', False)
    
    def require_auth(self, f):
        """Декоратор для защиты маршрутов."""
        def decorated(*args, **kwargs):
            if not self.is_authenticated():
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        decorated.__name__ = f.__name__
        return decorated

# Создаем глобальный экземпляр
pin_auth = PinAuth() 