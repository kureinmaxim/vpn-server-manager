"""Fixed read-only disk inspection; no user-supplied commands."""
DISPLAY_COMMANDS = """sudo du -xhd1 /var /opt /usr /root 2>/dev/null | sort -h
sudo du -sh /var/backups/telegramonly-reset /var/cache/apt/archives 2>/dev/null
journalctl --disk-usage"""
DISK_SOURCE = r'''import json
import subprocess

commands = [
    ('Каталоги /var, /opt, /usr, /root', ['bash', '-o', 'pipefail', '-c', 'du -xhd1 /var /opt /usr /root 2>/dev/null | sort -h']),
    ('Архивы очистки и кэш пакетов', ['du', '-sh', '/var/backups/telegramonly-reset', '/var/cache/apt/archives']),
    ('Системный журнал', ['journalctl', '--disk-usage']),
]
results = []
for title, command in commands:
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors='replace', timeout=120)
        results.append({'title': title, 'output': result.stdout[:65536], 'success': result.returncode == 0,
            'note': '' if result.returncode == 0 else 'Часть каталогов отсутствует или недоступна; показан полученный результат.'})
    except subprocess.TimeoutExpired:
        results.append({'title': title, 'output': '', 'success': False, 'note': 'Превышено время ожидания (120 секунд).'})
    except OSError:
        results.append({'title': title, 'output': '', 'success': False, 'note': 'Команда недоступна на сервере.'})
print(json.dumps({'results': results}, ensure_ascii=True))
'''
