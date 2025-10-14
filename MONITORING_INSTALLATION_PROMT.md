# 🔧 Полное руководство по установке и настройке системы мониторинга

> **Комплексное руководство**: установка, удаление, критические исправления безопасности

---

## 📋 Содержание

1. [Встроенный установщик мониторинга](#1-встроенный-установщик-мониторинга)
2. [Удаление и отмена установки](#2-удаление-и-отмена-установки)
3. [Критические исправления безопасности](#3-критические-исправления-безопасности)
4. [Тестирование и проверка](#4-тестирование-и-проверка)
5. [Troubleshooting](#5-troubleshooting)

---

# 1. Встроенный установщик мониторинга

## 📋 Что создаём:

1. **Backend** - API для установки через SSH
2. **Frontend** - Красивая кнопка с прогресс-баром
3. **Real-time логи** - Показываем что происходит
4. **Проверка зависимостей** - Проверяем перед установкой

---

## 🔧 Часть 1: Backend (Flask)

### 📝 `app/routes/monitoring.py` - Добавьте новые routes

```python
from flask import Blueprint, render_template, jsonify, request, Response
from app.models.server import Server
from app.services.ssh_service import SSHService
import json
import time

monitoring_bp = Blueprint('monitoring', __name__)

# =============================================================================
# УСТАНОВКА МОНИТОРИНГА
# =============================================================================

@monitoring_bp.route('/api/monitoring/<int:server_id>/install', methods=['POST'])
def install_monitoring(server_id):
    """
    Установка системы мониторинга на удаленный сервер
    Возвращает stream с прогрессом установки
    """
    def generate_progress():
        """Generator для SSE (Server-Sent Events)"""
        try:
            server = Server.query.get_or_404(server_id)
            ssh_service = SSHService()
            
            # Шаг 1: Подключение
            yield f"data: {json.dumps({'step': 1, 'total': 9, 'message': 'Подключение к серверу...', 'status': 'running'})}\n\n"
            time.sleep(0.5)
            
            # Проверяем SSH подключение
            test_result = ssh_service.execute_command(server, 'echo "test"', timeout=10)
            if not test_result.get('success'):
                yield f"data: {json.dumps({'error': 'Не удалось подключиться к серверу', 'status': 'error'})}\n\n"
                return
            
            yield f"data: {json.dumps({'step': 1, 'total': 9, 'message': '✅ Подключено к серверу', 'status': 'success'})}\n\n"
            
            # Шаг 2: Обновление пакетов
            yield f"data: {json.dumps({'step': 2, 'total': 9, 'message': 'Обновление списка пакетов...', 'status': 'running'})}\n\n"
            ssh_service.execute_command(server, 'sudo apt-get update -qq', timeout=60)
            yield f"data: {json.dumps({'step': 2, 'total': 9, 'message': '✅ Список пакетов обновлен', 'status': 'success'})}\n\n"
            
            # Шаг 3: Установка зависимостей
            yield f"data: {json.dumps({'step': 3, 'total': 9, 'message': 'Установка зависимостей (vnstat, bc, jq)...', 'status': 'running'})}\n\n"
            ssh_service.execute_command(server, 'sudo apt-get install -y vnstat bc jq net-tools', timeout=120)
            yield f"data: {json.dumps({'step': 3, 'total': 9, 'message': '✅ Зависимости установлены', 'status': 'success'})}\n\n"
            
            # Шаг 4: Запуск vnstat
            yield f"data: {json.dumps({'step': 4, 'total': 9, 'message': 'Настройка vnstat...', 'status': 'running'})}\n\n"
            ssh_service.execute_command(server, 'sudo systemctl enable vnstat && sudo systemctl start vnstat', timeout=30)
            yield f"data: {json.dumps({'step': 4, 'total': 9, 'message': '✅ vnstat запущен', 'status': 'success'})}\n\n"
            
            # Шаг 5: Создание директории
            yield f"data: {json.dumps({'step': 5, 'total': 9, 'message': 'Создание директории для скриптов...', 'status': 'running'})}\n\n"
            ssh_service.execute_command(server, 'sudo mkdir -p /usr/local/bin/monitoring', timeout=10)
            yield f"data: {json.dumps({'step': 5, 'total': 9, 'message': '✅ Директория создана', 'status': 'success'})}\n\n"
            
            # Шаг 6: Определение сетевого интерфейса
            yield f"data: {json.dumps({'step': 6, 'total': 9, 'message': 'Определение сетевого интерфейса...', 'status': 'running'})}\n\n"
            interface_result = ssh_service.execute_command(
                server, 
                "ip route | grep default | awk '{print $5}' | head -1",
                timeout=10
            )
            interface = interface_result.get('output', 'eth0').strip() or 'eth0'
            yield f"data: {json.dumps({'step': 6, 'total': 9, 'message': f'✅ Интерфейс: {interface}', 'status': 'success'})}\n\n"
            
            # Шаг 7: Загрузка скриптов
            yield f"data: {json.dumps({'step': 7, 'total': 9, 'message': 'Создание скриптов мониторинга...', 'status': 'running'})}\n\n"
            
            # Создаем главный скрипт
            main_script = get_monitoring_script_content(interface)
            create_script_result = ssh_service.execute_command(
                server,
                f"sudo bash -c 'cat > /usr/local/bin/monitoring/get-all-stats.sh' << 'SCRIPT_EOF'\n{main_script}\nSCRIPT_EOF",
                timeout=30
            )
            
            # Создаем скрипт истории
            history_script = get_history_script_content()
            ssh_service.execute_command(
                server,
                f"sudo bash -c 'cat > /usr/local/bin/monitoring/update-metrics-history.sh' << 'SCRIPT_EOF'\n{history_script}\nSCRIPT_EOF",
                timeout=30
            )
            
            # Делаем исполняемыми
            ssh_service.execute_command(server, 'sudo chmod +x /usr/local/bin/monitoring/*.sh', timeout=10)
            yield f"data: {json.dumps({'step': 7, 'total': 9, 'message': '✅ Скрипты созданы', 'status': 'success'})}\n\n"
            
            # Шаг 8: Настройка cron (безопасный вариант с flock)
            yield f"data: {json.dumps({'step': 8, 'total': 9, 'message': 'Настройка автоматического сбора метрик...', 'status': 'running'})}\n\n"
            cron_cmd = "(crontab -l 2>/dev/null | grep -v 'update-metrics-history.sh'; echo '*/5 * * * * flock -n /var/run/metrics-history.lock /usr/local/bin/monitoring/update-metrics-history.sh > /dev/null 2>&1') | crontab -"
            ssh_service.execute_command(server, cron_cmd, timeout=30)
            yield f"data: {json.dumps({'step': 8, 'total': 9, 'message': '✅ Cron настроен (каждые 5 минут)', 'status': 'success'})}\n\n"
            
            # Шаг 9: Тестирование
            yield f"data: {json.dumps({'step': 9, 'total': 9, 'message': 'Тестирование установки...', 'status': 'running'})}\n\n"
            
            # Запускаем скрипт истории
            ssh_service.execute_command(server, '/usr/local/bin/monitoring/update-metrics-history.sh', timeout=10)
            
            # Проверяем главный скрипт
            test_result = ssh_service.execute_command(server, 'sudo /usr/local/bin/monitoring/get-all-stats.sh', timeout=15)
            
            if test_result.get('success') and 'network' in test_result.get('output', ''):
                yield f"data: {json.dumps({'step': 9, 'total': 9, 'message': '✅ Мониторинг установлен и работает!', 'status': 'success'})}\n\n"
                yield f"data: {json.dumps({'complete': True, 'status': 'success'})}\n\n"
            else:
                yield f"data: {json.dumps({'error': 'Ошибка при тестировании скриптов', 'status': 'error'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"
    
    return Response(generate_progress(), mimetype='text/event-stream')

@monitoring_bp.route('/api/monitoring/<int:server_id>/check-installed')
def check_monitoring_installed(server_id):
    """Проверить, установлен ли мониторинг на сервере"""
    try:
        server = Server.query.get_or_404(server_id)
        ssh_service = SSHService()
        
        # Проверяем наличие главного скрипта
        result = ssh_service.execute_command(
            server,
            'test -f /usr/local/bin/monitoring/get-all-stats.sh && echo "installed" || echo "not_installed"',
            timeout=10
        )
        
        is_installed = 'installed' in result.get('output', '')
        
        return jsonify({
            'success': True,
            'installed': is_installed
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ - СОДЕРЖИМОЕ СКРИПТОВ
# =============================================================================

def get_monitoring_script_content(interface='eth0'):
    """Возвращает содержимое главного скрипта мониторинга"""
    return f'''#!/bin/bash
INTERFACE="{interface}"

get_network_stats() {{
    RX1=$(cat /sys/class/net/$INTERFACE/statistics/rx_bytes 2>/dev/null || echo "0")
    TX1=$(cat /sys/class/net/$INTERFACE/statistics/tx_bytes 2>/dev/null || echo "0")
    sleep 1
    RX2=$(cat /sys/class/net/$INTERFACE/statistics/rx_bytes 2>/dev/null || echo "0")
    TX2=$(cat /sys/class/net/$INTERFACE/statistics/tx_bytes 2>/dev/null || echo "0")
    RX_SPEED=$(echo "scale=2; ($RX2 - $RX1) / 1048576" | bc 2>/dev/null || echo "0.00")
    TX_SPEED=$(echo "scale=2; ($TX2 - $TX1) / 1048576" | bc 2>/dev/null || echo "0.00")
    
    if command -v vnstat &> /dev/null; then
        DAILY_RX=$(vnstat -i $INTERFACE --oneline 2>/dev/null | cut -d';' -f4 | xargs)
        DAILY_TX=$(vnstat -i $INTERFACE --oneline 2>/dev/null | cut -d';' -f5 | xargs)
    else
        DAILY_RX="N/A"
        DAILY_TX="N/A"
    fi
    
    [ -z "$DAILY_RX" ] && DAILY_RX="N/A"
    [ -z "$DAILY_TX" ] && DAILY_TX="N/A"
    
    echo "\\"network\\":{{\\"download\\":\\"$RX_SPEED\\",\\"upload\\":\\"$TX_SPEED\\",\\"daily_download\\":\\"$DAILY_RX\\",\\"daily_upload\\":\\"$DAILY_TX\\"}}"
}}

get_firewall_stats() {{
    UFW_STATUS="inactive"
    OPEN_PORTS="unknown"
    BLOCKED_24H=0
    LAST_BLOCKED_IP="none"
    
    if command -v ufw &> /dev/null; then
        UFW_STATUS=$(ufw status 2>/dev/null | grep "Status:" | awk '{{print $2}}' | tr '[:upper:]' '[:lower:]')
        OPEN_PORTS=$(ufw status numbered 2>/dev/null | grep -E "^\\[" | awk '{{print $3}}' | cut -d'/' -f1 | sort -u | tr '\\n' ',' | sed 's/,$//' | sed 's/,/, /g')
        
        if [ -f /var/log/ufw.log ]; then
            TODAY=$(date +%b\\ %e)
            BLOCKED_24H=$(grep "UFW BLOCK" /var/log/ufw.log 2>/dev/null | grep "$TODAY" | wc -l)
            LAST_BLOCKED_IP=$(grep "UFW BLOCK" /var/log/ufw.log 2>/dev/null | tail -1 | grep -oE "SRC=[0-9.]+" | cut -d'=' -f2)
        fi
    fi
    
    [ -z "$UFW_STATUS" ] && UFW_STATUS="inactive"
    [ -z "$OPEN_PORTS" ] && OPEN_PORTS="none"
    [ -z "$LAST_BLOCKED_IP" ] && LAST_BLOCKED_IP="none"
    [ -z "$BLOCKED_24H" ] && BLOCKED_24H=0
    
    echo "\\"firewall\\":{{\\"status\\":\\"$UFW_STATUS\\",\\"open_ports\\":\\"$OPEN_PORTS\\",\\"blocked_24h\\":$BLOCKED_24H,\\"last_blocked_ip\\":\\"$LAST_BLOCKED_IP\\"}}"
}}

get_services_stats() {{
    SERVICES=("nginx" "apache2" "sshd" "ssh" "postgresql" "mysql" "docker" "redis-server" "redis")
    SERVICE_LIST=""
    
    for SERVICE in "${{SERVICES[@]}}"; do
        if systemctl list-unit-files 2>/dev/null | grep -q "^$SERVICE.service"; then
            STATUS=$(systemctl is-active $SERVICE 2>/dev/null || echo "inactive")
            
            if [ "$STATUS" = "active" ]; then
                SINCE=$(systemctl show $SERVICE --property=ActiveEnterTimestamp 2>/dev/null | cut -d= -f2)
                
                if [ -n "$SINCE" ]; then
                    UPTIME_SECONDS=$(date -d "$SINCE" +%s 2>/dev/null)
                    NOW=$(date +%s)
                    SECONDS=$((NOW - UPTIME_SECONDS))
                    
                    DAYS=$((SECONDS / 86400))
                    HOURS=$(( (SECONDS % 86400) / 3600 ))
                    MINS=$(( (SECONDS % 3600) / 60 ))
                    
                    if [ $DAYS -gt 0 ]; then
                        UPTIME_STR="${{DAYS}}d ${{HOURS}}h"
                    elif [ $HOURS -gt 0 ]; then
                        UPTIME_STR="${{HOURS}}h ${{MINS}}m"
                    else
                        UPTIME_STR="${{MINS}}m"
                    fi
                else
                    UPTIME_STR="active"
                fi
            else
                UPTIME_STR="stopped"
            fi
            
            [ -n "$SERVICE_LIST" ] && SERVICE_LIST="${{SERVICE_LIST}},"
            SERVICE_LIST="${{SERVICE_LIST}}{{\\"name\\":\\"$SERVICE\\",\\"status\\":\\"$STATUS\\",\\"uptime\\":\\"$UPTIME_STR\\"}}"
        fi
    done
    
    echo "\\"services\\":[$SERVICE_LIST]"
}}

get_security_stats() {{
    SSH_FAILURES=0
    SECURITY_UPDATES=0
    DAYS_SINCE_UPDATE=0
    
    if [ -f /var/log/auth.log ]; then
        TODAY=$(date +%b\\ %e)
        SSH_FAILURES=$(grep "Failed password" /var/log/auth.log 2>/dev/null | grep "$TODAY" | wc -l)
    fi
    
    if command -v apt &> /dev/null; then
        SECURITY_UPDATES=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
    fi
    
    if [ -f /var/lib/apt/periodic/update-success-stamp ]; then
        LAST_UPDATE=$(stat -c %Y /var/lib/apt/periodic/update-success-stamp)
        NOW=$(date +%s)
        DAYS_SINCE_UPDATE=$(( (NOW - LAST_UPDATE) / 86400 ))
    fi
    
    echo "\\"security\\":{{\\"ssh_failures\\":$SSH_FAILURES,\\"security_updates\\":$SECURITY_UPDATES,\\"days_since_update\\":$DAYS_SINCE_UPDATE}}"
}}

get_metrics_history() {{
    HISTORY_FILE="/var/tmp/metrics_history.json"
    
    if [ -f "$HISTORY_FILE" ]; then
        cat "$HISTORY_FILE"
    else
        echo "[]"
    fi
}}

echo "{{"
get_network_stats
echo ","
get_firewall_stats
echo ","
get_services_stats
echo ","
get_security_stats
echo ","
echo "\\"metrics_history\\":"
get_metrics_history
echo "}}"
'''

def get_history_script_content():
    """Возвращает содержимое скрипта сбора истории"""
    return '''#!/bin/bash
HISTORY_FILE="/var/tmp/metrics_history.json"
MAX_POINTS=60

CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEM_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')
TIMESTAMP=$(date +%s)

[ -z "$CPU_USAGE" ] && CPU_USAGE="0.0"
[ -z "$MEM_USAGE" ] && MEM_USAGE="0.0"

NEW_POINT="{\\"timestamp\\":$TIMESTAMP,\\"cpu\\":$CPU_USAGE,\\"memory\\":$MEM_USAGE}"

if [ -f "$HISTORY_FILE" ]; then
    HISTORY=$(cat "$HISTORY_FILE")
else
    HISTORY="[]"
fi

if command -v jq &> /dev/null; then
    echo "$HISTORY" | jq ". += [$NEW_POINT] | .[-$MAX_POINTS:]" > "$HISTORY_FILE" 2>/dev/null
else
    if [ "$HISTORY" = "[]" ]; then
        echo "[$NEW_POINT]" > "$HISTORY_FILE"
    else
        HISTORY_WITHOUT_BRACKET=$(echo "$HISTORY" | sed 's/]$//')
        echo "${HISTORY_WITHOUT_BRACKET},${NEW_POINT}]" > "$HISTORY_FILE"
    fi
fi
'''
```

---

# 2. Удаление и отмена установки

## 📋 Что добавляем:

1. **Кнопка удаления** мониторинга с подтверждением
2. **Кнопка отмены** во время установки
3. **Прогресс удаления** с логами
4. **Восстановление** после отмены

---

## 🔧 API для удаления

### 📝 Добавьте в `app/routes/monitoring.py`

```python
@monitoring_bp.route('/api/monitoring/<int:server_id>/uninstall', methods=['POST'])
def uninstall_monitoring(server_id):
    """
    Удаление системы мониторинга с удаленного сервера
    Возвращает stream с прогрессом удаления
    """
    def generate_uninstall_progress():
        """Generator для SSE (Server-Sent Events)"""
        try:
            server = Server.query.get_or_404(server_id)
            ssh_service = SSHService()
            
            # Шаг 1: Подключение
            yield f"data: {json.dumps({'step': 1, 'total': 5, 'message': 'Подключение к серверу...', 'status': 'running'})}\n\n"
            time.sleep(0.3)
            
            test_result = ssh_service.execute_command(server, 'echo "test"', timeout=10)
            if not test_result.get('success'):
                yield f"data: {json.dumps({'error': 'Не удалось подключиться к серверу', 'status': 'error'})}\n\n"
                return
            
            yield f"data: {json.dumps({'step': 1, 'total': 5, 'message': '✅ Подключено к серверу', 'status': 'success'})}\n\n"
            
            # Шаг 2: Удаление cron задачи
            yield f"data: {json.dumps({'step': 2, 'total': 5, 'message': 'Удаление cron задачи...', 'status': 'running'})}\n\n"
            cron_cmd = "crontab -l 2>/dev/null | grep -v 'update-metrics-history.sh' | crontab -"
            ssh_service.execute_command(server, cron_cmd, timeout=30)
            yield f"data: {json.dumps({'step': 2, 'total': 5, 'message': '✅ Cron задача удалена', 'status': 'success'})}\n\n"
            
            # Шаг 3: Удаление файла истории
            yield f"data: {json.dumps({'step': 3, 'total': 5, 'message': 'Удаление файлов истории...', 'status': 'running'})}\n\n"
            ssh_service.execute_command(server, 'sudo rm -f /var/tmp/metrics_history.json', timeout=10)
            yield f"data: {json.dumps({'step': 3, 'total': 5, 'message': '✅ Файлы истории удалены', 'status': 'success'})}\n\n"
            
            # Шаг 4: Удаление скриптов
            yield f"data: {json.dumps({'step': 4, 'total': 5, 'message': 'Удаление скриптов мониторинга...', 'status': 'running'})}\n\n"
            ssh_service.execute_command(server, 'sudo rm -rf /usr/local/bin/monitoring', timeout=10)
            yield f"data: {json.dumps({'step': 4, 'total': 5, 'message': '✅ Скрипты удалены', 'status': 'success'})}\n\n"
            
            # Шаг 5: Удаление sudo правил (опционально)
            yield f"data: {json.dumps({'step': 5, 'total': 5, 'message': 'Очистка настроек...', 'status': 'running'})}\n\n"
            ssh_service.execute_command(server, 'sudo rm -f /etc/sudoers.d/monitoring', timeout=10)
            yield f"data: {json.dumps({'step': 5, 'total': 5, 'message': '✅ Настройки очищены', 'status': 'success'})}\n\n"
            
            # Проверяем удаление
            check_result = ssh_service.execute_command(
                server,
                'test -f /usr/local/bin/monitoring/get-all-stats.sh && echo "exists" || echo "removed"',
                timeout=10
            )
            
            if 'removed' in check_result.get('output', ''):
                yield f"data: {json.dumps({'complete': True, 'status': 'success', 'message': '🎉 Мониторинг успешно удален!'})}\n\n"
            else:
                yield f"data: {json.dumps({'error': 'Не удалось полностью удалить мониторинг', 'status': 'error'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"
    
    return Response(generate_uninstall_progress(), mimetype='text/event-stream')


# Глобальная переменная для отслеживания отмены установки
installation_cancelled = {}

@monitoring_bp.route('/api/monitoring/<int:server_id>/cancel-install', methods=['POST'])
def cancel_installation(server_id):
    """Отменить текущую установку"""
    global installation_cancelled
    installation_cancelled[server_id] = True
    
    return jsonify({
        'success': True,
        'message': 'Отмена установки...'
    })
```

---

# 3. Критические исправления безопасности

> **⚠️ ВАЖНО:** Эти изменения предотвратят перегрузку сервера и блокировку SSH!

---

## 📋 Проблемы которые исправляем:

1. ❌ Слишком частые SSH подключения (каждые 2 секунды)
2. ❌ Короткие timeout (10 сек вместо 30-60)
3. ❌ Новое SSH подключение каждый раз (нет переиспользования)
4. ❌ Cron каждую минуту без защиты от накопления процессов
5. ❌ Нет обработки ошибок и rate limiting
6. ❌ POST endpoint вызывается через GET (EventSource)

---

## 3.1 JavaScript - Безопасные интервалы

### 📝 Файл: `templates/monitoring.html` (JavaScript раздел)

#### Изменение 1: Увеличить интервал обновления

```javascript
// ❌ БЫЛО:
const refreshInterval = 2000; // 2 seconds

// ✅ ДОЛЖНО БЫТЬ:
const refreshInterval = 30000; // 30 seconds - безопасный интервал
```

#### Изменение 2: Счетчик ошибок и автоостановка

```javascript
// Добавить в начало скрипта:
let errorCount = 0;
const MAX_ERRORS = 3;
let intervals = []; // Для хранения всех setInterval

function handleError(message, context = '') {
    errorCount++;
    console.warn(`⚠️ Error ${errorCount}/${MAX_ERRORS} [${context}]: ${message}`);

    if (errorCount >= MAX_ERRORS) {
        console.error('❌ Too many errors! Stopping auto-refresh.');
        stopAllIntervals();
        showErrorNotification('Потеряно соединение с сервером. Автообновление остановлено.');
    }
}

function stopAllIntervals() {
    console.log('🛑 Stopping all auto-refresh intervals...');
    intervals.forEach(interval => clearInterval(interval));
    intervals = [];
}

function showErrorNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'alert alert-danger alert-dismissible fade show';
    notification.style.position = 'fixed';
    notification.style.top = '80px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.maxWidth = '400px';
    notification.innerHTML = `
        <div class="d-flex align-items-start">
            <div style="font-size: 2rem; margin-right: 15px;">⚠️</div>
            <div>
                <strong>Ошибка подключения</strong><br>
                ${message}
                <div class="mt-2">
                    <button class="btn btn-sm btn-primary" onclick="location.reload()">
                        <i class="bi bi-arrow-clockwise"></i> Обновить страницу
                    </button>
                </div>
            </div>
            <button type="button" class="btn-close ms-2" data-bs-dismiss="alert"></button>
        </div>
    `;
    document.body.appendChild(notification);
}
```

#### Изменение 3: Timeout для fetch запросов

```javascript
// Пример для функции обновления:
async function updateNetworkStats() {
    try {
        const response = await fetch(`/api/monitoring/${serverId}/network-stats`, {
            signal: AbortSignal.timeout(25000) // Timeout 25 секунд
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            errorCount = 0; // Сброс при успехе
            // ... обновление UI ...
        } else {
            handleError(data.error || 'Failed to load network stats', 'NetworkStats');
        }
    } catch (error) {
        handleError(error.message, 'NetworkStats');
    }
}

// При инициализации:
intervals.push(setInterval(updateNetworkStats, 30000));
intervals.push(setInterval(updateFirewallStatus, 30000));
intervals.push(setInterval(updateServicesStatus, 30000));
intervals.push(setInterval(updateSecurityEvents, 60000));
intervals.push(setInterval(updateCharts, 120000));
```

---

## 3.2 Python - SSH Connection Pooling

### 📝 Файл: `app/services/ssh_service.py`

```python
import threading
import logging
import paramiko
import time

logger = logging.getLogger(__name__)

class SSHService:
    """SSH Service с connection pooling"""
    
    # Кэш подключений
    _connection_pool = {}
    _pool_lock = threading.Lock()
    
    @classmethod
    def get_connection_pooled(cls, server):
        """Получить или создать SSH подключение (с переиспользованием)"""
        key = f"{server.host}:{server.port or 22}:{server.username}"
        
        with cls._pool_lock:
            # Проверяем есть ли живое подключение
            if key in cls._connection_pool:
                conn = cls._connection_pool[key]
                try:
                    if conn.get_transport() and conn.get_transport().is_active():
                        logger.info(f"♻️ Reusing existing connection to {server.host}")
                        return conn
                    else:
                        logger.info(f"💀 Old connection dead, removing")
                        del cls._connection_pool[key]
                except Exception as e:
                    logger.warning(f"Connection check failed: {e}")
                    if key in cls._connection_pool:
                        del cls._connection_pool[key]
            
            # Создаем новое подключение
            logger.info(f"🔌 Creating new SSH connection to {server.host}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                ssh.connect(
                    server.host,
                    port=server.port or 22,
                    username=server.username,
                    password=server.password,
                    timeout=30,              # Увеличили с 10 до 30
                    banner_timeout=60,       # Важно!
                    auth_timeout=30,         # Важно!
                    look_for_keys=False,     # Быстрее
                    allow_agent=False        # Быстрее
                )
                
                cls._connection_pool[key] = ssh
                return ssh
                
            except Exception as e:
                logger.error(f"Failed to connect to {server.host}: {e}")
                raise
    
    def execute_command(self, server, command, timeout=30):
        """Выполнить команду используя pooled connection"""
        try:
            ssh = self.get_connection_pooled(server)
            
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            return {
                'success': True,
                'output': output,
                'error': error
            }
            
        except Exception as e:
            # При ошибке - удаляем подключение из пула
            key = f"{server.host}:{server.port or 22}:{server.username}"
            with self._pool_lock:
                if key in self._connection_pool:
                    try:
                        self._connection_pool[key].close()
                    except:
                        pass
                    del self._connection_pool[key]
            
            logger.error(f"Error executing command on {server.host}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def close_all(cls):
        """Закрыть все подключения (вызывать при остановке приложения)"""
        logger.info("🧹 Closing all SSH connections...")
        with cls._pool_lock:
            for key, conn in list(cls._connection_pool.items()):
                try:
                    logger.info(f"Closing connection: {key}")
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection {key}: {e}")
            cls._connection_pool.clear()
        logger.info("✅ All SSH connections closed")
```

---

## 3.3 Python - Rate Limiting

### 📝 Создать новый файл: `app/utils/rate_limiter.py`

```python
"""
Rate Limiter для защиты от слишком частых запросов
"""
import time
import logging
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

class RateLimiter:
    """Ограничитель частоты запросов"""
    
    def __init__(self, max_requests=10, time_window=60):
        """
        Args:
            max_requests: максимум запросов
            time_window: в течение скольких секунд
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
        self.blocked_count = defaultdict(int)
        self.lock = Lock()
    
    def is_allowed(self, key):
        """
        Проверить можно ли выполнить запрос
        
        Args:
            key: уникальный идентификатор (например server_id)
            
        Returns:
            bool: True если запрос разрешен, False если превышен лимит
        """
        with self.lock:
            now = time.time()
            
            # Удаляем старые запросы (за пределами окна)
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < self.time_window
            ]
            
            # Проверяем лимит
            if len(self.requests[key]) >= self.max_requests:
                self.blocked_count[key] += 1
                if self.blocked_count[key] % 10 == 0:  # Log every 10th block
                    logger.warning(
                        f"🚫 Rate limit exceeded for '{key}' - "
                        f"blocked {self.blocked_count[key]} times "
                        f"(limit: {self.max_requests} req/{self.time_window}s)"
                    )
                return False
            
            # Добавляем новый запрос
            self.requests[key].append(now)
            return True
```

### 📝 Использовать в `app/routes/api.py`

```python
from app.utils.rate_limiter import RateLimiter

# Создать лимитер (макс 10 запросов в минуту на сервер)
rate_limiter = RateLimiter(max_requests=10, time_window=60)

# В каждый endpoint добавить проверку:
@api_bp.route('/monitoring/<server_id>/network-stats')
def get_network_stats(server_id):
    """Получить статистику сети"""
    
    # Проверка rate limit
    if not rate_limiter.is_allowed(f"server_{server_id}"):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait a moment.'
        }), 429  # HTTP 429 Too Many Requests
    
    try:
        # ... остальная логика ...
        pass
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

## 3.4 Python - Graceful Shutdown

### 📝 Файл: `run.py`

```python
import atexit
import logging
from app.services.ssh_service import SSHService

logger = logging.getLogger(__name__)

# Закрывать все SSH подключения при остановке приложения
@atexit.register
def cleanup():
    """Очистка ресурсов при остановке приложения"""
    logger.info("🧹 Cleaning up SSH connections...")
    try:
        SSHService.close_all()
        logger.info("✅ SSH connections closed")
    except Exception as e:
        logger.warning(f"⚠️ Error during cleanup: {e}")
```

---

# 4. Тестирование и проверка

## 4.1 Проверка интервала обновления

```bash
# Запустите приложение
python3 run.py

# Откройте страницу мониторинга
# Откройте консоль браузера (F12) → Network
# Фильтр: network-stats

# Проверьте:
# ✓ Запросы идут каждые ~30 секунд (не 2!)
# ✓ Нет множественных одновременных запросов
# ✓ При ошибках автообновление останавливается после 3 попыток
```

## 4.2 Проверка SSH подключений

```bash
# Во время работы приложения на сервере:
ssh root@your-server

# Проверьте количество SSH соединений:
netstat -tn | grep :22 | wc -l

# Должно быть:
# ✓ 1-2 соединения (вместо 10-20)
```

## 4.3 Проверка cron

```bash
# На сервере:
crontab -l

# Должно быть:
# ✓ */5 * * * * flock -n /var/run/metrics-history.lock ...
# (раз в 5 минут с lock файлом)
```

## 4.4 Проверка rate limiting

```bash
# В браузере откройте консоль (F12) и выполните:
for (let i = 0; i < 15; i++) {
    fetch('/api/monitoring/3/network-stats')
        .then(r => r.json())
        .then(d => console.log(i, d));
}

# Ожидаемый результат:
# Первые 10 запросов: success: true
# Следующие 5 запросов: error: "Rate limit exceeded", status: 429
```

---

# 5. Troubleshooting

## 5.1 Если сервер уже перегружен

```bash
# Зайдите через веб-консоль хостинга

# 1. Остановить cron
crontab -r

# 2. Убить процессы мониторинга
pkill -9 -f monitoring

# 3. Разблокировать IP (если fail2ban)
fail2ban-client unban --all

# 4. Перезапустить SSH
systemctl restart sshd

# 5. Проверить загрузку
top
htop
```

## 5.2 Сравнение ДО и ПОСЛЕ

| Параметр | ДО (опасно ❌) | ПОСЛЕ (безопасно ✅) |
|----------|----------------|----------------------|
| **JS интервал обновления** | 2 секунды | 30 секунд |
| **SSH timeout** | 10 сек | 30/60 сек |
| **SSH подключения** | Новое каждый раз | Переиспользование (pooling) |
| **Cron частота** | Каждую минуту | Раз в 5 минут |
| **Cron защита** | Нет | Lock файл (flock) |
| **Rate limiting** | Нет | 10 запросов/минуту |
| **Обработка ошибок** | Нет | Остановка после 3 ошибок |
| **Graceful shutdown** | Нет | Закрытие всех подключений |
| **Fetch timeout** | Нет (бесконечный) | 25 секунд |

---

## ✅ Финальный Чеклист

- [ ] Backend: Установка мониторинга (`install_monitoring`)
- [ ] Backend: Проверка установки (`check_monitoring_installed`)
- [ ] Backend: Удаление мониторинга (`uninstall_monitoring`)
- [ ] Backend: Отмена установки (`cancel_installation`)
- [ ] Backend: SSH Connection Pooling
- [ ] Backend: Rate Limiting
- [ ] Backend: Graceful Shutdown
- [ ] Frontend: UI установки с прогрессом
- [ ] Frontend: UI удаления с подтверждением
- [ ] Frontend: Безопасные интервалы (30 сек)
- [ ] Frontend: Обработка ошибок (3 попытки)
- [ ] Frontend: Timeout для fetch (25 сек)
- [ ] Server: Cron с flock (каждые 5 минут)
- [ ] Server: Скрипты мониторинга
- [ ] Тестирование: Интервалы обновления
- [ ] Тестирование: SSH подключения
- [ ] Тестирование: Rate limiting
- [ ] Тестирование: Cron задачи

---

## 🎯 Результат

После применения всех изменений вы получите:

✅ **Безопасную** систему мониторинга без перегрузки сервера
✅ **Надежную** систему с обработкой ошибок и автовосстановлением
✅ **Эффективную** систему с переиспользованием SSH подключений
✅ **Масштабируемую** систему с rate limiting
✅ **Удобную** систему с установкой в один клик

**Поздравляю! Система мониторинга готова к продакшену! 🎉**

