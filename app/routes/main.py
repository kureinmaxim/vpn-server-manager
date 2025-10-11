from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_babel import gettext as _
import logging
from ..services import registry
from ..utils.decorators import require_auth, require_pin, handle_errors, log_request
from ..exceptions import ValidationError, AuthenticationError

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@log_request
def index():
    """Главная страница"""
    if not session.get('authenticated'):
        return redirect(url_for('main.index_locked'))
    
    try:
        # Получаем список серверов
        crypto_service = registry.get('crypto')
        if crypto_service:
            # Здесь должна быть логика загрузки серверов
            servers = []  # Временно пустой список
        else:
            servers = []
        
        return render_template('index.html', servers=servers)
    except Exception as e:
        logger.error(f"Error loading main page: {str(e)}")
        flash(_('Error loading servers'), 'error')
        return render_template('index.html', servers=[])

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

@main_bp.route('/edit_server/<server_id>')
@require_auth
@require_pin
@log_request
def edit_server(server_id):
    """Страница редактирования сервера"""
    try:
        # Здесь должна быть логика загрузки сервера по ID
        server = None  # Временно None
        
        if not server:
            flash(_('Server not found'), 'error')
            return redirect(url_for('main.index'))
        
        return render_template('edit_server.html', server=server)
    except Exception as e:
        logger.error(f"Error loading server {server_id}: {str(e)}")
        flash(_('Error loading server'), 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/settings')
@require_auth
@require_pin
@log_request
def settings():
    """Страница настроек"""
    return render_template('settings.html')

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
    return render_template('manage_hints.html')

@main_bp.route('/change_language/<language>')
@log_request
def change_language(language):
    """Смена языка интерфейса"""
    if language in ['ru', 'en', 'zh']:
        session['language'] = language
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
