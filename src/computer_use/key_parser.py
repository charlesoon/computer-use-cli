from __future__ import annotations

from pynput.keyboard import Key

KEY_NAME_MAP: dict[str, Key] = {
    "ctrl": Key.ctrl_l,
    "control": Key.ctrl_l,
    "ctrl_l": Key.ctrl_l,
    "ctrl_r": Key.ctrl_r,
    "alt": Key.alt_l,
    "alt_l": Key.alt_l,
    "alt_r": Key.alt_r,
    "shift": Key.shift_l,
    "shift_l": Key.shift_l,
    "shift_r": Key.shift_r,
    "super": Key.cmd,
    "cmd": Key.cmd,
    "command": Key.cmd,
    "meta": Key.cmd,
    "win": Key.cmd,
    "return": Key.enter,
    "enter": Key.enter,
    "tab": Key.tab,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "escape": Key.esc,
    "esc": Key.esc,
    "space": Key.space,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "home": Key.home,
    "end": Key.end,
    "page_up": Key.page_up,
    "pageup": Key.page_up,
    "page_down": Key.page_down,
    "pagedown": Key.page_down,
    "insert": Key.insert,
    "caps_lock": Key.caps_lock,
    "capslock": Key.caps_lock,
    "num_lock": Key.num_lock,
    "print_screen": Key.print_screen,
    "scroll_lock": Key.scroll_lock,
    "pause": Key.pause,
    "menu": Key.menu,
    "f1": Key.f1,
    "f2": Key.f2,
    "f3": Key.f3,
    "f4": Key.f4,
    "f5": Key.f5,
    "f6": Key.f6,
    "f7": Key.f7,
    "f8": Key.f8,
    "f9": Key.f9,
    "f10": Key.f10,
    "f11": Key.f11,
    "f12": Key.f12,
    "f13": Key.f13,
    "f14": Key.f14,
    "f15": Key.f15,
    "f16": Key.f16,
    "f17": Key.f17,
    "f18": Key.f18,
    "f19": Key.f19,
    "f20": Key.f20,
}

MODIFIER_KEYS = {"ctrl", "control", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r",
                  "shift", "shift_l", "shift_r", "super", "cmd", "command", "meta", "win"}


def parse_key_combination(text: str) -> list:
    parts = [p.strip().lower() for p in text.split("+")]
    result = []
    for part in parts:
        if part in KEY_NAME_MAP:
            result.append(KEY_NAME_MAP[part])
        elif len(part) == 1:
            result.append(part)
        else:
            raise ValueError(f"Unknown key: {part}")
    return result
