from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("focus_window")
class FocusWindowHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        has_pid = params.get("pid") is not None
        has_title = params.get("title") is not None
        has_process = params.get("process_name") is not None
        if not (has_pid or has_title or has_process):
            raise ValueError(
                "at least one of process_name, title, or pid is required"
            )

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        pid = params.get("pid")
        title = params.get("title")
        process_name = params.get("process_name")
        try:
            success = backend.focus_window(
                pid=pid, title=title, process_name=process_name,
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        if not success:
            return ActionResult(
                success=False,
                error="no matching window found",
            )
        active = backend.get_active_window()
        if active is None:
            return ActionResult(
                success=True,
                data={"focused": True},
            )
        return ActionResult(
            success=True,
            data={
                "focused": True,
                "window": {
                    "z_order": active.z_order,
                    "title": active.title,
                    "process_name": active.process_name,
                    "pid": active.pid,
                    "bounds": active.bounds,
                    "is_minimized": active.is_minimized,
                },
            },
        )
