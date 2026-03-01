from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("clipboard")
class ClipboardHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        pass

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        if "text" in params:
            try:
                backend.set_clipboard(params["text"])
            except Exception as exc:
                return ActionResult(success=False, error=str(exc))
            return ActionResult(success=True, data={"written": True})
        try:
            text = backend.get_clipboard()
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"text": text})
