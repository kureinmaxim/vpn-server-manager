"""A read-only Linux snapshot using the same /proc counters as monitoring."""

import math
import shlex
import time

# One SSH command, one shared sampling interval for CPU and network. No installs,
# sudo, history files or remote Python dependency. Prefixes match monitoring.
SNAPSHOT_SCRIPT = r"""
export LC_ALL=C
sample() {
    awk -v tag="CPU$1" '$1 == "cpu" {print tag, $2, $3, $4, $5, $6, $7, $8, $9}' /proc/stat
    awk -v tag="TIME$1" '{print tag, $1}' /proc/uptime
    awk -v tag="NET$1" 'index($0, ":") {
        gsub(":", " ");
        if ($1 ~ /^(eth|ens|eno|enp|wlan|wlp|tun|tap|wg|ppp|ipsec)/)
            print tag, $1, $2, $10
    }' /proc/net/dev
}
sample 1
sleep 1
sample 2
awk '{gsub(":", "", $1); print "MEM", $1, $2}' /proc/meminfo
awk '{print "LOAD", $1, $2, $3}' /proc/loadavg
printf 'CORES '
getconf _NPROCESSORS_ONLN 2>/dev/null || awk '/^processor/ {n++} END {print n}' /proc/cpuinfo
df -kP / 2>/dev/null | awk 'NR == 2 {print "DISK", $2, $3, $4, $5}'
"""
SNAPSHOT_COMMAND = "sh -c " + shlex.quote(SNAPSHOT_SCRIPT)


def _numbers(values, count):
    if len(values) < count:
        raise ValueError("Incomplete metric")
    result = [float(value.rstrip("%")) for value in values[:count]]
    if any(not math.isfinite(value) or value < 0 for value in result):
        raise ValueError("Invalid metric")
    return result


def parse_snapshot(output):
    """Missing/invalid metrics stay null, never masquerade as an idle server."""
    fields, memory, networks = {}, {}, {"NET1": {}, "NET2": {}}
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        key, values = parts[0], parts[1:]
        try:
            if key == "MEM" and len(values) >= 2:
                memory[values[0]] = _numbers(values[1:], 1)[0] * 1024
            elif key in networks and len(values) >= 3:
                networks[key][values[0]] = _numbers(values[1:], 2)
            else:
                fields[key] = values
        except ValueError:
            continue

    result = dict(
        cpu=None,
        memory=None,
        disk=None,
        load=None,
        network=None,
        checked_at=int(time.time()),
    )
    try:
        first = _numbers(fields.get("CPU1", []), 8)
        second = _numbers(fields.get("CPU2", []), 8)
        delta = [b - a for a, b in zip(first, second)]
        total = sum(delta)
        if total > 0 and min(delta) >= 0:
            # iowait is idle, as in SSHService._get_cpu_used_pct.
            result["cpu"] = {
                "used_pct": round(100 * (total - delta[3] - delta[4]) / total, 1)
            }
    except ValueError:
        pass

    total = memory.get("MemTotal", 0)
    available = memory.get("MemAvailable")
    if available is None and all(
        key in memory for key in ("MemFree", "Buffers", "Cached")
    ):
        available = (
            memory["MemFree"]
            + memory["Buffers"]
            + memory["Cached"]
            + memory.get("SReclaimable", 0)
            - memory.get("Shmem", 0)
        )
    if total > 0 and available is not None:
        available = max(0, min(total, available))
        result["memory"] = {
            "total_bytes": total,
            "used_bytes": total - available,
            "available_bytes": available,
            "used_pct": round(100 * (total - available) / total, 1),
        }

    try:
        size, used, free, pct = _numbers(fields.get("DISK", []), 4)
        if size > 0 and used <= size and free <= size and pct <= 100:
            result["disk"] = {
                "mount": "/",
                "total_bytes": size * 1024,
                "used_bytes": used * 1024,
                "available_bytes": free * 1024,
                "used_pct": pct,
            }
    except ValueError:
        pass

    try:
        averages = _numbers(fields.get("LOAD", []), 3)
        cores = _numbers(fields.get("CORES", []), 1)[0]
        if cores >= 1:
            result["load"] = {
                "averages": averages,
                "cores": int(cores),
                "per_core": round(averages[0] / cores, 2),
            }
    except ValueError:
        pass

    try:
        elapsed = (
            _numbers(fields.get("TIME2", []), 1)[0]
            - _numbers(fields.get("TIME1", []), 1)[0]
        )
        interfaces, rx, tx = [], 0, 0
        for name in sorted(networks["NET1"].keys() & networks["NET2"].keys()):
            rx_delta, tx_delta = [
                b - a for a, b in zip(networks["NET1"][name], networks["NET2"][name])
            ]
            if rx_delta < 0 or tx_delta < 0:
                continue  # Interface reset during the sample.
            interfaces.append(name)
            rx += rx_delta
            tx += tx_delta
        if elapsed > 0 and interfaces:
            result["network"] = {
                "rx_bytes_per_second": rx / elapsed,
                "tx_bytes_per_second": tx / elapsed,
                "interfaces": interfaces,
                "sample_seconds": round(elapsed, 2),
            }
    except ValueError:
        pass

    if all(result[key] is None for key in ("cpu", "memory", "disk", "load", "network")):
        raise ValueError("No Linux metrics returned")
    return result
