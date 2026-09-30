"""Host-side executor. Only standard library; sent over verified SSH, never installed.

The inventory deliberately treats each protocol independently from TelegramOnly.
No application credentials, Docker environments or service logs are returned.
"""
from pathlib import Path
from .service_catalog import CONTROL_CATALOG

SCRIPT_SOURCE = Path(__file__).with_name("server_control_remote.py").read_text(encoding="utf-8").replace(
    "from .service_catalog import CONTROL_CATALOG as CATALOG", "CATALOG = " + repr(CONTROL_CATALOG))
SCRIPT_SOURCE = SCRIPT_SOURCE.replace("from .protocol_inspection import inspect_protocols",
    Path(__file__).with_name("protocol_inspection.py").read_text(encoding="utf-8"))
SCRIPT_SOURCE = SCRIPT_SOURCE.replace("from .protocol_clients import client_operation",
    Path(__file__).with_name("protocol_clients.py").read_text(encoding="utf-8").replace(
        "from .protocol_inspection import PROTOCOL_FILES, sources, read_metadata", ""))
