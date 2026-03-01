from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MonitorInfo:
    index: int
    primary: bool
    logical_width: int
    logical_height: int
    physical_width: int
    physical_height: int
    dpi_scale: float
    position_x: int
    position_y: int


@dataclass
class ScreenInfo:
    logical_width: int
    logical_height: int
    dpi_scale: float


@dataclass
class WindowInfo:
    z_order: int
    title: str
    process_name: str
    pid: int
    bounds: list[int]
    is_minimized: bool


class PlatformBackend(ABC):
    # Screen
    @abstractmethod
    def get_monitors(self) -> list[MonitorInfo]:
        ...

    @abstractmethod
    def get_screen_info(self, monitor: int = 0) -> ScreenInfo:
        ...

    @abstractmethod
    def capture_screenshot(self, monitor: int = 0) -> bytes:
        ...

    # Mouse
    @abstractmethod
    def move_mouse(self, x: int, y: int) -> None:
        ...

    @abstractmethod
    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        count: int = 1,
        modifier_keys: list[str] | None = None,
    ) -> None:
        ...

    @abstractmethod
    def mouse_down(self, x: int, y: int, button: str = "left") -> None:
        ...

    @abstractmethod
    def mouse_up(self, x: int, y: int, button: str = "left") -> None:
        ...

    @abstractmethod
    def drag(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> None:
        ...

    # Keyboard
    @abstractmethod
    def type_text(self, text: str) -> None:
        ...

    @abstractmethod
    def press_key(self, keys: list) -> None:
        ...

    @abstractmethod
    def hold_key(self, keys: list, duration: float) -> None:
        ...

    # Scroll
    @abstractmethod
    def scroll(
        self,
        x: int,
        y: int,
        direction: str,
        amount: int,
        modifier_keys: list[str] | None = None,
    ) -> None:
        ...

    # Window Management
    @abstractmethod
    def get_windows(self) -> list[WindowInfo]:
        ...

    @abstractmethod
    def get_active_window(self) -> WindowInfo | None:
        ...

    @abstractmethod
    def focus_window(
        self,
        pid: int | None = None,
        title: str | None = None,
        process_name: str | None = None,
    ) -> bool:
        ...

    # Environment
    @abstractmethod
    def get_cursor_position(self) -> tuple[int, int]:
        ...

    @abstractmethod
    def get_clipboard(self) -> str:
        ...

    @abstractmethod
    def set_clipboard(self, text: str) -> None:
        ...
