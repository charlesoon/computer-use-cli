from __future__ import annotations

import time
from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


@register("wait")
class WaitHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        duration = params.get("duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise ValueError("duration must be a number greater than 0")

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        duration = params["duration"]
        try:
            time.sleep(duration)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"duration": duration})
