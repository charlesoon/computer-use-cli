from __future__ import annotations

from typing import Any

from computer_use.adapters.base import FormatAdapter

_KEY_MAP: dict[str, str] = {
    "Control": "ctrl",
    "Meta": "super",
    "ArrowUp": "up",
    "ArrowDown": "down",
    "ArrowLeft": "left",
    "ArrowRight": "right",
    "Enter": "return",
    "Backspace": "backspace",
    "Delete": "delete",
    "Escape": "escape",
    "Tab": "tab",
    " ": "space",
}


class OpenAIAdapter(FormatAdapter):
    """Convert OpenAI computer-use format to internal canonical format."""

    def normalize(self, action: str, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        normalizer = _ACTION_NORMALIZERS.get(action)
        if normalizer is None:
            return action, params
        return normalizer(params)

    def denormalize_result(self, action: str, result: dict[str, Any]) -> dict[str, Any]:
        return result


def _convert_key(name: str) -> str:
    return _KEY_MAP.get(name, name)


def _normalize_click(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    button = params.get("button", "left")
    action_map = {"left": "left_click", "right": "right_click", "middle": "middle_click"}
    internal_action = action_map.get(button, "left_click")
    return internal_action, {"coordinate": [params["x"], params["y"]]}


def _normalize_double_click(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    return "double_click", {"coordinate": [params["x"], params["y"]]}


def _normalize_type(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    return "type", {"text": params["text"]}


def _normalize_keypress(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    keys = [_convert_key(k) for k in params["keys"]]
    return "key", {"text": "+".join(keys)}


def _normalize_scroll(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    scroll_x = params.get("scroll_x", 0)
    scroll_y = params.get("scroll_y", 0)
    coordinate = [params["x"], params["y"]]

    if scroll_y != 0:
        direction = "down" if scroll_y < 0 else "up"
        amount = abs(scroll_y)
    else:
        direction = "right" if scroll_x > 0 else "left"
        amount = abs(scroll_x)

    if amount == 0:
        amount = 1

    return "scroll", {
        "coordinate": coordinate,
        "scroll_direction": direction,
        "scroll_amount": amount,
    }


def _normalize_drag(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    path = params["path"]
    return "left_click_drag", {
        "start_coordinate": list(path[0]),
        "coordinate": list(path[-1]),
    }


def _normalize_mouse_move(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    return "mouse_move", {"coordinate": [params["x"], params["y"]]}


def _normalize_screenshot(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    return "screenshot", {}


def _normalize_wait(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    return "wait", {"duration": params["duration"]}


_ACTION_NORMALIZERS: dict[str, Any] = {
    "click": _normalize_click,
    "double_click": _normalize_double_click,
    "type": _normalize_type,
    "keypress": _normalize_keypress,
    "scroll": _normalize_scroll,
    "drag": _normalize_drag,
    "mouse_move": _normalize_mouse_move,
    "screenshot": _normalize_screenshot,
    "wait": _normalize_wait,
}
