"""Standalone Linux service controller used over SSH (no Telegram dependency)."""
import hashlib
import json
import os
import socket
import subprocess
import sys
import time

from .service_catalog import CONTROL_CATALOG as CATALOG
from .protocol_inspection import inspect_protocols
from .protocol_clients import client_operation
ACTIONS = ("start", "stop", "restart")


def run(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
        return result.returncode, result.stdout[:1048576]
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def discover():
    code, raw = run(["systemctl", "list-unit-files", "--type=service", "--no-legend", "--no-pager"])
    units_ok = code == 0
    units = {line.split()[0] for line in raw.splitlines() if line.split()} if units_ok else set()
    code, raw = run(["docker", "ps", "-a", "--no-trunc", "--format", "{{json .}}"])
    containers_ok = code == 0
    containers = []
    if containers_ok:
        for line in raw.splitlines():
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    containers.append(obj)
            except ValueError:
                containers_ok = False
    results = []
    for key, (title, aliases, docker_aliases) in CATALOG.items():
        instances = []
        for alias in aliases:
            unit = alias + ".service"
            if unit not in units:
                continue
            code, raw = run(["systemctl", "show", unit, "--no-pager", "--property=Id,LoadState,ActiveState,SubState,FragmentPath"])
            fields = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
            if code or fields.get("LoadState") != "loaded":
                continue
            # Deduplicate systemd aliases by canonical Id.
            identifier = fields.get("Id", unit)
            if any(i["id"] == identifier for i in instances):
                continue
            instances.append({"runtime": "systemd", "id": identifier,
                              "state": fields.get("ActiveState", "unknown"),
                              "revision": digest(fields)})
        for container in containers:
            name = container.get("Names", "")
            identifier = container.get("ID", "")
            # Exact names or Compose service labels, never image-name substrings.
            labels = dict(x.split("=", 1) for x in container.get("Labels", "").split(",") if "=" in x)
            service = labels.get("com.docker.compose.service", "")
            if name not in docker_aliases and service not in docker_aliases:
                continue
            if len(identifier) != 64 or any(c not in "0123456789abcdef" for c in identifier):
                continue
            instances.append({"runtime": "docker", "id": identifier, "name": name,
                              "state": container.get("State", "unknown"),
                              "project": labels.get("com.docker.compose.project", ""),
                              "service": service,
                              "revision": digest({k: container.get(k) for k in ("ID", "State", "Image", "Labels")})})
        results.append({"key": key, "title": title, "instances": instances})
    return {"hostname": socket.gethostname(), "components": results,
            "systemd_available": units_ok, "docker_available": containers_ok,
            "uid": os.geteuid()}


def plan(body):
    inventory = discover()
    component, action = body.get("component"), body.get("action")
    if component not in CATALOG or action not in ACTIONS:
        raise ValueError("invalid_operation")
    matches = [i for c in inventory["components"] if c["key"] == component
               for i in c["instances"] if i["id"] == body.get("instance") and i["runtime"] == body.get("runtime")]
    if len(matches) != 1:
        raise ValueError("target_changed")
    selected = matches[0]
    result = {"hostname": inventory["hostname"], "component": component,
              "action": action, "target": selected}
    result["plan_hash"] = digest(result)
    return result


def execute(body):
    operation = body.get("operation")
    if operation == "discover":
        return discover()
    if operation == "protocols":
        return inspect_protocols(discover(), run)
    if operation in ("clients", "export_client"):
        return client_operation(body, discover(), run)
    if operation not in ("plan", "apply"):
        raise ValueError("invalid_operation")
    if operation == "plan":
        return plan(body)
    # Cross-process lock: independent app windows must not operate concurrently.
    import fcntl
    fd = os.open("/run/vpn-server-manager-control.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = plan(body)
        if current["plan_hash"] != body.get("plan_hash") or current["hostname"] != body.get("confirmation"):
            raise ValueError("target_changed")
        selected = current["target"]
        # Fixed fields only: never command output, environment or credentials.
        journal(current, "started")
        command = ["systemctl", current["action"], "--", selected["id"]] if selected["runtime"] == "systemd" else ["docker", current["action"], selected["id"]]
        code, _ = run(command)
        updated = discover()
        after = [i for c in updated["components"] if c["key"] == current["component"]
                 for i in c["instances"] if i["id"] == selected["id"] and i["runtime"] == selected["runtime"]]
        expected = ("inactive", "failed") if current["action"] == "stop" and selected["runtime"] == "systemd" else (("exited", "created") if current["action"] == "stop" else ("active", "running"))
        success = code == 0 and len(after) == 1 and after[0]["state"] in expected
        journal(current, "complete" if success else "unconfirmed")
        return {"success": success, "error": None if success else "verify_state", "inventory": updated}
    finally:
        os.close(fd)


def journal(plan_data, status):
    path = "/var/log/vpn-server-manager-control.jsonl"
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        record = {"time": int(time.time()), "component": plan_data["component"],
                  "action": plan_data["action"], "runtime": plan_data["target"]["runtime"],
                  "id": plan_data["target"]["id"], "plan_hash": plan_data["plan_hash"], "status": status}
        os.write(fd, (json.dumps(record) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    try:
        # Arguments contain only allowlisted identifiers, never credentials.
        body = json.loads(sys.argv[1])
        if not isinstance(body, dict):
            raise ValueError("invalid_operation")
        result = execute(body)
    except ValueError as error:
        code = str(error)
        result = {"success": False, "error": code if code in ("invalid_operation", "target_changed") else "remote_failed"}
    except Exception:
        result = {"success": False, "error": "remote_failed"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
