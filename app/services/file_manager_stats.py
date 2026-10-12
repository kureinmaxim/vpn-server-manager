"""Read-only resource sampling for the documented Rust File Manager units."""
import math

UNITS = {
    'rust-file-manager.service': 'Rust File Manager',
    'rfm-internal-bridge.service': 'RFM internal bridge',
}
# Fixed unit/property allowlist; never read Environment, command lines or user files.
_SHOW = ('systemctl show --no-pager -p Id -p LoadState -p ActiveState '
         '-p MainPID -p ActiveEnterTimestampMonotonic -p CPUUsageNSec '
         '-p MemoryCurrent -p TasksCurrent -- ' + ' '.join(UNITS) + ' 2>/dev/null')
COMMAND = ("printf 'SAMPLE\\n'; awk '{print \"UP=\" $1}' /proc/uptime; " + _SHOW
           + "; sleep 1; printf '\\nSAMPLE\\n'; awk '{print \"UP=\" $1}' /proc/uptime; " + _SHOW)


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and 0 <= result < 2**64 - 1 else None
    except (TypeError, ValueError):
        return None


def parse_sample(text):
    """Missing/permission-denied measurements remain unknown, not zero."""
    samples = []
    for chunk in text.split('SAMPLE\n')[1:]:
        records, block, uptime = {}, {}, None
        for line in (chunk.strip() + '\n\n').splitlines():
            if line.startswith('UP='):
                uptime = number(line[3:])
            elif '=' in line:
                key, value = line.split('=', 1)
                block[key] = value
            elif block:
                records[block.get('Id')] = block
                block = {}
        samples.append((uptime, records))
    before = samples[0] if len(samples) >= 2 else (None, {})
    after = samples[-1] if samples else (None, {})
    elapsed = after[0] - before[0] if None not in (before[0], after[0]) else 0
    results = []
    for unit, label in UNITS.items():
        old, state = before[1].get(unit, {}), after[1].get(unit, {})
        status = ('not_installed' if state.get('LoadState') == 'not-found'
                  else state.get('ActiveState', 'unknown'))
        cpu = None
        a, b = number(old.get('CPUUsageNSec')), number(state.get('CPUUsageNSec'))
        same_run = (old.get('MainPID') == state.get('MainPID')
                    and old.get('ActiveEnterTimestampMonotonic') == state.get('ActiveEnterTimestampMonotonic')
                    and number(state.get('MainPID')) not in (None, 0))
        if status == 'active' and same_run and elapsed > 0 and a is not None and b is not None and b >= a:
            cpu = round((b - a) / (elapsed * 1e9) * 100, 1)
        results.append({
            'name': unit, 'display_name': label, 'group': 'file_manager',
            'status': status, 'cpu_percent': cpu,
            'memory_bytes': number(state.get('MemoryCurrent')) if status == 'active' else None,
            'tasks': number(state.get('TasksCurrent')) if status == 'active' else None,
        })
    return results
