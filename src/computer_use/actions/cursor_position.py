from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("cursor_position")
class CursorPositionHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        pass

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        try:
            x, y = backend.get_cursor_position()
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"coordinate": [x, y]})
