from __future__ import annotations

from typing import TYPE_CHECKING, Any

from computer_use.actions import get_handler
from computer_use.actions.base import ActionResult
from computer_use.coordinate import scale_params

if TYPE_CHECKING:
    from computer_use.adapters.base import FormatAdapter
    from computer_use.platform.base import PlatformBackend
    from computer_use.screenshot.scaling import ScalingContext


class ChainExecutor:
    def execute(
        self,
        actions_list: list[dict[str, Any]],
        backend: PlatformBackend,
        screenshot_dir: str | None,
        scaling: ScalingContext,
        adapter: FormatAdapter,
    ) -> ActionResult:
        if not actions_list:
            return ActionResult(success=True, data={"executed": 0, "last_action": None})

        executed = 0
        last_result = ActionResult(success=True, data={})

        for item in actions_list:
            action_name = item.get("action", "")
            params = item.get("params", {})

            # Normalize through adapter
            action_name, params = adapter.normalize(action_name, params)

            handler = get_handler(action_name)
            if handler is None:
                return ActionResult(
                    success=False,
                    error=f"Unknown action: {action_name}",
                    data={"executed": executed, "last_action": action_name},
                )

            scale_params(action_name, params, scaling)

            handler.validate(params)
            last_result = handler.execute(params, backend, screenshot_dir)

            executed += 1

            if not last_result.success:
                last_result.data["executed"] = executed
                last_result.data["last_action"] = action_name
                return last_result

        last_result.data["executed"] = executed
        last_result.data["last_action"] = action_name
        return last_result
