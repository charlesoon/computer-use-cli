from __future__ import annotations

import sys

from computer_use.platform.base import PlatformBackend

_instance: PlatformBackend | None = None


def get_backend() -> PlatformBackend:
    global _instance
    if _instance is not None:
        return _instance
    if sys.platform == "win32":
        from computer_use.platform.windows import WindowsBackend
        _instance = WindowsBackend()
    elif sys.platform == "darwin":
        from computer_use.platform.macos import MacOSBackend
        _instance = MacOSBackend()
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")
    return _instance
