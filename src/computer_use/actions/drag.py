from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("left_click_drag")
class LeftClickDragHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        start = params.get("start_coordinate")
        if not isinstance(start, list) or len(start) != 2:
            raise ValueError("start_coordinate must be a [x, y] list")
        end = params.get("coordinate")
        if not isinstance(end, list) or len(end) != 2:
            raise ValueError("coordinate must be a [x, y] list")

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        start_x, start_y = params["start_coordinate"]
        end_x, end_y = params["coordinate"]
        try:
            backend.drag(start_x, start_y, end_x, end_y)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(
            success=True,
            data={
                "start_coordinate": [start_x, start_y],
                "coordinate": [end_x, end_y],
            },
        )
