from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


class _MouseStateBase(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        coord = params.get("coordinate")
        if not isinstance(coord, list) or len(coord) != 2:
            raise ValueError("coordinate must be a [x, y] list")


@register("left_mouse_down")
class LeftMouseDownHandler(_MouseStateBase):
    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        x, y = params["coordinate"]
        try:
            backend.mouse_down(x, y)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"coordinate": [x, y]})


@register("left_mouse_up")
class LeftMouseUpHandler(_MouseStateBase):
    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        x, y = params["coordinate"]
        try:
            backend.mouse_up(x, y)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"coordinate": [x, y]})
