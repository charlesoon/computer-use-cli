from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("status")
class StatusHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        pass

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        try:
            monitors = backend.get_monitors()
            active = backend.get_active_window()
            cursor_x, cursor_y = backend.get_cursor_position()
            windows = backend.get_windows()
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        monitors_data = [
            {
                "index": m.index,
                "primary": m.primary,
                "logical": [m.logical_width, m.logical_height],
                "physical": [m.physical_width, m.physical_height],
                "dpi_scale": m.dpi_scale,
                "position": [m.position_x, m.position_y],
            }
            for m in monitors
        ]

        active_data = None
        if active is not None:
            active_data = {
                "z_order": active.z_order,
                "title": active.title,
                "process_name": active.process_name,
                "pid": active.pid,
                "bounds": active.bounds,
                "is_minimized": active.is_minimized,
            }

        windows_data = [
            {
                "z_order": w.z_order,
                "title": w.title,
                "process_name": w.process_name,
                "pid": w.pid,
                "bounds": w.bounds,
                "is_minimized": w.is_minimized,
            }
            for w in windows
        ]

        return ActionResult(
            success=True,
            data={
                "monitors": monitors_data,
                "active_window": active_data,
                "cursor": [cursor_x, cursor_y],
                "windows": windows_data,
            },
        )
