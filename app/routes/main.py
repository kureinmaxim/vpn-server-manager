from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, current_app
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
import logging
import os
import json
import datetime
import shutil
import zipfile
import signal
from ..services import registry
from ..utils.decorators import require_auth, require_pin, handle_errors, log_request
from ..exceptions import ValidationError, AuthenticationError

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

def get_secret_pin():
    """Получает текущий PIN из config.json"""
    try:
        config_path = os.path.join(current_app.config.get('APP_DATA_DIR', '.'), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('secret_pin', {}).get('current_pin', '1234')
    except Exception as e:
        logger.error(f"Error loading PIN from config: {e}")
        return '1234'

@main_bp.route('/')
@log_request
def index():
    """Главная страница"""
    # Проверяем PIN авторизацию
    logger.info(f"Index route accessed. Session: {dict(session)}")
    if not session.get('pin_authenticated'):
        logger.warning("Not authenticated, redirecting to locked page")
        return redirect(url_for('main.index_locked'))
    
    try:
        # Получаем список серверов из активного файла данных
        data_manager = registry.get('data_manager')
        if data_manager:
            servers = data_manager.load_servers(current_app.config)
            logger.info(f"Loaded {len(servers)} servers from active data file")
        else:
            servers = []
            logger.warning("DataManager not available, using empty server list")
        
        # Загружаем service_urls из конфигурации
        service_urls = {
            'general_ip_test': current_app.config.get('GENERAL_IP_TEST', 'https://browserleaks.com/ip'),
            'general_dns_test': current_app.config.get('GENERAL_DNS_TEST', 'https://dnsleaktest.com/'),
            'ip2location_demo': current_app.config.get('IP2LOCATION_DEMO', 'https://www.ip2location.com/demo')
        }
        
        return render_template('index.html', servers=servers, service_urls=service_urls)
    except Exception as e:
        logger.error(f"Error loading main page: {str(e)}")
        flash(_('Error loading servers'), 'error')
        # Предоставляем дефолтные значения для service_urls даже при ошибке
        service_urls = {
            'general_ip_test': 'https://browserleaks.com/ip',
            'general_dns_test': 'https://dnsleaktest.com/',
            'ip2location_demo': 'https://www.ip2location.com/demo'
        }
        return render_template('index.html', servers=[], service_urls=service_urls)

@main_bp.route('/locked')
@log_request
def index_locked():
    """Заблокированная главная страница (требует PIN)"""
    return render_template('index_locked.html')

@main_bp.route('/verify_pin', methods=['POST'])
@handle_errors
def verify_pin():
    """Проверка PIN кода"""
    pin = request.form.get('pin', '').strip()
    
    if not pin:
        flash(_('PIN is required'), 'error')
        return redirect(url_for('main.index_locked'))
    
    # Здесь должна быть логика проверки PIN
    # Временно используем простую проверку
    if pin == '1234':  # Это должно быть из конфигурации
        session['authenticated'] = True
        session['pin_verified'] = True
        flash(_('PIN verified successfully'), 'success')
        return redirect(url_for('main.index'))
    else:
        flash(_('Invalid PIN'), 'error')
        return redirect(url_for('main.index_locked'))

@main_bp.route('/logout')
@log_request
def logout():
    """Выход из системы"""
    session.clear()
    flash(_('Logged out successfully'), 'info')
    return redirect(url_for('main.index_locked'))

@main_bp.route('/add_server')
@require_auth
@require_pin
@log_request
def add_server():
    """Страница добавления сервера"""
    return render_template('add_server.html')

@main_bp.route('/delete_server/<int:server_id>', methods=['POST'])
@require_auth
@require_pin
def delete_server(server_id):
    """Удаление сервера"""
    try:
        data_manager = registry.get('data_manager')
        if not data_manager:
            flash(_('Сервис данных не инициализирован.'), 'danger')
            return redirect(url_for('main.index'))
            
        servers = data_manager.load_servers(current_app.config)
        
        # Фильтруем список, исключая сервер с нужным ID
        original_count = len(servers)
        servers_to_keep = [s for s in servers if str(s.get('id')) != str(server_id)]
        
        if len(servers_to_keep) < original_count:
            active_file = data_manager.get_active_data_path(current_app.config)
            if active_file:
                data_manager.save_servers(servers_to_keep, active_file)
                flash(_('Сервер успешно удален.'), 'success')
            else:
                flash(_('Нет активного файла данных для сохранения изменений.'), 'error')
        else:
            flash(_('Сервер с ID %(server_id)s не найден.', server_id=server_id), 'warning')
        
        return redirect(url_for('main.index'))
    except Exception as e:
        logger.error(f"Error deleting server {server_id}: {str(e)}")
        flash(f'Ошибка при удалении сервера: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/edit_server/<server_id>', methods=['GET', 'POST'])
@require_auth
@require_pin
@log_request
def edit_server(server_id):
    """Страница редактирования сервера"""
    try:
        data_manager = registry.get('data_manager')
        crypto_service = registry.get('crypto')
        
        if not data_manager:
            flash(_('Сервис данных не инициализирован.'), 'danger')
            return redirect(url_for('main.index'))
            
        servers = data_manager.load_servers(current_app.config)
        
        # Ищем сервер по ID, приводя ID к строке для надежного сравнения
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            flash(_('Сервер с ID %(server_id)s не найден.', server_id=server_id), 'error')
            return redirect(url_for('main.index'))
        
        # Если POST - сохраняем изменения
        if request.method == 'POST':
            try:
                # Обновляем базовые поля
                server['name'] = request.form.get('name', server.get('name'))
                server['provider'] = request.form.get('provider', server.get('provider'))
                server['ip_address'] = request.form.get('ip_address', server.get('ip_address'))
                server['os'] = request.form.get('os', server.get('os'))
                server['status'] = request.form.get('status', server.get('status'))
                server['notes'] = request.form.get('notes', server.get('notes', ''))
                server['docker_info'] = request.form.get('docker_info', server.get('docker_info', ''))
                server['software_info'] = request.form.get('software_info', server.get('software_info', ''))
                server['card_color'] = request.form.get('card_color', server.get('card_color', '#ffc107'))
                server['panel_url'] = request.form.get('panel_url', server.get('panel_url', ''))
                server['hoster_url'] = request.form.get('hoster_url', server.get('hoster_url', ''))
                
                # Обновляем характеристики
                server['specs']['cpu'] = request.form.get('cpu', server['specs'].get('cpu', ''))
                server['specs']['ram'] = request.form.get('ram', server['specs'].get('ram', ''))
                server['specs']['disk'] = request.form.get('disk', server['specs'].get('disk', ''))
                
                # Обновляем платежную информацию
                server['payment_info']['amount'] = float(request.form.get('amount', 0) or 0)
                server['payment_info']['currency'] = request.form.get('currency', 'USD')
                server['payment_info']['next_due_date'] = request.form.get('next_due_date', '')
                server['payment_info']['payment_period'] = request.form.get('payment_period', 'Monthly')
                
                # Обновляем SSH данные
                server['ssh_credentials']['user'] = request.form.get('ssh_user', server['ssh_credentials'].get('user', ''))
                server['ssh_credentials']['port'] = int(request.form.get('ssh_port', 22) or 22)
                server['ssh_credentials']['root_login_allowed'] = bool(request.form.get('root_login_allowed'))
                
                # Обновляем пароли SSH если указаны новые
                new_ssh_password = request.form.get('ssh_password', '').strip()
                if new_ssh_password and crypto_service:
                    server['ssh_credentials']['password'] = crypto_service.encrypt(new_ssh_password)
                    server['ssh_credentials']['password_decrypted'] = new_ssh_password
                
                new_root_password = request.form.get('ssh_root_password', '').strip()
                if new_root_password and crypto_service:
                    server['ssh_credentials']['root_password'] = crypto_service.encrypt(new_root_password)
                    server['ssh_credentials']['root_password_decrypted'] = new_root_password
                
                # Обновляем данные панели управления
                new_panel_user = request.form.get('panel_user', '').strip()
                if new_panel_user and crypto_service:
                    server['panel_credentials']['user'] = crypto_service.encrypt(new_panel_user)
                    server['panel_credentials']['user_decrypted'] = new_panel_user
                
                new_panel_password = request.form.get('panel_password', '').strip()
                if new_panel_password and crypto_service:
                    server['panel_credentials']['password'] = crypto_service.encrypt(new_panel_password)
                    server['panel_credentials']['password_decrypted'] = new_panel_password
                
                # Обновляем данные хостера
                server['hoster_credentials']['login_method'] = request.form.get('hoster_login_method', 'password')
                
                new_hoster_user = request.form.get('hoster_user', '').strip()
                if new_hoster_user and crypto_service:
                    server['hoster_credentials']['user'] = crypto_service.encrypt(new_hoster_user)
                    server['hoster_credentials']['user_decrypted'] = new_hoster_user
                
                new_hoster_password = request.form.get('hoster_password', '').strip()
                if new_hoster_password and crypto_service:
                    server['hoster_credentials']['password'] = crypto_service.encrypt(new_hoster_password)
                    server['hoster_credentials']['password_decrypted'] = new_hoster_password
                
                # Обновляем проверки
                server['checks']['dns_ok'] = bool(request.form.get('check_dns_ok'))
                server['checks']['streaming_ok'] = bool(request.form.get('check_streaming_ok'))
                
                # Сохраняем обновленный список серверов
                active_file = data_manager.get_active_data_path(current_app.config)
                if active_file:
                    data_manager.save_servers(servers, active_file)
                    flash(_('Изменения успешно сохранены.'), 'success')
                    return redirect(url_for('main.index'))
                else:
                    flash(_('Нет активного файла данных для сохранения изменений.'), 'error')
                    
            except Exception as save_error:
                logger.error(f"Error saving server {server_id}: {str(save_error)}")
                flash(_('Ошибка при сохранении изменений: %(error)s', error=str(save_error)), 'error')
        
        return render_template('edit_server.html', server=server)
        
    except Exception as e:
        logger.error(f"Error loading server {server_id}: {str(e)}")
        flash(_('Ошибка при загрузке данных сервера.'), 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/settings')
@require_auth
@require_pin
@log_request
def settings():
    """Страница настроек"""
    return render_template(
        'settings.html',
        active_data_file=current_app.config.get('active_data_file')
    )

# TODO: Implement these routes (moved from old app.py)
@main_bp.route('/change_main_key', methods=['POST'])
@require_auth
@require_pin
def change_main_key():
    """Смена главного ключа с перешифровкой всех данных."""
    from cryptography.fernet import Fernet
    import sys
    from pathlib import Path
    
    try:
        data_manager = registry.get('data_manager')
        new_key = request.form.get('new_key', '').strip()
        confirm_key = request.form.get('confirm_key', '').strip()
        
        # Проверяем, что ключи совпадают
        if new_key != confirm_key:
            flash(_('Ошибка: ключи не совпадают.'), 'danger')
            return redirect(url_for('main.settings'))
        
        # Проверяем формат нового ключа
        if not new_key:
            flash(_('Ошибка: новый ключ не может быть пустым.'), 'danger')
            return redirect(url_for('main.settings'))
            
        try:
            # Проверяем, что новый ключ корректный для Fernet
            test_fernet = Fernet(new_key.encode())
        except Exception:
            flash(_('Ошибка: некорректный формат ключа. Ключ должен быть в формате Fernet.'), 'danger')
            return redirect(url_for('main.settings'))
        
        # Загружаем текущие данные с существующим ключом
        current_servers = data_manager.load_servers(current_app.config)
        
        # Создаем резервную копию
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        app_data_dir = current_app.config.get('APP_DATA_DIR')
        data_dir = os.path.join(app_data_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        active_file = current_app.config.get('active_data_file')
        if active_file and os.path.exists(active_file):
            backup_path = data_manager.create_backup(
                active_file,
                data_dir,
                prefix=f"backup_before_key_change_{timestamp}"
            )
        
        # Обновляем конфигурацию с новым ключом
        current_app.config['SECRET_KEY'] = new_key
        
        # Определяем правильный путь к .env файлу
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            # Для упакованного приложения сохраняем .env в пользовательскую директорию
            env_file = os.path.join(app_data_dir, '.env')
        else:
            # Для разработки используем локальный .env
            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Обновляем или добавляем SECRET_KEY
        key_updated = False
        for i, line in enumerate(env_lines):
            if line.startswith('SECRET_KEY='):
                env_lines[i] = f'SECRET_KEY={new_key}\n'
                key_updated = True
                break
        
        if not key_updated:
            env_lines.append(f'SECRET_KEY={new_key}\n')
        
        # Создаем директорию если нужно
        os.makedirs(os.path.dirname(env_file) if os.path.dirname(env_file) else '.', exist_ok=True)
        
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
        
        # Создаем новый зашифрованный файл с новым ключом
        new_filename = f"servers_reencrypted_{timestamp}.enc"
        new_file_path = os.path.join(data_dir, new_filename)
        
        # Создаем новый DataManagerService с новым ключом
        new_data_manager = DataManagerService(new_key, app_data_dir)
        new_data_manager.save_servers(current_servers, new_file_path)
        
        # Обновляем конфигурацию приложения
        current_app.config['active_data_file'] = new_file_path
        
        # Сохраняем конфигурацию
        config_path = os.path.join(app_data_dir, 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config_data = {}
        
        config_data['active_data_file'] = new_file_path
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # Обновляем data_manager в реестре с новым ключом
        registry.register('data_manager', new_data_manager)
        
        flash(f'✅ Ключ успешно изменен! Создан новый файл данных: {new_filename}. Резервная копия сохранена.', 'success')
        flash('⚠️ Перезапустите приложение для применения изменений.', 'warning')
            
    except Exception as e:
        logger.error(f"Error changing key: {str(e)}")
        flash(f'Ошибка при смене ключа: {str(e)}', 'danger')
    
    return redirect(url_for('main.settings'))

@main_bp.route('/verify_key_data', methods=['POST'])
@require_auth
@require_pin
def verify_key_data():
    """Проверка соответствия ключа и данных без импорта."""
    try:
        data_manager = registry.get('data_manager')
        uploaded_file = request.files.get('verify_file')
        test_key = request.form.get('verify_key', '').strip()
        
        if not uploaded_file or not test_key:
            flash(_('Необходимо выбрать файл и указать ключ для проверки.'), 'danger')
            return redirect(url_for('main.settings'))
        
        if not uploaded_file.filename.endswith('.enc'):
            flash(_('Неверный тип файла. Выберите файл .enc'), 'danger')
            return redirect(url_for('main.settings'))
        
        # Читаем файл
        file_content = uploaded_file.read()
        
        # Проверяем ключ
        result = data_manager.verify_key_for_file(file_content, test_key)
        
        if result['success']:
            data = result['data']
            if isinstance(data, list):
                server_count = result.get('server_count', 0)
                providers = result.get('providers', [])
                server_names = result.get('server_names', [])
                
                provider_list = ', '.join(providers) if providers else 'Не указано'
                name_preview = ', '.join(server_names[:3])
                if len(server_names) > 3:
                    name_preview += f' и еще {len(server_names) - 3}'
                
                flash(f'✅ Ключ подходит! Найдено серверов: {server_count}. Провайдеры: {provider_list}. Серверы: {name_preview}', 'success')
            else:
                flash(_('✅ Ключ подходит, но структура данных неожиданная.'), 'warning')
        else:
            error = result['error']
            if error == 'invalid_key':
                flash(_('❌ Ключ не подходит к этому файлу данных.'), 'danger')
            elif error == 'invalid_json':
                flash(_('❌ Файл расшифрован, но содержит некорректные JSON данные.'), 'danger')
            else:
                flash(f'❌ Ошибка при проверке: {error}', 'danger')
            
    except Exception as e:
        logger.error(f"Error verifying key/data: {str(e)}")
        flash(f'Ошибка при обработке файла: {str(e)}', 'danger')
    
    return redirect(url_for('main.settings'))

@main_bp.route('/detach_data', methods=['POST'])
@require_auth
@require_pin
def detach_data():
    """Открепляет текущий файл данных."""
    try:
        if current_app.config.get('active_data_file'):
            current_app.config['active_data_file'] = None
            
            # Сохраняем конфигурацию
            app_data_dir = current_app.config.get('APP_DATA_DIR')
            config_path = os.path.join(app_data_dir, 'config.json')
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                config_data = {}
            
            config_data['active_data_file'] = None
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            flash(_('Файл данных успешно откреплен.'), 'info')
    except Exception as e:
        logger.error(f"Error detaching data: {str(e)}")
        flash(f'Ошибка при откреплении файла: {str(e)}', 'danger')
    
    return redirect(url_for('main.index'))

@main_bp.route('/import_data', methods=['POST'])
@require_auth
@require_pin
def import_data():
    """Импорт зашифрованного файла данных"""
    try:
        data_manager = registry.get('data_manager')
        if not data_manager:
            flash(_('Сервис управления данными не инициализирован. Проверьте конфигурацию и ключ шифрования.'), 'danger')
            return redirect(url_for('main.settings'))

        uploaded_file = request.files['data_file']
        
        if uploaded_file and data_manager.allowed_file(uploaded_file.filename, current_app.config.get('ALLOWED_EXTENSIONS')) and uploaded_file.filename.endswith('.enc'):
            # Создаем уникальное имя файла с временной меткой
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imported_{timestamp}_{secure_filename(uploaded_file.filename)}"
            
            # Получаем директорию для хранения данных
            app_data_dir = current_app.config.get('APP_DATA_DIR')
            data_dir = os.path.join(app_data_dir, "data")
            
            # Убедимся, что директория существует
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = os.path.join(data_dir, filename)
            uploaded_file.save(file_path)
            
            # Проверяем, что файл действительно зашифрован и может быть прочитан с нашим ключом
            try:
                with open(file_path, 'rb') as f:
                    encrypted_content = f.read()
                servers = data_manager.load_servers({'active_data_file': file_path})
                if not isinstance(servers, list):
                    raise ValueError("Invalid data structure")
                
                server_count = len(servers)
                flash(f'✅ Файл данных успешно импортирован! Найдено серверов: {server_count}', 'success')
                logger.info(f"Successfully imported {server_count} servers from {filename}")
            except Exception as e:
                # Удаляем файл, если он не может быть расшифрован
                os.remove(file_path)
                logger.error(f"Error decrypting imported file: {str(e)}")
                flash(_('Ошибка: файл не может быть расшифрован или поврежден. Возможно, он создан с другим ключом.'), 'danger')
                return redirect(url_for('main.settings'))
            
            # Обновляем конфигурацию для использования нового файла
            current_app.config['active_data_file'] = file_path
            
            # Сохраняем конфигурацию через DataManagerService
            if not data_manager.update_user_config({'active_data_file': file_path}):
                flash(_('Не удалось сохранить путь к новому файлу данных. Изменение будет временным.'), 'warning')
            
            # Перенаправляем на главную страницу, чтобы пользователь увидел импортированные серверы
            flash('💡 Обновите страницу (F5), если серверы не отображаются сразу.', 'info')
            return redirect(url_for('main.index'))
        else:
            flash(_('Неверный тип файла. Пожалуйста, выберите файл .enc'), 'danger')
    except Exception as e:
        logger.error(f"Error importing data: {str(e)}")
        flash(f'Ошибка при импорте файла: {str(e)}', 'danger')
    return redirect(url_for('main.settings'))

@main_bp.route('/import_external_data', methods=['POST'])
@require_auth
@require_pin
def import_external_data():
    """Импорт внешних данных с другим ключом шифрования"""
    import tempfile
    from cryptography.fernet import Fernet, InvalidToken
    
    try:
        data_manager = registry.get('data_manager')
        if not data_manager:
            flash(_('Сервис управления данными не инициализирован. Проверьте конфигурацию и ключ шифрования.'), 'danger')
            return redirect(url_for('main.settings'))
            
        uploaded_file = request.files['external_file']
        external_key = request.form.get('external_key', '').strip()
        
        if not uploaded_file or not external_key:
            flash(_('Необходимо выбрать файл и указать внешний ключ шифрования.'), 'danger')
            return redirect(url_for('main.settings'))
            
        if not uploaded_file.filename.endswith('.enc'):
            flash(_('Неверный тип файла. Пожалуйста, выберите файл .enc'), 'danger')
            return redirect(url_for('main.settings'))
        
        # Проверяем формат ключа
        try:
            test_fernet = Fernet(external_key.encode())
        except Exception:
            flash(_('Неверный формат ключа шифрования. Ключ должен быть действительным ключом Fernet.'), 'danger')
            return redirect(url_for('main.settings'))
        
        # Создаем временный файл для проверки
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            uploaded_file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Пытаемся расшифровать файл с внешним ключом
            with open(temp_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            fernet_external = Fernet(external_key.encode())
            decrypted_data = fernet_external.decrypt(encrypted_data)
            servers_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Проверяем структуру данных
            if not isinstance(servers_data, list):
                raise ValueError("Неверная структура данных")
            
            # Загружаем текущие серверы
            current_servers = data_manager.load_servers(current_app.config)
            
            # Объединяем серверы
            merge_result = data_manager.merge_servers(current_servers, servers_data)
            merged_servers = merge_result['merged_servers']
            added_count = merge_result['added_count']
            skipped_count = merge_result['skipped_count']
            
            # Перешифровываем пароли в новых серверах
            our_secret_key = current_app.config.get('SECRET_KEY')
            for server in merged_servers[len(current_servers):]:  # Только новые серверы
                # Перешифровываем SSH пароли
                if 'ssh_credentials' in server:
                    if 'password' in server['ssh_credentials'] and server['ssh_credentials']['password']:
                        server['ssh_credentials']['password'] = data_manager.re_encrypt_password(
                            server['ssh_credentials']['password'],
                            external_key,
                            our_secret_key
                        )
                    if 'root_password' in server['ssh_credentials'] and server['ssh_credentials']['root_password']:
                        server['ssh_credentials']['root_password'] = data_manager.re_encrypt_password(
                            server['ssh_credentials']['root_password'],
                            external_key,
                            our_secret_key
                        )
                
                # Перешифровываем пароли панели управления
                if 'panel_credentials' in server:
                    if 'password' in server['panel_credentials'] and server['panel_credentials']['password']:
                        server['panel_credentials']['password'] = data_manager.re_encrypt_password(
                            server['panel_credentials']['password'],
                            external_key,
                            our_secret_key
                        )
                    if 'user' in server['panel_credentials'] and server['panel_credentials']['user']:
                        server['panel_credentials']['user'] = data_manager.re_encrypt_password(
                            server['panel_credentials']['user'],
                            external_key,
                            our_secret_key
                        )
                
                # Перешифровываем пароли кабинета хостера
                if 'hoster_credentials' in server:
                    if 'password' in server['hoster_credentials'] and server['hoster_credentials']['password']:
                        server['hoster_credentials']['password'] = data_manager.re_encrypt_password(
                            server['hoster_credentials']['password'],
                            external_key,
                            our_secret_key
                        )
                    if 'user' in server['hoster_credentials'] and server['hoster_credentials']['user']:
                        server['hoster_credentials']['user'] = data_manager.re_encrypt_password(
                            server['hoster_credentials']['user'],
                            external_key,
                            our_secret_key
                        )
            
            # Создаем новый файл с объединенными данными
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"merged_{timestamp}.enc"
            
            app_data_dir = current_app.config.get('APP_DATA_DIR')
            data_dir = os.path.join(app_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = os.path.join(data_dir, filename)
            data_manager.save_servers(merged_servers, file_path)
            
            # Обновляем конфигурацию
            current_app.config['active_data_file'] = file_path
            
            # Сохраняем конфигурацию
            config_path = os.path.join(app_data_dir, 'config.json')
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                config_data = {}
            
            config_data['active_data_file'] = file_path
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            # Информируем пользователя о результате
            if added_count > 0:
                message = f'Успешно импортировано {added_count} новых серверов!'
                if skipped_count > 0:
                    message += f' Пропущено {skipped_count} дублирующихся серверов.'
                flash(_(message), 'success')
            else:
                flash(_('Все сервера из импортируемого файла уже существуют в вашем списке.'), 'info')
            
        except InvalidToken:
            flash(_('Ошибка: неверный ключ шифрования. Проверьте правильность введенного ключа.'), 'danger')
        except json.JSONDecodeError:
            flash(_('Ошибка: файл содержит некорректные данные.'), 'danger')
        except Exception as e:
            logger.error(f"Error importing external data: {str(e)}")
            flash(f'Ошибка при импорте: {str(e)}', 'danger')
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        logger.error(f"Error processing external import: {str(e)}")
        flash(f'Ошибка при обработке файла: {str(e)}', 'danger')
    
    return redirect(url_for('main.settings'))

@main_bp.route('/export_data')
@require_auth
@require_pin
def export_data():
    """Отдает текущий активный файл данных для скачивания."""
    try:
        data_manager = registry.get('data_manager')
        active_file = data_manager.get_active_data_path(current_app.config)
        
        if not active_file or not os.path.exists(active_file):
            flash(_('Нет активного файла данных для экспорта.'), 'warning')
            return redirect(url_for('main.settings'))
        
        # Создаем копию файла в папке Downloads для удобного доступа
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"servers_export_{timestamp}.enc"
        export_dir = data_manager.get_export_dir()
        export_path = os.path.join(export_dir, export_filename)
        
        # Копируем файл в папку Downloads
        shutil.copy2(active_file, export_path)
        
        flash(f'✅ Файл данных экспортирован как: {export_filename} в папку Downloads', 'success')
        
        return send_from_directory(
            export_dir, 
            export_filename, 
            as_attachment=True
        )
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        flash(f'Ошибка при экспорте: {str(e)}', 'danger')
        return redirect(url_for('main.settings'))

@main_bp.route('/export_key')
@require_auth
@require_pin
def export_key():
    """Экспортирует SECRET_KEY в виде .env файла для скачивания."""
    try:
        data_manager = registry.get('data_manager')
        export_dir = data_manager.get_export_dir()
        
        # Создаем .env файл в папке Downloads
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        key_filename = f"SECRET_KEY_{timestamp}.env"
        key_path = os.path.join(export_dir, key_filename)
        
        secret_key = current_app.config.get('SECRET_KEY')
        with open(key_path, 'w', encoding='utf-8') as f:
            f.write(f"SECRET_KEY={secret_key}\n")
            f.write(f"FLASK_SECRET_KEY=portable_app_key\n")
        
        flash(f'✅ Ключ шифрования экспортирован как: {key_filename} в папку Downloads', 'success')
        
        return send_from_directory(
            export_dir,
            key_filename,
            as_attachment=True
        )
    except Exception as e:
        logger.error(f"Error exporting key: {str(e)}")
        flash(f'Ошибка при экспорте ключа: {str(e)}', 'danger')
        return redirect(url_for('main.settings'))

@main_bp.route('/export_package')
@require_auth
@require_pin
def export_package():
    """Создает ZIP архив с данными, ключом и загруженными файлами."""
    try:
        data_manager = registry.get('data_manager')
        
        # Проверяем наличие активного файла данных
        active_file = data_manager.get_active_data_path(current_app.config)
        if not active_file or not os.path.exists(active_file):
            flash(_('Нет активного файла данных для экспорта.'), 'warning')
            return redirect(url_for('main.settings'))
        
        # Создаем ZIP файл в папке Downloads
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f'vpn_servers_backup_{timestamp}.zip'
        export_dir = data_manager.get_export_dir()
        zip_path = os.path.join(export_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавляем файл данных сервера
            zipf.write(active_file, f"servers_{timestamp}.enc")
            
            # Создаем и добавляем файл с ключом
            secret_key = current_app.config.get('SECRET_KEY')
            env_content = f"SECRET_KEY={secret_key}\nFLASK_SECRET_KEY=portable_app_key\n"
            zipf.writestr("SECRET_KEY.env", env_content)
            
            # Добавляем файл с PIN-кодом
            current_pin = get_secret_pin()
            pin_content = f"PIN={current_pin}\n"
            zipf.writestr("PIN.txt", pin_content)
            
            # Добавляем загруженные файлы (если они есть)
            app_data_dir = current_app.config.get('APP_DATA_DIR')
            uploads_dir = os.path.join(app_data_dir, "uploads")
            if os.path.exists(uploads_dir):
                for filename in os.listdir(uploads_dir):
                    file_path = os.path.join(uploads_dir, filename)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, f"uploads/{filename}")
            
            # Добавляем README с инструкциями
            readme_content = f"""VPN Server Manager - Экспорт данных
===========================================

Дата экспорта: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

Содержимое архива:
- servers_{timestamp}.enc - Зашифрованные данные серверов
- SECRET_KEY.env - Ключ шифрования (поместите в папку с приложением)
- PIN.txt - PIN-код для входа в приложение
- uploads/ - Загруженные файлы (счета, скриншоты и т.д.)

Инструкция по импорту:
1. Скопируйте SECRET_KEY.env в папку с новой установкой VPN Server Manager
2. Переименуйте SECRET_KEY.env в .env
3. Перезапустите приложение
4. В разделе "Настройки" -> "Управление данными" импортируйте файл servers_{timestamp}.enc
5. Скопируйте содержимое папки uploads/ в папку uploads/ новой установки
6. Запомните PIN-код из файла PIN.txt для входа в приложение

ВАЖНО: Храните этот архив в безопасном месте. Любой, кто имеет доступ к нему,
может расшифровать ваши данные о серверах!
"""
            zipf.writestr("README.txt", readme_content)
        
        flash(f'✅ Полный архив создан как: {zip_filename} в папке Downloads', 'success')
        
        # Отправляем ZIP файл
        return send_from_directory(
            export_dir,
            zip_filename,
            as_attachment=True
        )
        
    except Exception as e:
        logger.error(f"Error creating export package: {str(e)}")
        flash(f'Ошибка при создании архива: {str(e)}', 'danger')
        return redirect(url_for('main.settings'))

@main_bp.route('/help')
@log_request
def help():
    """Страница помощи"""
    return render_template('help.html')

@main_bp.route('/about')
@log_request
def about():
    """Страница о приложении"""
    return render_template('about.html')

@main_bp.route('/cheatsheet')
@require_auth
@require_pin
@log_request
def cheatsheet():
    """Страница шпаргалки"""
    return render_template('cheatsheet.html')

@main_bp.route('/manage_hints')
@require_auth
@require_pin
@log_request
def manage_hints():
    """Страница управления подсказками"""
    hints = _load_hints()
    
    # Словарь переводов для названий групп
    group_translations = {
        'Ключевые утилиты': {
            'ru': 'Ключевые утилиты',
            'en': 'Key utilities',
            'zh': '关键工具'
        },
        'Управление службами': {
            'ru': 'Управление службами',
            'en': 'Service management',
            'zh': '服务管理'
        },
        'Управление пакетами': {
            'ru': 'Управление пакетами',
            'en': 'Package management',
            'zh': '包管理'
        },
        'Безопасность': {
            'ru': 'Безопасность',
            'en': 'Security',
            'zh': '安全'
        }
    }
    
    # Получаем текущий язык
    from flask_babel import get_locale
    current_lang = str(get_locale())
    
    # Переводим названия групп
    for hint in hints:
        if hint['group'] in group_translations:
            hint['group_display'] = group_translations[hint['group']].get(current_lang, hint['group'])
        else:
            hint['group_display'] = hint['group']
    
    return render_template('manage_hints.html', hints=hints)

@main_bp.route('/add_hint', methods=['POST'])
@require_auth
@require_pin
@log_request
def add_hint():
    """Добавить новую подсказку"""
    hints = _load_hints()
    new_id = max([h['id'] for h in hints] + [0]) + 1
    
    new_hint = {
        "id": new_id,
        "group": request.form['group'],
        "command": request.form['command']
    }
    hints.append(new_hint)
    _save_hints(hints)
    flash(_('Hint added successfully'), 'success')
    return redirect(url_for('main.manage_hints'))

@main_bp.route('/delete_hint/<int:hint_id>', methods=['POST'])
@require_auth
@require_pin
@log_request
def delete_hint(hint_id):
    """Удалить подсказку"""
    hints = _load_hints()
    hints = [h for h in hints if h['id'] != hint_id]
    _save_hints(hints)
    flash(_('Hint deleted successfully'), 'success')
    return redirect(url_for('main.manage_hints'))

# Helper functions for hints
def _load_hints():
    """Загрузка подсказок из JSON файла"""
    try:
        app_data_dir = current_app.config.get('APP_DATA_DIR', '.')
        hints_path = os.path.join(app_data_dir, 'data', 'hints.json')
        if os.path.exists(hints_path):
            with open(hints_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading hints: {e}")
    return []

def _save_hints(hints):
    """Сохранение подсказок в JSON файл"""
    try:
        app_data_dir = current_app.config.get('APP_DATA_DIR', '.')
        hints_path = os.path.join(app_data_dir, 'data', 'hints.json')
        os.makedirs(os.path.dirname(hints_path), exist_ok=True)
        with open(hints_path, 'w', encoding='utf-8') as f:
            json.dump(hints, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving hints: {e}")

@main_bp.route('/change_language/<language>')
@log_request
def change_language(language):
    """Смена языка интерфейса"""
    if language in ['ru', 'en', 'zh']:
        session['language'] = language
        session.permanent = True  # Сохраняем сессию
        session.modified = True   # Явно помечаем как измененную
        flash(_('Language changed successfully'), 'success')
    else:
        flash(_('Unsupported language'), 'error')
    
    return redirect(request.referrer or url_for('main.index'))

@main_bp.route('/test_connection/<server_id>')
@require_auth
@require_pin
@handle_errors
def test_connection(server_id):
    """Тестирование подключения к серверу"""
    try:
        # Здесь должна быть логика тестирования подключения
        # Временно возвращаем успешный результат
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': _('Connection test successful')
            })
        else:
            flash(_('Connection test successful'), 'success')
            return redirect(url_for('main.index'))
            
    except Exception as e:
        logger.error(f"Connection test failed for server {server_id}: {str(e)}")
        
        if request.is_json:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
        else:
            flash(_('Connection test failed: %(error)s', error=str(e)), 'error')
            return redirect(url_for('main.index'))

@main_bp.route('/server_status/<server_id>')
@require_auth
@require_pin
def server_status(server_id):
    """Получение статуса сервера"""
    try:
        # Здесь должна быть логика получения статуса сервера
        status = {
            'connected': False,
            'last_check': None,
            'error': None
        }
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting server status {server_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/monitoring/<server_id>')
@require_auth
@require_pin
@log_request
def monitoring(server_id):
    """Страница расширенного мониторинга сервера"""
    try:
        data_manager = registry.get('data_manager')
        if not data_manager:
            flash(_('Сервис данных не инициализирован.'), 'danger')
            return redirect(url_for('main.index'))
            
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            flash(_('Сервер с ID %(server_id)s не найден.', server_id=server_id), 'error')
            return redirect(url_for('main.index'))
        
        return render_template('monitoring.html', server=server)
        
    except Exception as e:
        logger.error(f"Error loading monitoring page for server {server_id}: {str(e)}")
        flash(_('Ошибка при загрузке страницы мониторинга.'), 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    """Отдает загруженный файл (иконку сервера)"""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, filename)

@main_bp.route('/upload_icon', methods=['POST'])
@require_auth
@require_pin
@handle_errors
def upload_icon():
    """Загрузка иконки сервера"""
    if 'icon' not in request.files:
        flash(_('No file selected'), 'error')
        return redirect(request.referrer or url_for('main.index'))
    
    file = request.files['icon']
    if file.filename == '':
        flash(_('No file selected'), 'error')
        return redirect(request.referrer or url_for('main.index'))
    
    # Здесь должна быть логика обработки загруженного файла
    # Временно просто перенаправляем обратно
    
    flash(_('Icon uploaded successfully'), 'success')
    return redirect(request.referrer or url_for('main.index'))

@main_bp.route('/download_backup')
@require_auth
@require_pin
@log_request
def download_backup():
    """Скачивание резервной копии"""
    try:
        # Здесь должна быть логика создания и скачивания резервной копии
        flash(_('Backup download not implemented yet'), 'info')
        return redirect(url_for('main.settings'))
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        flash(_('Error creating backup'), 'error')
        return redirect(url_for('main.settings'))

@main_bp.route('/restore_backup', methods=['POST'])
@require_auth
@require_pin
@handle_errors
def restore_backup():
    """Восстановление из резервной копии"""
    if 'backup_file' not in request.files:
        flash(_('No backup file selected'), 'error')
        return redirect(url_for('main.settings'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash(_('No backup file selected'), 'error')
        return redirect(url_for('main.settings'))
    
    # Здесь должна быть логика восстановления из резервной копии
    flash(_('Backup restore not implemented yet'), 'info')
    return redirect(url_for('main.settings'))

@main_bp.route('/favicon.ico')
def favicon():
    """Favicon"""
    from flask import send_from_directory
    import os
    return send_from_directory(os.path.join(main_bp.root_path, '..', '..', 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@main_bp.route('/shutdown')
def shutdown():
    """Эндпоинт для корректного завершения сервера"""
    logger.info("Shutdown request received")
    
    # Отправляем сигнал завершения процессу
    os.kill(os.getpid(), signal.SIGINT)
    
    return 'Сервер выключается...', 200
