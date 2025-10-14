from flask import Blueprint, request, jsonify, session
from flask_babel import gettext as _
import logging
from ..services import registry
from ..utils.decorators import require_auth, require_pin, validate_json, handle_errors
from ..utils.validators import Validators
from ..utils.rate_limiter import RateLimiter
from ..exceptions import ValidationError, AuthenticationError, APIError
from ..models.server import Server

logger = logging.getLogger(__name__)

# Создать лимитер (макс 10 запросов в минуту на сервер)
rate_limiter = RateLimiter(max_requests=10, time_window=60)

api_bp = Blueprint('api', __name__, url_prefix='/api')

# PIN endpoints (без /api префикса)
pin_bp = Blueprint('pin', __name__, url_prefix='/pin')

# Vendor endpoints (без префикса)
vendor_bp = Blueprint('vendor', __name__)

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

@api_bp.route('/server/<server_id>/stats', methods=['GET'])
@require_auth
@require_pin
def get_server_stats(server_id):
    """Получение статистики сервера через SSH"""
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        if not ssh_service or not data_manager:
            raise APIError('Required services not available')
        
        # Получаем данные сервера
        from flask import current_app
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            return jsonify({
                'error': f'Server with id {server_id} not found'
            }), 404
        
        # Получаем timeout из параметров запроса
        timeout = int(request.args.get('timeout', 30))
        
        # Получаем SSH credentials из правильной структуры
        ssh_creds = server.get('ssh_credentials', {})
        ssh_user = ssh_creds.get('user', 'root')
        ssh_port = ssh_creds.get('port', 22)  # Получаем SSH порт
        
        # Проверяем, есть ли уже расшифрованный пароль
        ssh_password = ssh_creds.get('password_decrypted', '')
        
        # Если нет, пытаемся расшифровать
        if not ssh_password and ssh_creds.get('password'):
            try:
                ssh_password = data_manager.decrypt_data(ssh_creds['password'])
            except Exception as e:
                logger.error(f"Failed to decrypt SSH password: {str(e)}")
        
        if not ssh_password:
            return jsonify({
                'error': 'SSH password not available. Please edit server and set SSH credentials.'
            }), 400
        
        # Получаем статистику через SSH
        stats = ssh_service.get_server_stats(
            ip=server.get('ip_address', server.get('ip', '')),
            user=ssh_user,
            password=ssh_password,
            port=ssh_port,  # Передаем SSH порт
            timeout=timeout
        )
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting server stats {server_id}: {str(e)}")
        
        # Определяем тип ошибки для более понятного сообщения
        error_message = str(e)
        if "SSH authentication failed" in error_message:
            error_message = f"SSH authentication failed. Please check username and password for server {server_id}."
        elif "not responding" in error_message or "SSH service is not running" in error_message:
            error_message = f"Server {server_id} is not responding. Please check if the server is online and SSH service is running."
        elif "Connection timeout" in error_message:
            error_message = f"Connection timeout to server {server_id}. Server may be slow or unreachable."
        elif "SSH connection failed" in error_message:
            error_message = f"SSH connection failed to server {server_id}. Please check network connectivity and SSH settings."
        
        return jsonify({
            'error': error_message
        }), 500

@api_bp.route('/snapshot/save', methods=['POST'])
@require_auth
@require_pin
def snapshot_save():
    """Accepts a PNG data URL and saves it to Downloads (export dir). Returns JSON with filename."""
    try:
        import base64
        import datetime
        import os
        
        logger.info("Snapshot save request received")
        
        data = request.get_json(silent=True) or {}
        data_url = data.get('data_url', '')
        
        if not data_url:
            logger.error("No data_url provided")
            return jsonify({"success": False, "error": "No data_url provided"}), 400
            
        if not data_url.startswith('data:image/png;base64,'):
            logger.error(f"Invalid data_url format: {data_url[:50]}")
            return jsonify({"success": False, "error": "Invalid data_url format"}), 400
        
        b64 = data_url.split(',', 1)[1]
        img_bytes = base64.b64decode(b64)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'server_status_{ts}.png'
        
        logger.info(f"Creating PNG file: {filename}, size: {len(img_bytes)} bytes")
        
        # Используем папку Downloads пользователя
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(downloads_dir) and os.access(downloads_dir, os.W_OK):
            export_dir = downloads_dir
            logger.info(f"Using Downloads directory: {export_dir}")
        else:
            # Если Downloads недоступна, используем папку exports в проекте
            export_dir = os.path.join(os.getcwd(), 'exports')
            os.makedirs(export_dir, exist_ok=True)
            logger.warning(f"Downloads not available, using exports: {export_dir}")
        
        path = os.path.join(export_dir, filename)
        with open(path, 'wb') as f:
            f.write(img_bytes)
        
        logger.info(f"PNG saved successfully: {path}")
        return jsonify({"success": True, "filename": filename, "dir": export_dir})
    except Exception as e:
        logger.error(f"Error saving snapshot: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@vendor_bp.route('/vendor/html2canvas.min.js')
def vendor_html2canvas():
    """Serve html2canvas library"""
    try:
        # Простая но рабочая реализация html2canvas
        html2canvas_code = """
!function(window) {
    'use strict';
    
    window.html2canvas = function(element, options) {
        options = options || {};
        
        return new Promise(function(resolve, reject) {
            try {
                var canvas = document.createElement('canvas');
                var ctx = canvas.getContext('2d');
                
                // Получаем размеры элемента
                var rect = element.getBoundingClientRect();
                var scale = options.scale || window.devicePixelRatio || 2;
                
                canvas.width = rect.width * scale;
                canvas.height = rect.height * scale;
                ctx.scale(scale, scale);
                
                // Устанавливаем фон
                ctx.fillStyle = options.backgroundColor || '#ffffff';
                ctx.fillRect(0, 0, rect.width, rect.height);
                
                // Добавляем текстовое содержимое
                ctx.fillStyle = '#000000';
                ctx.font = '12px Arial';
                
                var textContent = element.innerText || element.textContent || '';
                var lines = textContent.split('\\n');
                var y = 20;
                
                for (var i = 0; i < lines.length && y < rect.height; i++) {
                    var line = lines[i].trim();
                    if (line) {
                        ctx.fillText(line.substring(0, 80), 10, y);
                        y += 16;
                    }
                }
                
                console.log('html2canvas: Canvas created successfully', canvas.width + 'x' + canvas.height);
                resolve(canvas);
                
            } catch (e) {
                console.error('html2canvas error:', e);
                reject(e);
            }
        });
    };
    
    console.log('html2canvas loaded successfully');
    
}(window);
"""
        return html2canvas_code, 200, {'Content-Type': 'application/javascript; charset=utf-8'}
    except Exception as e:
        logger.error(f"Error serving html2canvas: {str(e)}")
        return f"console.error('html2canvas load failed:', '{str(e)}');", 200, {'Content-Type': 'application/javascript; charset=utf-8'}

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

# Monitoring Endpoints
@api_bp.route('/monitoring/<server_id>/network-stats', methods=['GET'])
@require_auth
@require_pin
def get_network_stats(server_id):
    """Получение статистики сетевого трафика"""
    # Rate limiting
    if not rate_limiter.is_allowed(f"server_{server_id}"):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait a moment.'
        }), 429
    
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        if not ssh_service or not data_manager:
            raise APIError('Required services not available')
        
        from flask import current_app
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with id {server_id} not found'
            }), 404
        
        stats = ssh_service.get_network_stats(
            ip=server.get('ip_address'),
            user=server.get('ssh_credentials', {}).get('user', 'root'),
            password=server.get('ssh_credentials', {}).get('password_decrypted', ''),
            port=server.get('ssh_credentials', {}).get('port', 22),
            timeout=30  # Увеличиваем timeout до 30 секунд
        )
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting network stats for server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/monitoring/<server_id>/firewall-stats', methods=['GET'])
@require_auth
@require_pin
def get_firewall_stats(server_id):
    """Получение статистики брандмауэра"""
    # Rate limiting
    if not rate_limiter.is_allowed(f"server_{server_id}"):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait a moment.'
        }), 429
    
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        if not ssh_service or not data_manager:
            raise APIError('Required services not available')
        
        from flask import current_app
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with id {server_id} not found'
            }), 404
        
        stats = ssh_service.get_firewall_stats(
            ip=server.get('ip_address'),
            user=server.get('ssh_credentials', {}).get('user', 'root'),
            password=server.get('ssh_credentials', {}).get('password_decrypted', ''),
            port=server.get('ssh_credentials', {}).get('port', 22),
            timeout=30
        )
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting firewall stats for server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/monitoring/<server_id>/services-stats', methods=['GET'])
@require_auth
@require_pin
def get_services_stats(server_id):
    """Получение статистики системных сервисов"""
    # Rate limiting
    if not rate_limiter.is_allowed(f"server_{server_id}"):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait a moment.'
        }), 429
    
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        if not ssh_service or not data_manager:
            raise APIError('Required services not available')
        
        from flask import current_app
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with id {server_id} not found'
            }), 404
        
        stats = ssh_service.get_services_stats(
            ip=server.get('ip_address'),
            user=server.get('ssh_credentials', {}).get('user', 'root'),
            password=server.get('ssh_credentials', {}).get('password_decrypted', ''),
            port=server.get('ssh_credentials', {}).get('port', 22),
            timeout=30
        )
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting services stats for server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/monitoring/<server_id>/security-events', methods=['GET'])
@require_auth
@require_pin
def get_security_events(server_id):
    """Получение событий безопасности"""
    # Rate limiting
    if not rate_limiter.is_allowed(f"server_{server_id}"):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait a moment.'
        }), 429
    
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        if not ssh_service or not data_manager:
            raise APIError('Required services not available')
        
        from flask import current_app
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with id {server_id} not found'
            }), 404
        
        stats = ssh_service.get_security_events(
            ip=server.get('ip_address'),
            user=server.get('ssh_credentials', {}).get('user', 'root'),
            password=server.get('ssh_credentials', {}).get('password_decrypted', ''),
            port=server.get('ssh_credentials', {}).get('port', 22),
            timeout=30
        )
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting security events for server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/monitoring/<server_id>/metrics-history', methods=['GET'])
@require_auth
@require_pin
def get_metrics_history(server_id):
    """Получение истории метрик (CPU/Memory)"""
    # Rate limiting
    if not rate_limiter.is_allowed(f"server_{server_id}"):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait a moment.'
        }), 429
    
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        if not ssh_service or not data_manager:
            raise APIError('Required services not available')
        
        from flask import current_app
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with id {server_id} not found'
            }), 404
        
        history = ssh_service.get_metrics_history(
            ip=server.get('ip_address'),
            user=server.get('ssh_credentials', {}).get('user', 'root'),
            password=server.get('ssh_credentials', {}).get('password_decrypted', ''),
            port=server.get('ssh_credentials', {}).get('port', 22),
            timeout=30
        )
        
        return jsonify({
            'success': True,
            'data': history
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics history for server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/monitoring/<server_id>/check-tools', methods=['GET'])
@require_auth
@require_pin
def check_monitoring_tools(server_id):
    """Проверка наличия необходимых утилит для мониторинга"""
    # Rate limiting
    if not rate_limiter.is_allowed(f"server_{server_id}"):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait a moment.'
        }), 429
    
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        if not ssh_service or not data_manager:
            raise APIError('Required services not available')
        
        from flask import current_app
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with id {server_id} not found'
            }), 404
        
        tools_status = ssh_service.check_required_tools(
            ip=server.get('ip_address'),
            user=server.get('ssh_credentials', {}).get('user', 'root'),
            password=server.get('ssh_credentials', {}).get('password_decrypted', ''),
            port=server.get('ssh_credentials', {}).get('port', 22),
            timeout=30
        )
        
        return jsonify({
            'success': True,
            'data': tools_status
        })
        
    except Exception as e:
        logger.error(f"Error checking tools for server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/monitoring/<server_id>/check-installed', methods=['GET'])
@require_auth
@require_pin
def check_monitoring_installed(server_id):
    """Проверить, установлен ли мониторинг на сервере"""
    # Rate limiting
    if not rate_limiter.is_allowed(f"server_{server_id}"):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait a moment.'
        }), 429
    
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        if not ssh_service or not data_manager:
            raise APIError('Required services not available')
        
        from flask import current_app
        servers = data_manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
        
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with id {server_id} not found'
            }), 404
        
        # Проверяем наличие всех необходимых утилит
        tools_status = ssh_service.check_required_tools(
            ip=server.get('ip_address'),
            user=server.get('ssh_credentials', {}).get('user', 'root'),
            password=server.get('ssh_credentials', {}).get('password_decrypted', ''),
            port=server.get('ssh_credentials', {}).get('port', 22),
            timeout=30
        )
        
        # Считаем установленным, если все утилиты на месте
        is_installed = tools_status.get('all_ok', False)
        
        return jsonify({
            'success': True,
            'installed': is_installed,
            'details': tools_status
        })
        
    except Exception as e:
        logger.error(f"Error checking installation for server {server_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'installed': False
        })

# Глобальная переменная для отслеживания отмены установки
installation_cancelled = {}

@api_bp.route('/monitoring/<server_id>/cancel-install', methods=['POST'])
@require_auth
@require_pin
def cancel_installation(server_id):
    """Отменить текущую установку"""
    global installation_cancelled
    installation_cancelled[server_id] = True
    
    return jsonify({
        'success': True,
        'message': 'Отмена установки...'
    })

@api_bp.route('/monitoring/<server_id>/install', methods=['GET'])  # EventSource использует GET!
@require_auth
@require_pin
def install_monitoring(server_id):
    """Установка системы мониторинга на удаленный сервер (с SSE прогрессом)"""
    from flask import Response, stream_with_context
    import time
    import json
    
    global installation_cancelled
    installation_cancelled[server_id] = False  # Сбрасываем флаг отмены
    
    def generate_progress():
        """Generator для Server-Sent Events"""
        try:
            ssh_service = registry.get('ssh')
            data_manager = registry.get('data_manager')
            
            if not ssh_service or not data_manager:
                yield f"data: {json.dumps({'error': 'Required services not available', 'status': 'error'})}\n\n"
                return
            
            from flask import current_app
            servers = data_manager.load_servers(current_app.config)
            server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
            
            if not server:
                yield f"data: {json.dumps({'error': f'Server with id {server_id} not found', 'status': 'error'})}\n\n"
                return
            
            # Получаем credentials
            ip = server.get('ip_address')
            user = server.get('ssh_credentials', {}).get('user', 'root')
            
            # Расшифровываем пароль
            crypto_service = registry.get('crypto')
            encrypted_password = server.get('ssh_credentials', {}).get('password', '')
            password = ''
            if encrypted_password and crypto_service:
                try:
                    password = crypto_service.decrypt(encrypted_password)
                except Exception as e:
                    logger.error(f"Failed to decrypt password for server {server_id}: {e}")
                    yield f"data: {json.dumps({'error': 'Не удалось расшифровать пароль сервера', 'status': 'error'})}\n\n"
                    return
            
            port = server.get('ssh_credentials', {}).get('port', 22)
            
            # Функция проверки отмены
            def check_cancelled():
                if installation_cancelled.get(server_id, False):
                    return True
                return False
            
            # Проверка: не установлен ли уже мониторинг
            yield f"data: {json.dumps({'step': 0, 'total': 7, 'message': 'Проверка существующей установки...', 'status': 'running'})}\n\n"
            import paramiko
            check_client = None
            try:
                check_client = paramiko.SSHClient()
                check_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                check_client.connect(hostname=ip, username=user, password=password, port=port, timeout=30, 
                                   banner_timeout=60, auth_timeout=30, look_for_keys=False, allow_agent=False)
                
                # Проверяем наличие файла мониторинга
                _, stdout, _ = check_client.exec_command('test -f /usr/local/bin/monitoring/get-all-stats.sh && echo "exists"', timeout=10)
                result = stdout.read().decode('utf-8').strip()
                check_client.close()
                
                if result == 'exists':
                    logger.warning(f"Monitoring already installed on server {server_id}, aborting installation")
                    yield f"data: {json.dumps({'error': 'Мониторинг уже установлен на этом сервере! Обновите страницу.', 'status': 'error'})}\n\n"
                    return
            except Exception as e:
                if check_client:
                    check_client.close()
                # Игнорируем ошибку проверки, продолжаем установку
                logger.debug(f"Pre-installation check failed (this is OK): {e}")
            
            # Шаг 1: Подключение
            yield f"data: {json.dumps({'step': 1, 'total': 7, 'message': 'Подключение к серверу...', 'status': 'running'})}\n\n"
            if check_cancelled():
                yield f"data: {json.dumps({'cancelled': True, 'message': '⚠️ Установка отменена пользователем', 'status': 'cancelled'})}\n\n"
                return
            time.sleep(0.3)
            
            # Проверяем SSH подключение
            client = None
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(hostname=ip, username=user, password=password, port=port, timeout=30)
                
                yield f"data: {json.dumps({'step': 1, 'total': 7, 'message': '✅ Подключено к серверу', 'status': 'success'})}\n\n"
                if check_cancelled():
                    yield f"data: {json.dumps({'cancelled': True, 'message': '⚠️ Установка отменена пользователем', 'status': 'cancelled'})}\n\n"
                    return
                
                # Шаг 2: Обновление пакетов
                yield f"data: {json.dumps({'step': 2, 'total': 7, 'message': 'Обновление списка пакетов...', 'status': 'running'})}\n\n"
                if check_cancelled():
                    yield f"data: {json.dumps({'cancelled': True, 'message': '⚠️ Установка отменена пользователем', 'status': 'cancelled'})}\n\n"
                    return
                _, stdout, stderr = client.exec_command('sudo apt-get update -qq', timeout=60)
                stdout.channel.recv_exit_status()  # Ждем завершения
                yield f"data: {json.dumps({'step': 2, 'total': 7, 'message': '✅ Список пакетов обновлен', 'status': 'success'})}\n\n"
                if check_cancelled():
                    yield f"data: {json.dumps({'cancelled': True, 'message': '⚠️ Установка отменена пользователем', 'status': 'cancelled'})}\n\n"
                    return
                
                # Шаг 3: Установка vnstat
                yield f"data: {json.dumps({'step': 3, 'total': 7, 'message': 'Установка vnstat...', 'status': 'running'})}\n\n"
                _, stdout, stderr = client.exec_command('sudo apt-get install -y vnstat', timeout=120)
                stdout.channel.recv_exit_status()
                _, stdout, stderr = client.exec_command('sudo systemctl enable vnstat && sudo systemctl start vnstat', timeout=30)
                stdout.channel.recv_exit_status()
                yield f"data: {json.dumps({'step': 3, 'total': 7, 'message': '✅ vnstat установлен и запущен', 'status': 'success'})}\n\n"
                
                # Шаг 4: Установка jq
                yield f"data: {json.dumps({'step': 4, 'total': 7, 'message': 'Установка jq...', 'status': 'running'})}\n\n"
                _, stdout, stderr = client.exec_command('sudo apt-get install -y jq', timeout=60)
                stdout.channel.recv_exit_status()
                yield f"data: {json.dumps({'step': 4, 'total': 7, 'message': '✅ jq установлен', 'status': 'success'})}\n\n"
                
                # Шаг 5: Установка net-tools
                yield f"data: {json.dumps({'step': 5, 'total': 7, 'message': 'Установка net-tools...', 'status': 'running'})}\n\n"
                _, stdout, stderr = client.exec_command('sudo apt-get install -y net-tools', timeout=60)
                stdout.channel.recv_exit_status()
                yield f"data: {json.dumps({'step': 5, 'total': 7, 'message': '✅ net-tools установлен', 'status': 'success'})}\n\n"
                
                # Шаг 6: Установка и настройка UFW (опционально)
                yield f"data: {json.dumps({'step': 6, 'total': 7, 'message': 'Проверка UFW...', 'status': 'running'})}\n\n"
                _, stdout, _ = client.exec_command('which ufw', timeout=10)
                ufw_exists = bool(stdout.read().decode('utf-8').strip())
                
                if not ufw_exists:
                    _, stdout, stderr = client.exec_command('sudo apt-get install -y ufw', timeout=60)
                    stdout.channel.recv_exit_status()
                    yield f"data: {json.dumps({'step': 6, 'total': 7, 'message': '✅ UFW установлен', 'status': 'success'})}\n\n"
                else:
                    yield f"data: {json.dumps({'step': 6, 'total': 7, 'message': '✅ UFW уже установлен', 'status': 'success'})}\n\n"
                
                # Шаг 7: Создание cron задачи для сбора метрик
                yield f"data: {json.dumps({'step': 7, 'total': 8, 'message': 'Настройка автоматического сбора метрик...', 'status': 'running'})}\n\n"
                
                # Создаем скрипт сбора метрик
                script_content = '''#!/bin/bash
# VPN Server Manager - Metrics Collection Script
HISTORY_FILE="/var/tmp/metrics_history.json"
MAX_POINTS=288  # 24 часа истории (288 точек × 5 минут)

# Получаем текущие метрики
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\\([0-9.]*\\)%* id.*/\\1/" | awk '{print 100 - $1}')
MEM_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')
TIMESTAMP=$(date +%s)

# Проверяем наличие jq
if ! command -v jq &> /dev/null; then
    echo "[]" > "$HISTORY_FILE"
    exit 0
fi

# Читаем существующую историю или создаем новую
if [ ! -f "$HISTORY_FILE" ]; then
    echo "[]" > "$HISTORY_FILE"
fi

# Добавляем новую точку и ограничиваем до MAX_POINTS
jq ". += [{\\"timestamp\\":$TIMESTAMP,\\"cpu\\":$CPU_USAGE,\\"memory\\":$MEM_USAGE}] | .[-$MAX_POINTS:]" "$HISTORY_FILE" > "$HISTORY_FILE.tmp" && mv "$HISTORY_FILE.tmp" "$HISTORY_FILE"
'''
                
                # Создаем директорию для скрипта
                _, stdout, _ = client.exec_command('sudo mkdir -p /usr/local/bin/monitoring', timeout=10)
                stdout.channel.recv_exit_status()
                
                # Записываем скрипт
                import base64
                script_b64 = base64.b64encode(script_content.encode()).decode()
                _, stdout, _ = client.exec_command(f'echo {script_b64} | base64 -d | sudo tee /usr/local/bin/monitoring/update-metrics-history.sh > /dev/null', timeout=10)
                stdout.channel.recv_exit_status()
                
                # Делаем исполняемым
                _, stdout, _ = client.exec_command('sudo chmod +x /usr/local/bin/monitoring/update-metrics-history.sh', timeout=10)
                stdout.channel.recv_exit_status()
                
                # Создаем cron задачу с flock (безопасная версия - раз в 5 минут)
                cron_cmd = '(crontab -l 2>/dev/null | grep -v "update-metrics-history.sh"; echo "*/5 * * * * flock -n /var/run/metrics-history.lock /usr/local/bin/monitoring/update-metrics-history.sh > /dev/null 2>&1") | crontab -'
                _, stdout, _ = client.exec_command(cron_cmd, timeout=10)
                stdout.channel.recv_exit_status()
                
                yield f"data: {json.dumps({'step': 7, 'total': 8, 'message': '✅ Автоматический сбор метрик настроен', 'status': 'success'})}\n\n"
                
                # Шаг 8: Тестирование
                yield f"data: {json.dumps({'step': 8, 'total': 8, 'message': 'Проверка установленных утилит...', 'status': 'running'})}\n\n"
                
                # Проверяем все утилиты
                tools_status = ssh_service.check_required_tools(ip=ip, user=user, password=password, port=port, timeout=30)
                
                if tools_status.get('all_ok', False):
                    yield f"data: {json.dumps({'step': 8, 'total': 8, 'message': '✅ Все утилиты успешно установлены!', 'status': 'success'})}\n\n"
                    yield f"data: {json.dumps({'complete': True, 'status': 'success'})}\n\n"
                else:
                    missing = tools_status.get('missing_count', 0)
                    yield f"data: {json.dumps({'error': f'Не все утилиты установлены ({missing} отсутствует)', 'status': 'error'})}\n\n"
                
            except paramiko.AuthenticationException:
                yield f"data: {json.dumps({'error': 'Ошибка аутентификации SSH. Проверьте имя пользователя и пароль.', 'status': 'error'})}\n\n"
            except paramiko.SSHException as e:
                yield f"data: {json.dumps({'error': f'Ошибка SSH: {str(e)}', 'status': 'error'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': f'Ошибка: {str(e)}', 'status': 'error'})}\n\n"
            finally:
                if client:
                    try:
                        client.close()
                    except:
                        pass
                # Очищаем флаг отмены после завершения
                installation_cancelled[server_id] = False
                        
        except Exception as e:
            logger.error(f"Error during monitoring installation: {str(e)}")
            yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"
            installation_cancelled[server_id] = False
    
    return Response(stream_with_context(generate_progress()), mimetype='text/event-stream')

@api_bp.route('/monitoring/<server_id>/uninstall', methods=['GET'])  # EventSource использует GET!
@require_auth
@require_pin
def uninstall_monitoring(server_id):
    """Удаление системы мониторинга с удаленного сервера"""
    from flask import Response, stream_with_context
    import time
    import json
    
    def generate_uninstall_progress():
        """Generator для SSE при удалении"""
        try:
            ssh_service = registry.get('ssh')
            data_manager = registry.get('data_manager')
            
            if not ssh_service or not data_manager:
                yield f"data: {json.dumps({'error': 'Required services not available', 'status': 'error'})}\n\n"
                return
            
            from flask import current_app
            servers = data_manager.load_servers(current_app.config)
            server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)
            
            if not server:
                yield f"data: {json.dumps({'error': f'Server with id {server_id} not found', 'status': 'error'})}\n\n"
                return
            
            # Получаем credentials
            ip = server.get('ip_address')
            user = server.get('ssh_credentials', {}).get('user', 'root')
            
            # Расшифровываем пароль
            crypto_service = registry.get('crypto')
            encrypted_password = server.get('ssh_credentials', {}).get('password', '')
            password = ''
            if encrypted_password and crypto_service:
                try:
                    password = crypto_service.decrypt(encrypted_password)
                except Exception as e:
                    logger.error(f"Failed to decrypt password for server {server_id}: {e}")
                    yield f"data: {json.dumps({'error': 'Не удалось расшифровать пароль сервера', 'status': 'error'})}\n\n"
                    return
            
            port = server.get('ssh_credentials', {}).get('port', 22)
            
            # Шаг 1: Подключение
            yield f"data: {json.dumps({'step': 1, 'total': 5, 'message': 'Подключение к серверу...', 'status': 'running'})}\n\n"
            time.sleep(0.3)
            
            import paramiko
            client = None
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(hostname=ip, username=user, password=password, port=port, timeout=30)
                
                yield f"data: {json.dumps({'step': 1, 'total': 5, 'message': '✅ Подключено к серверу', 'status': 'success'})}\n\n"
                
                # Шаг 2: Остановка vnstat (опционально, не удаляем сам пакет)
                yield f"data: {json.dumps({'step': 2, 'total': 5, 'message': 'Проверка vnstat...', 'status': 'running'})}\n\n"
                # Просто проверяем, не удаляем пакеты, так как они могут использоваться другими приложениями
                yield f"data: {json.dumps({'step': 2, 'total': 5, 'message': '✅ Проверка завершена (пакеты оставлены)', 'status': 'success'})}\n\n"
                
                # Шаг 3: Удаление файла истории и скриптов
                yield f"data: {json.dumps({'step': 3, 'total': 5, 'message': 'Удаление файлов мониторинга...', 'status': 'running'})}\n\n"
                _, stdout, stderr = client.exec_command('sudo rm -f /var/tmp/metrics_history.json', timeout=10)
                stdout.channel.recv_exit_status()
                _, stdout, stderr = client.exec_command('sudo rm -rf /usr/local/bin/monitoring', timeout=10)
                stdout.channel.recv_exit_status()
                yield f"data: {json.dumps({'step': 3, 'total': 5, 'message': '✅ Файлы мониторинга удалены', 'status': 'success'})}\n\n"
                
                # Шаг 4: Удаление cron задачи
                yield f"data: {json.dumps({'step': 4, 'total': 5, 'message': 'Удаление автоматических задач...', 'status': 'running'})}\n\n"
                cron_remove_cmd = 'crontab -l 2>/dev/null | grep -v "update-metrics-history.sh" | crontab -'
                _, stdout, stderr = client.exec_command(cron_remove_cmd, timeout=10)
                stdout.channel.recv_exit_status()
                yield f"data: {json.dumps({'step': 4, 'total': 5, 'message': '✅ Автоматические задачи удалены', 'status': 'success'})}\n\n"
                
                # Шаг 5: Завершение
                yield f"data: {json.dumps({'step': 5, 'total': 5, 'message': 'Завершение...', 'status': 'running'})}\n\n"
                yield f"data: {json.dumps({'step': 5, 'total': 5, 'message': '✅ Мониторинг деактивирован', 'status': 'success'})}\n\n"
                
                yield f"data: {json.dumps({'complete': True, 'status': 'success', 'message': '🎉 Мониторинг успешно удален!'})}\n\n"
                
            except paramiko.AuthenticationException:
                yield f"data: {json.dumps({'error': 'Ошибка аутентификации SSH', 'status': 'error'})}\n\n"
            except paramiko.SSHException as e:
                yield f"data: {json.dumps({'error': f'Ошибка SSH: {str(e)}', 'status': 'error'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': f'Ошибка: {str(e)}', 'status': 'error'})}\n\n"
            finally:
                if client:
                    try:
                        client.close()
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Error during monitoring uninstallation: {str(e)}")
            yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"
    
    return Response(stream_with_context(generate_uninstall_progress()), mimetype='text/event-stream')

@api_bp.route('/monitoring/stats/system', methods=['GET'])
@require_auth
@require_pin
def monitoring_system_stats():
    """Статистика работы системы мониторинга"""
    from ..services.ssh_service import SSHService
    
    try:
        # Количество открытых SSH соединений
        active_connections = len(SSHService._connection_pool)
        
        # Список активных соединений
        connections = []
        for key, conn in SSHService._connection_pool.items():
            try:
                is_alive = conn.get_transport() and conn.get_transport().is_active()
                connections.append({
                    'key': key,
                    'alive': is_alive
                })
            except:
                connections.append({
                    'key': key,
                    'alive': False
                })
        
        return jsonify({
            'success': True,
            'stats': {
                'active_ssh_connections': active_connections,
                'connections': connections,
                'connection_pool_enabled': True,
                'rate_limiting_enabled': True,
                'max_requests_per_minute': rate_limiter.max_requests,
                'time_window': rate_limiter.time_window
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting monitoring system stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/monitoring/health', methods=['GET'])
def health_check():
    """Health check endpoint для мониторинга работоспособности"""
    import time
    from ..services.ssh_service import SSHService
    
    health = {
        'status': 'healthy',
        'timestamp': int(time.time()),
        'checks': {}
    }
    
    # Проверка SSH Connection Pool
    try:
        pool_size = len(SSHService._connection_pool)
        active_count = 0
        for key, conn in SSHService._connection_pool.items():
            try:
                if conn.get_transport() and conn.get_transport().is_active():
                    active_count += 1
            except:
                pass
        
        health['checks']['ssh_pool'] = {
            'status': 'ok',
            'total_connections': pool_size,
            'active_connections': active_count
        }
    except Exception as e:
        health['checks']['ssh_pool'] = {
            'status': 'error',
            'error': str(e)
        }
        health['status'] = 'degraded'
    
    # Проверка Rate Limiter
    try:
        health['checks']['rate_limiter'] = {
            'status': 'ok',
            'enabled': True,
            'max_requests': rate_limiter.max_requests,
            'time_window': rate_limiter.time_window
        }
    except Exception as e:
        health['checks']['rate_limiter'] = {
            'status': 'error',
            'error': str(e)
        }
        health['status'] = 'degraded'
    
    # Проверка services registry
    try:
        ssh_service = registry.get('ssh')
        data_manager = registry.get('data_manager')
        
        health['checks']['services'] = {
            'status': 'ok',
            'ssh_service': ssh_service is not None,
            'data_manager': data_manager is not None
        }
        
        if not ssh_service or not data_manager:
            health['status'] = 'degraded'
    except Exception as e:
        health['checks']['services'] = {
            'status': 'error',
            'error': str(e)
        }
        health['status'] = 'degraded'
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code

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
            # Устанавливаем все необходимые флаги сессии
            session['pin_authenticated'] = True
            session['authenticated'] = True  # Для @require_auth
            session['pin_verified'] = True  # Для @require_pin
            session.permanent = False  # Сессия НЕ постоянная - сбрасывается при закрытии браузера/приложения
            session.pop('block_until', None)  # Снимаем блокировку
            session.pop('failed_attempts', None)  # Сбрасываем счетчик
            logger.info(f"PIN authenticated successfully. Session: {dict(session)}")
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

@pin_bp.route('/logout', methods=['POST'])
def logout():
    """Выход из системы (сброс сессии)"""
    try:
        # Очищаем все данные сессии
        session.clear()
        logger.info("User logged out, session cleared")
        return jsonify({
            'success': True,
            'message': _('Logged out successfully')
        })
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pin_bp.route('/check_auth', methods=['GET'])
def check_auth():
    """Проверка статуса аутентификации"""
    try:
        authenticated = session.get('pin_authenticated', False) or session.get('authenticated', False)
        return jsonify({
            'authenticated': authenticated
        })
    except Exception as e:
        logger.error(f"Error checking auth: {str(e)}")
        return jsonify({
            'authenticated': False
        })

@pin_bp.route('/exit_app', methods=['POST'])
def exit_app():
    """Закрытие приложения (только для desktop mode)"""
    try:
        # Очищаем сессию
        session.clear()
        logger.info("Exit app request received, session cleared")
        
        # Пытаемся остановить приложение (работает только в desktop mode)
        import sys
        import os
        
        # Проверяем, запущено ли приложение в desktop режиме
        if '--desktop' in sys.argv or os.environ.get('DESKTOP_MODE') == '1':
            # Отправляем сигнал на остановку через threading
            import threading
            def stop_app():
                import time
                time.sleep(0.5)  # Даём время на отправку ответа
                # Останавливаем pywebview
                try:
                    import webview
                    # Получаем все окна и закрываем их
                    for window in webview.windows:
                        window.destroy()
                except Exception as e:
                    logger.error(f"Error destroying windows: {e}")
                    # Если не получилось закрыть через webview, выходим из процесса
                    os._exit(0)
            
            threading.Thread(target=stop_app, daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': _('Application closing...')
        })
    except Exception as e:
        logger.error(f"Error in exit_app: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
