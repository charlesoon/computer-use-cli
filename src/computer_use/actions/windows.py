from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("windows")
class WindowsListHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        pass

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        try:
            windows = backend.get_windows()
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(
            success=True,
            data={
                "windows": [
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
            },
        )
