from __future__ import annotations

from computer_use.platform.base import (
    MonitorInfo,
    PlatformBackend,
    ScreenInfo,
    WindowInfo,
)


class MacOSBackend(PlatformBackend):
    def get_monitors(self) -> list[MonitorInfo]:
        raise NotImplementedError

    def get_screen_info(self, monitor: int = 0) -> ScreenInfo:
        raise NotImplementedError

    def capture_screenshot(self, monitor: int = 0) -> bytes:
        raise NotImplementedError

    def move_mouse(self, x: int, y: int) -> None:
        raise NotImplementedError

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        count: int = 1,
        modifier_keys: list[str] | None = None,
    ) -> None:
        raise NotImplementedError

    def mouse_down(self, x: int, y: int, button: str = "left") -> None:
        raise NotImplementedError

    def mouse_up(self, x: int, y: int, button: str = "left") -> None:
        raise NotImplementedError

    def drag(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> None:
        raise NotImplementedError

    def type_text(self, text: str) -> None:
        raise NotImplementedError

    def press_key(self, keys: list) -> None:
        raise NotImplementedError

    def hold_key(self, keys: list, duration: float) -> None:
        raise NotImplementedError

    def scroll(
        self,
        x: int,
        y: int,
        direction: str,
        amount: int,
        modifier_keys: list[str] | None = None,
    ) -> None:
        raise NotImplementedError

    def get_windows(self) -> list[WindowInfo]:
        raise NotImplementedError

    def get_active_window(self) -> WindowInfo | None:
        raise NotImplementedError

    def focus_window(
        self,
        pid: int | None = None,
        title: str | None = None,
        process_name: str | None = None,
    ) -> bool:
        raise NotImplementedError

    def get_cursor_position(self) -> tuple[int, int]:
        raise NotImplementedError

    def get_clipboard(self) -> str:
        raise NotImplementedError

    def set_clipboard(self, text: str) -> None:
        raise NotImplementedError
