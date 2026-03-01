from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.key_parser import parse_key_combination
from computer_use.platform.base import PlatformBackend


@register("hold_key")
class HoldKeyHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        text = params.get("text")
        if not isinstance(text, str):
            raise ValueError("'text' parameter is required and must be a string")

        duration = params.get("duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise ValueError("'duration' parameter is required and must be a number greater than 0")

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        text = params["text"]
        duration = params["duration"]
        try:
            keys = parse_key_combination(text)
            backend.hold_key(keys, duration)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"text": text, "duration": duration})
