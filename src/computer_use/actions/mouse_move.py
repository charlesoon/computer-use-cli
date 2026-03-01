from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("mouse_move")
class MouseMoveHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        coord = params.get("coordinate")
        if not isinstance(coord, list) or len(coord) != 2:
            raise ValueError("coordinate must be a [x, y] list")

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        x, y = params["coordinate"]
        try:
            backend.move_mouse(x, y)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"coordinate": [x, y]})
