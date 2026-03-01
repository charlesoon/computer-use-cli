from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("type")
class TypeTextHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        text = params.get("text")
        if not isinstance(text, str):
            raise ValueError("'text' parameter is required and must be a string")

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        text = params["text"]
        try:
            backend.type_text(text)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"text": text})
