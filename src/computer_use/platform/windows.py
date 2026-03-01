from __future__ import annotations

import ctypes
import ctypes.wintypes
import io
import time

import mss
from PIL import Image
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Button, Controller as MouseController

from computer_use.platform.base import (
    MonitorInfo,
    PlatformBackend,
    ScreenInfo,
    WindowInfo,
)

# Enable Per-Monitor DPI Awareness V2
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _get_dpi_scale() -> float:
    """Get DPI scale factor for the primary monitor."""
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi / 96.0
    except Exception:
        return 1.0


class WindowsBackend(PlatformBackend):
    def __init__(self):
        self._mouse = MouseController()
        self._keyboard = KeyboardController()
        self._sct = mss.mss()

    def get_monitors(self) -> list[MonitorInfo]:
        monitors = []
        for i, mon in enumerate(self._sct.monitors):
            if i == 0:
                continue  # skip "all monitors" entry
            dpi_scale = _get_dpi_scale()
            pw = mon["width"]
            ph = mon["height"]
            lw = round(pw / dpi_scale)
            lh = round(ph / dpi_scale)
            monitors.append(MonitorInfo(
                index=i - 1,
                primary=(i == 1),
                logical_width=lw,
                logical_height=lh,
                physical_width=pw,
                physical_height=ph,
                dpi_scale=dpi_scale,
                position_x=mon["left"],
                position_y=mon["top"],
            ))
        return monitors

    def get_screen_info(self, monitor: int = 0) -> ScreenInfo:
        monitors = self.get_monitors()
        if monitor < 0 or monitor >= len(monitors):
            monitor = 0
        m = monitors[monitor]
        return ScreenInfo(
            logical_width=m.logical_width,
            logical_height=m.logical_height,
            dpi_scale=m.dpi_scale,
        )

    def capture_screenshot(self, monitor: int = 0) -> bytes:
        mss_index = monitor + 1
        if mss_index >= len(self._sct.monitors):
            mss_index = 1
        sct_img = self._sct.grab(self._sct.monitors[mss_index])
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG", compress_level=1)
        return buf.getvalue()

    def move_mouse(self, x: int, y: int) -> None:
        self._mouse.position = (x, y)

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        count: int = 1,
        modifier_keys: list[str] | None = None,
    ) -> None:
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(button, Button.left)
        self._mouse.position = (x, y)

        pressed_keys = []
        if modifier_keys:
            from computer_use.key_parser import KEY_NAME_MAP
            for mk in modifier_keys:
                key = KEY_NAME_MAP.get(mk.lower())
                if key:
                    self._keyboard.press(key)
                    pressed_keys.append(key)

        self._mouse.click(btn, count)

        for key in reversed(pressed_keys):
            self._keyboard.release(key)

    def mouse_down(self, x: int, y: int, button: str = "left") -> None:
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(button, Button.left)
        self._mouse.position = (x, y)
        self._mouse.press(btn)

    def mouse_up(self, x: int, y: int, button: str = "left") -> None:
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(button, Button.left)
        self._mouse.position = (x, y)
        self._mouse.release(btn)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        self._mouse.position = (start_x, start_y)
        time.sleep(0.05)
        self._mouse.press(Button.left)
        time.sleep(0.05)
        steps = 10
        for i in range(1, steps + 1):
            ix = start_x + round((end_x - start_x) * i / steps)
            iy = start_y + round((end_y - start_y) * i / steps)
            self._mouse.position = (ix, iy)
            time.sleep(0.01)
        self._mouse.release(Button.left)

    def type_text(self, text: str) -> None:
        self._keyboard.type(text)

    def press_key(self, keys: list) -> None:
        modifiers = []
        for k in keys[:-1]:
            self._keyboard.press(k)
            modifiers.append(k)
        if keys:
            last = keys[-1]
            self._keyboard.press(last)
            self._keyboard.release(last)
        for k in reversed(modifiers):
            self._keyboard.release(k)

    def hold_key(self, keys: list, duration: float) -> None:
        for k in keys:
            self._keyboard.press(k)
        time.sleep(duration)
        for k in reversed(keys):
            self._keyboard.release(k)

    def scroll(
        self,
        x: int,
        y: int,
        direction: str,
        amount: int,
        modifier_keys: list[str] | None = None,
    ) -> None:
        self._mouse.position = (x, y)

        pressed_keys = []
        if modifier_keys:
            from computer_use.key_parser import KEY_NAME_MAP
            for mk in modifier_keys:
                key = KEY_NAME_MAP.get(mk.lower())
                if key:
                    self._keyboard.press(key)
                    pressed_keys.append(key)

        dx, dy = 0, 0
        if direction == "up":
            dy = amount
        elif direction == "down":
            dy = -amount
        elif direction == "left":
            dx = -amount
        elif direction == "right":
            dx = amount
        self._mouse.scroll(dx, dy)

        for key in reversed(pressed_keys):
            self._keyboard.release(key)

    def get_windows(self) -> list[WindowInfo]:
        windows = []
        z_order = [0]

        def enum_callback(hwnd, _):
            if not ctypes.windll.user32.IsWindowVisible(hwnd):
                return True
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True

            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

            # Skip empty titles
            if not title.strip():
                return True

            # Get process info
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            process_name = ""
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value
            )
            if handle:
                buf2 = ctypes.create_unicode_buffer(260)
                psapi = ctypes.windll.psapi
                if psapi.GetModuleBaseNameW(handle, None, buf2, 260):
                    process_name = buf2.value
                ctypes.windll.kernel32.CloseHandle(handle)

            # Get bounds
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))

            # Check minimized
            is_minimized = bool(ctypes.windll.user32.IsIconic(hwnd))

            windows.append(WindowInfo(
                z_order=z_order[0],
                title=title,
                process_name=process_name,
                pid=pid.value,
                bounds=[rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top],
                is_minimized=is_minimized,
            ))
            z_order[0] += 1
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        return windows

    def get_active_window(self) -> WindowInfo | None:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return None

        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        pid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        process_name = ""
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value
        )
        if handle:
            buf2 = ctypes.create_unicode_buffer(260)
            if ctypes.windll.psapi.GetModuleBaseNameW(handle, None, buf2, 260):
                process_name = buf2.value
            ctypes.windll.kernel32.CloseHandle(handle)

        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        is_minimized = bool(ctypes.windll.user32.IsIconic(hwnd))

        return WindowInfo(
            z_order=0,
            title=title,
            process_name=process_name,
            pid=pid.value,
            bounds=[rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top],
            is_minimized=is_minimized,
        )

    def focus_window(
        self,
        pid: int | None = None,
        title: str | None = None,
        process_name: str | None = None,
    ) -> bool:
        target_hwnd = None

        def find_callback(hwnd, _):
            nonlocal target_hwnd
            if not ctypes.windll.user32.IsWindowVisible(hwnd):
                return True

            if pid is not None:
                w_pid = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
                if w_pid.value == pid:
                    target_hwnd = hwnd
                    return False

            if title is not None:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                if title.lower() in buf.value.lower():
                    target_hwnd = hwnd
                    return False

            if process_name is not None:
                w_pid = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(w_pid))
                PROCESS_QUERY_INFORMATION = 0x0400
                PROCESS_VM_READ = 0x0010
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, w_pid.value
                )
                if handle:
                    buf2 = ctypes.create_unicode_buffer(260)
                    if ctypes.windll.psapi.GetModuleBaseNameW(handle, None, buf2, 260):
                        if process_name.lower() in buf2.value.lower():
                            target_hwnd = hwnd
                            ctypes.windll.kernel32.CloseHandle(handle)
                            return False
                    ctypes.windll.kernel32.CloseHandle(handle)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(find_callback), 0)

        if target_hwnd is None:
            return False

        SW_RESTORE = 9
        if ctypes.windll.user32.IsIconic(target_hwnd):
            ctypes.windll.user32.ShowWindow(target_hwnd, SW_RESTORE)

        current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
        fg_thread = ctypes.windll.user32.GetWindowThreadProcessId(fg_hwnd, None)

        ctypes.windll.user32.AttachThreadInput(current_thread, fg_thread, True)
        ctypes.windll.user32.SetForegroundWindow(target_hwnd)
        ctypes.windll.user32.BringWindowToTop(target_hwnd)
        ctypes.windll.user32.AttachThreadInput(current_thread, fg_thread, False)

        return True

    def get_cursor_position(self) -> tuple[int, int]:
        pos = self._mouse.position
        return (int(pos[0]), int(pos[1]))

    def get_clipboard(self) -> str:
        CF_UNICODETEXT = 13
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.OpenClipboard.argtypes = [ctypes.c_void_p]
        user32.OpenClipboard.restype = ctypes.c_bool
        user32.GetClipboardData.argtypes = [ctypes.c_uint]
        user32.GetClipboardData.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

        if not user32.OpenClipboard(None):
            return ""
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()

    def set_clipboard(self, text: str) -> None:
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        user32.OpenClipboard.argtypes = [ctypes.c_void_p]
        user32.OpenClipboard.restype = ctypes.c_bool
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.argtypes = [ctypes.c_void_p]

        data = (text + "\0").encode("utf-16-le")
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h_mem:
            raise RuntimeError("GlobalAlloc failed")
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            kernel32.GlobalFree(h_mem)
            raise RuntimeError("GlobalLock failed")
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(h_mem)

        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(h_mem)
            raise RuntimeError("OpenClipboard failed")
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, h_mem):
            kernel32.GlobalFree(h_mem)
            user32.CloseClipboard()
            raise RuntimeError("SetClipboardData failed")
        user32.CloseClipboard()
