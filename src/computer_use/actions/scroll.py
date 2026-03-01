from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend

_VALID_DIRECTIONS = {"up", "down", "left", "right"}


@register("scroll")
class ScrollHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        coord = params.get("coordinate")
        if not isinstance(coord, list) or len(coord) != 2:
            raise ValueError("coordinate must be a [x, y] list")

        direction = params.get("scroll_direction")
        if direction not in _VALID_DIRECTIONS:
            raise ValueError(
                f"scroll_direction must be one of {sorted(_VALID_DIRECTIONS)}"
            )

        amount = params.get("scroll_amount")
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError("scroll_amount must be an integer greater than 0")

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        x, y = params["coordinate"]
        direction = params["scroll_direction"]
        amount = params["scroll_amount"]
        modifier_keys = params.get("modifier_keys")
        try:
            backend.scroll(x, y, direction, amount, modifier_keys=modifier_keys)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(
            success=True,
            data={
                "coordinate": [x, y],
                "scroll_direction": direction,
                "scroll_amount": amount,
            },
        )
