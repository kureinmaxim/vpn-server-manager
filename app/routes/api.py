from flask import Blueprint, request, jsonify, session
from flask_babel import gettext as _
import logging
from ..services import registry
from ..utils.decorators import require_auth, require_pin, validate_json, handle_errors
from ..utils.validators import Validators
from ..exceptions import ValidationError, AuthenticationError, APIError
from ..models.server import Server

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

# PIN endpoints (без /api префикса)
pin_bp = Blueprint('pin', __name__, url_prefix='/pin')

@api_bp.route('/servers', methods=['GET'])
@require_auth
@require_pin
def get_servers():
    """Получение списка серверов"""
    try:
        # Здесь должна быть логика загрузки серверов из зашифрованного файла
        servers = []  # Временно пустой список
        
        return jsonify({
            'success': True,
            'servers': [server.to_dict() if hasattr(server, 'to_dict') else server for server in servers]
        })
    except Exception as e:
        logger.error(f"Error getting servers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/servers', methods=['POST'])
@require_auth
@require_pin
@validate_json
@handle_errors
def create_server():
    """Создание нового сервера"""
    data = request.get_json()
    
    # Валидация данных
    errors = Validators.validate_server_data(data)
    if errors:
        raise ValidationError('; '.join(errors))
    
    try:
        # Создание объекта сервера
        server = Server(
            id=data.get('id', ''),
            name=data['name'],
            hostname=data['hostname'],
            username=data['username'],
            password=data.get('password'),
            key_file=data.get('key_file'),
            port=int(data.get('port', 22)),
            description=data.get('description')
        )
        
        # Дополнительная валидация
        validation_errors = server.validate()
        if validation_errors:
            raise ValidationError('; '.join(validation_errors))
        
        # Здесь должна быть логика сохранения сервера
        # Временно просто возвращаем успех
        
        return jsonify({
            'success': True,
            'message': _('Server created successfully'),
            'server': server.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating server: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/servers/<server_id>', methods=['GET'])
@require_auth
@require_pin
def get_server(server_id):
    """Получение сервера по ID"""
    try:
        # Здесь должна быть логика загрузки сервера по ID
        server = None  # Временно None
        
        if not server:
            return jsonify({
                'success': False,
                'error': _('Server not found')
            }), 404
        
        return jsonify({
            'success': True,
            'server': server.to_dict() if hasattr(server, 'to_dict') else server
        })
    except Exception as e:
        logger.error(f"Error getting server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/servers/<server_id>', methods=['PUT'])
@require_auth
@require_pin
@validate_json
@handle_errors
def update_server(server_id):
    """Обновление сервера"""
    data = request.get_json()
    
    # Валидация данных
    errors = Validators.validate_server_data(data)
    if errors:
        raise ValidationError('; '.join(errors))
    
    try:
        # Здесь должна быть логика обновления сервера
        # Временно просто возвращаем успех
        
        return jsonify({
            'success': True,
            'message': _('Server updated successfully')
        })
        
    except Exception as e:
        logger.error(f"Error updating server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/servers/<server_id>', methods=['DELETE'])
@require_auth
@require_pin
def delete_server(server_id):
    """Удаление сервера"""
    try:
        # Здесь должна быть логика удаления сервера
        # Временно просто возвращаем успех
        
        return jsonify({
            'success': True,
            'message': _('Server deleted successfully')
        })
        
    except Exception as e:
        logger.error(f"Error deleting server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/servers/<server_id>/test', methods=['POST'])
@require_auth
@require_pin
def test_server_connection(server_id):
    """Тестирование подключения к серверу"""
    try:
        # Здесь должна быть логика тестирования подключения
        # Временно возвращаем успешный результат
        
        return jsonify({
            'success': True,
            'message': _('Connection test successful'),
            'status': 'connected'
        })
        
    except Exception as e:
        logger.error(f"Connection test failed for server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'error'
        }), 500

@api_bp.route('/servers/<server_id>/status', methods=['GET'])
@require_auth
@require_pin
def get_server_status(server_id):
    """Получение статуса сервера"""
    try:
        # Здесь должна быть логика получения статуса сервера
        status = {
            'connected': False,
            'last_check': None,
            'error': None,
            'uptime': None,
            'load': None
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting server status {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/ip-check', methods=['GET'])
@require_auth
@require_pin
def check_ip():
    """Проверка IP адреса"""
    try:
        api_service = registry.get('api')
        if not api_service:
            raise APIError('API service not available')
        
        ip = request.args.get('ip')
        if ip:
            result = api_service.check_ip_info(ip)
        else:
            # Получаем текущий IP
            current_ip = api_service.get_current_ip()
            result = api_service.check_ip_info(current_ip)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error checking IP: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/dns-test', methods=['POST'])
@require_auth
@require_pin
def test_dns():
    """Тест DNS утечек"""
    try:
        api_service = registry.get('api')
        if not api_service:
            raise APIError('API service not available')
        
        result = api_service.test_dns_leak()
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error testing DNS: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/speed-test', methods=['POST'])
@require_auth
@require_pin
def test_speed():
    """Тест скорости соединения"""
    try:
        api_service = registry.get('api')
        if not api_service:
            raise APIError('API service not available')
        
        result = api_service.test_connection_speed()
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error testing speed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/backup', methods=['POST'])
@require_auth
@require_pin
def create_backup():
    """Создание резервной копии"""
    try:
        # Здесь должна быть логика создания резервной копии
        # Временно возвращаем успех
        
        return jsonify({
            'success': True,
            'message': _('Backup created successfully'),
            'backup_path': '/path/to/backup.json'
        })
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/restore', methods=['POST'])
@require_auth
@require_pin
@validate_json
def restore_backup():
    """Восстановление из резервной копии"""
    try:
        data = request.get_json()
        backup_data = data.get('backup_data')
        
        if not backup_data:
            raise ValidationError('Backup data is required')
        
        # Здесь должна быть логика восстановления из резервной копии
        # Временно возвращаем успех
        
        return jsonify({
            'success': True,
            'message': _('Backup restored successfully')
        })
        
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/settings', methods=['GET'])
@require_auth
@require_pin
def get_settings():
    """Получение настроек приложения"""
    try:
        # Здесь должна быть логика загрузки настроек
        settings = {
            'default_pin': '1234',
            'language': session.get('language', 'ru'),
            'auto_backup': True,
            'backup_interval': 24
        }
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/settings', methods=['PUT'])
@require_auth
@require_pin
@validate_json
@handle_errors
def update_settings():
    """Обновление настроек приложения"""
    try:
        data = request.get_json()
        
        # Здесь должна быть логика обновления настроек
        # Временно просто возвращаем успех
        
        return jsonify({
            'success': True,
            'message': _('Settings updated successfully')
        })
        
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# PIN endpoints
@pin_bp.route('/check_block', methods=['GET'])
def check_block():
    """Проверка блокировки входа"""
    try:
        # Проверяем блокировку в сессии
        block_until = session.get('block_until')
        if block_until:
            import time
            if time.time() < block_until:
                remaining = int(block_until - time.time())
                return jsonify({
                    'blocked': True,
                    'remaining': remaining
                })
            else:
                # Блокировка истекла
                session.pop('block_until', None)
        
        return jsonify({
            'blocked': False,
            'remaining': 0
        })
    except Exception as e:
        logger.error(f"Error checking block: {str(e)}")
        return jsonify({
            'blocked': False,
            'remaining': 0
        })

@pin_bp.route('/check_first_setup_allowed', methods=['GET'])
def check_first_setup_allowed():
    """Проверка, разрешен ли первый запуск"""
    try:
        # Проверяем, есть ли уже данные серверов
        import os
        servers_file = os.path.join('data', 'servers.json.enc')
        if os.path.exists(servers_file) and os.path.getsize(servers_file) > 0:
            return jsonify({
                'allowed': False,
                'reason': 'Data already exists'
            })
        
        return jsonify({
            'allowed': True
        })
    except Exception as e:
        logger.error(f"Error checking first setup: {str(e)}")
        return jsonify({
            'allowed': False,
            'error': str(e)
        })

@pin_bp.route('/login_ajax', methods=['POST', 'OPTIONS'])
def login_ajax():
    """AJAX авторизация по PIN"""
    # Обработка OPTIONS запроса (CORS preflight)
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        # Логируем для отладки
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request data: {request.get_data()}")
        logger.info(f"Request JSON: {request.get_json(silent=True)}")
        
        # Поддерживаем как JSON, так и form-data
        if request.is_json:
            data = request.get_json()
            pin = data.get('pin', '').strip() if data else ''
        else:
            # Обрабатываем form-data
            try:
                pin = request.form.get('pin', '').strip()
            except Exception as e:
                logger.error(f"Error getting form data: {e}")
                pin = ''
            
        logger.info(f"Extracted PIN: '{pin}'")
        
        if not pin:
            return jsonify({
                'success': False,
                'error': _('PIN is required')
            }), 400
        
        # Получаем правильный PIN из config.json
        def get_secret_pin():
            try:
                import json
                import os
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config.get('secret_pin', {}).get('current_pin', '1234')
            except Exception as e:
                logger.error(f"Error loading PIN from config: {e}")
                return '1234'
        
        current_pin = get_secret_pin()
        
        # Проверяем PIN
        if pin == current_pin:
            session['pin_authenticated'] = True
            session.pop('block_until', None)  # Снимаем блокировку
            session.pop('failed_attempts', None)  # Сбрасываем счетчик
            return jsonify({
                'success': True,
                'message': _('Login successful')
            })
        else:
            # Увеличиваем счетчик неудачных попыток
            failed_attempts = session.get('failed_attempts', 0) + 1
            session['failed_attempts'] = failed_attempts
            
            if failed_attempts >= 3:
                # Блокируем на 30 секунд
                import time
                session['block_until'] = time.time() + 30
                session['failed_attempts'] = 0
                return jsonify({
                    'success': False,
                    'error': _('Too many failed attempts. Blocked for 30 seconds.'),
                    'blocked': True
                }), 429
            
            return jsonify({
                'success': False,
                'error': _('Invalid PIN'),
                'attempts_left': 3 - failed_attempts
            }), 401
            
    except Exception as e:
        logger.error(f"Error in login_ajax: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pin_bp.route('/change_ajax', methods=['POST'])
def change_ajax():
    """AJAX смена PIN"""
    try:
        data = request.get_json()
        old_pin = data.get('old_pin', '').strip()
        new_pin = data.get('new_pin', '').strip()
        
        if not old_pin or not new_pin:
            return jsonify({
                'success': False,
                'error': _('Both old and new PIN are required')
            }), 400
        
        # Здесь должна быть проверка старого PIN и сохранение нового
        # Временно используем простую проверку
        if old_pin == '1234':  # Дефолтный PIN
            # Здесь должно быть сохранение нового PIN
            return jsonify({
                'success': True,
                'message': _('PIN changed successfully')
            })
        else:
            return jsonify({
                'success': False,
                'error': _('Invalid old PIN')
            }), 401
            
    except Exception as e:
        logger.error(f"Error in change_ajax: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
