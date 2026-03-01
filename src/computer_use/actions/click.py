from __future__ import annotations

from typing import Any

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend


def _parse_modifier_keys(text: str | None) -> list[str] | None:
    if not text:
        return None
    keys = [k.strip().lower() for k in text.split("+") if k.strip()]
    return keys or None


class _ClickHandlerBase(ActionHandler):
    _button: str
    _count: int

    def validate(self, params: dict[str, Any]) -> None:
        coord = params.get("coordinate")
        if not isinstance(coord, list) or len(coord) != 2:
            raise ValueError("coordinate must be a [x, y] list")

    def _get_modifier_keys(self, params: dict[str, Any]) -> list[str] | None:
        return None

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        x, y = params["coordinate"]
        modifier_keys = self._get_modifier_keys(params)
        try:
            backend.click(
                x, y,
                button=self._button,
                count=self._count,
                modifier_keys=modifier_keys,
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=True, data={"coordinate": [x, y]})


@register("left_click")
class LeftClickHandler(_ClickHandlerBase):
    _button = "left"
    _count = 1

    def _get_modifier_keys(self, params: dict[str, Any]) -> list[str] | None:
        return _parse_modifier_keys(params.get("text"))


@register("right_click")
class RightClickHandler(_ClickHandlerBase):
    _button = "right"
    _count = 1


@register("middle_click")
class MiddleClickHandler(_ClickHandlerBase):
    _button = "middle"
    _count = 1


@register("double_click")
class DoubleClickHandler(_ClickHandlerBase):
    _button = "left"
    _count = 2


@register("triple_click")
class TripleClickHandler(_ClickHandlerBase):
    _button = "left"
    _count = 3
