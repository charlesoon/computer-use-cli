from __future__ import annotations

import json
import os
import signal
import socket
import struct
import sys
import threading
import time
from pathlib import Path
from typing import Any

STATE_DIR = Path.home() / ".computer_use"
STATE_FILE = STATE_DIR / "server.json"
IDLE_TIMEOUT = 300
HEADER_SIZE = 4


def _read_message(conn: socket.socket) -> dict[str, Any] | None:
    header = b""
    while len(header) < HEADER_SIZE:
        chunk = conn.recv(HEADER_SIZE - len(header))
        if not chunk:
            return None
        header += chunk

    length = struct.unpack(">I", header)[0]
    if length == 0 or length > 10 * 1024 * 1024:
        return None

    data = b""
    while len(data) < length:
        chunk = conn.recv(min(length - len(data), 65536))
        if not chunk:
            return None
        data += chunk

    return json.loads(data.decode("utf-8"))


def _send_message(conn: socket.socket, msg: dict[str, Any]) -> None:
    payload = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    header = struct.pack(">I", len(payload))
    conn.sendall(header + payload)


def _build_success(data: dict[str, Any]) -> dict[str, Any]:
    return {"status": "success", "data": data}


def _build_error(error: str) -> dict[str, Any]:
    return {"status": "error", "error": error}


def _write_state(pid: int, port: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "pid": pid,
        "port": port,
        "started_at": time.time(),
    }
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def _remove_state() -> None:
    try:
        STATE_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _read_state() -> dict[str, Any] | None:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _is_pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


class Server:
    def __init__(self, port: int = 0) -> None:
        self._port = port
        self._lock = threading.Lock()
        self._last_activity = time.monotonic()
        self._running = False
        self._server_socket: socket.socket | None = None

    def _reset_idle_timer(self) -> None:
        with self._lock:
            self._last_activity = time.monotonic()

    def _idle_watchdog(self) -> None:
        while self._running:
            time.sleep(5)
            with self._lock:
                elapsed = time.monotonic() - self._last_activity
            if elapsed >= IDLE_TIMEOUT:
                self._shutdown()
                return

    def _shutdown(self) -> None:
        self._running = False
        _remove_state()
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass

    def _handle_request(
        self,
        request: dict[str, Any],
        backend: Any,
    ) -> dict[str, Any]:
        from computer_use.actions import get_handler
        from computer_use.adapters import get_adapter
        from computer_use.coordinate import scale_params
        from computer_use.screenshot.scaling import ScalingContext

        action_name = request.get("action")
        if not action_name:
            return _build_error("Missing 'action' field")

        params = request.get("params", {})
        screenshot_dir = request.get("screenshot_dir")
        format_name = request.get("format", "anthropic")

        adapter = get_adapter(format_name)
        action_name, params = adapter.normalize(action_name, params)

        handler = get_handler(action_name)
        if handler is None:
            return _build_error(f"Unknown action: {action_name}")

        try:
            handler.validate(params)
        except (ValueError, TypeError) as exc:
            return _build_error(f"Validation error: {exc}")

        monitor = request.get("monitor", 0)
        screen_info = backend.get_screen_info(monitor)
        scaling = ScalingContext(
            logical_width=screen_info.logical_width,
            logical_height=screen_info.logical_height,
            dpi_scale=screen_info.dpi_scale,
        )
        params = scale_params(action_name, params, scaling)

        try:
            result = handler.execute(params, backend, screenshot_dir)
        except Exception as exc:
            return _build_error(f"Execution error: {exc}")

        if result.success and result.data:
            if "screenshot_path" in result.data:
                if "display_width" not in result.data:
                    result.data["display_width"] = scaling.api_width
                if "display_height" not in result.data:
                    result.data["display_height"] = scaling.api_height
            if "coordinate" in result.data and action_name == "cursor_position":
                cx, cy = result.data["coordinate"]
                ax, ay = scaling.screen_to_api(cx, cy)
                result.data["coordinate"] = [ax, ay]

        if result.success:
            return _build_success(result.data)
        return _build_error(result.error or "Unknown error")

    def _handle_connection(
        self,
        conn: socket.socket,
        backend: Any,
    ) -> None:
        try:
            conn.settimeout(10)
            request = _read_message(conn)
            if request is None:
                return

            self._reset_idle_timer()
            response = self._handle_request(request, backend)
            _send_message(conn, response)
        except Exception:
            try:
                _send_message(conn, _build_error("Internal server error"))
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def serve(self) -> None:
        from computer_use.platform import get_backend

        backend = get_backend()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", self._port))
        sock.listen(5)
        sock.settimeout(2)

        self._server_socket = sock
        self._running = True
        actual_port = sock.getsockname()[1]

        _write_state(os.getpid(), actual_port)

        watchdog = threading.Thread(target=self._idle_watchdog, daemon=True)
        watchdog.start()

        try:
            while self._running:
                try:
                    conn, _ = sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                thread = threading.Thread(
                    target=self._handle_connection,
                    args=(conn, backend),
                    daemon=True,
                )
                thread.start()
        finally:
            self._shutdown()


def serve(port: int = 0) -> None:
    server = Server(port=port)
    server.serve()


def stop_server() -> bool:
    state = _read_state()
    if state is None:
        return False

    pid = state.get("pid")
    if pid is None:
        return False

    if not _is_pid_alive(pid):
        _remove_state()
        return False

    if sys.platform == "win32":
        import ctypes
        PROCESS_TERMINATE = 0x0001
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
        if handle:
            kernel32.TerminateProcess(handle, 1)
            kernel32.CloseHandle(handle)
    else:
        os.kill(pid, signal.SIGTERM)

    _remove_state()
    return True


def server_status() -> dict[str, Any] | None:
    state = _read_state()
    if state is None:
        return None

    pid = state.get("pid")
    if pid is None or not _is_pid_alive(pid):
        _remove_state()
        return None

    return state
