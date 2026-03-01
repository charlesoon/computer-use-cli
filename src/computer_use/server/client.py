from __future__ import annotations

import json
import socket
import struct
from typing import Any

from computer_use.server.server import HEADER_SIZE, STATE_FILE


def _read_state() -> dict[str, Any] | None:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def try_server_request(
    action: str,
    params: dict[str, Any],
    screenshot_dir: str | None = None,
    format_name: str = "anthropic",
) -> dict[str, Any] | None:
    state = _read_state()
    if state is None:
        return None

    port = state.get("port")
    if port is None:
        return None

    request = {"action": action, "params": params}
    if screenshot_dir is not None:
        request["screenshot_dir"] = screenshot_dir
    request["format"] = format_name

    payload = json.dumps(request, ensure_ascii=False).encode("utf-8")
    header = struct.pack(">I", len(payload))

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", port))

        sock.sendall(header + payload)

        resp_header = b""
        while len(resp_header) < HEADER_SIZE:
            chunk = sock.recv(HEADER_SIZE - len(resp_header))
            if not chunk:
                return None
            resp_header += chunk

        length = struct.unpack(">I", resp_header)[0]
        if length == 0 or length > 10 * 1024 * 1024:
            return None

        data = b""
        while len(data) < length:
            chunk = sock.recv(min(length - len(data), 65536))
            if not chunk:
                return None
            data += chunk

        return json.loads(data.decode("utf-8"))
    except (OSError, ConnectionRefusedError, socket.timeout, json.JSONDecodeError):
        return None
    finally:
        try:
            sock.close()
        except Exception:
            pass
