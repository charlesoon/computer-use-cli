from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from computer_use.actions.base import ActionHandler

_registry: dict[str, ActionHandler] = {}


def register(name: str):
    def decorator(cls):
        _registry[name] = cls()
        return cls
    return decorator


def get_handler(name: str) -> ActionHandler | None:
    _ensure_loaded()
    return _registry.get(name)


def list_actions() -> list[str]:
    _ensure_loaded()
    return sorted(_registry.keys())


_loaded = False


def _ensure_loaded():
    global _loaded
    if _loaded:
        return
    _loaded = True
    from computer_use.actions import (  # noqa: F401
        click,
        clipboard,
        cursor_position,
        drag,
        focus_window,
        hold_key,
        key_press,
        mouse_move,
        mouse_state,
        screenshot,
        scroll,
        status,
        type_text,
        wait,
        windows,
    )
