from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from computer_use.screenshot.scaling import ScalingContext

COORDINATE_ACTIONS = {
    "left_click", "right_click", "middle_click", "double_click",
    "triple_click", "mouse_move", "scroll", "left_mouse_down",
    "left_mouse_up",
}


def scale_params(
    action_name: str,
    params: dict[str, Any],
    scaling: ScalingContext,
) -> dict[str, Any]:
    """Scale coordinate params from API space to screen space.

    Mutates and returns ``params`` for convenience.
    """
    if action_name in COORDINATE_ACTIONS and "coordinate" in params:
        coord = params["coordinate"]
        sx, sy = scaling.api_to_screen(coord[0], coord[1])
        params["coordinate"] = [sx, sy]

    if action_name == "left_click_drag":
        if "start_coordinate" in params:
            sc = params["start_coordinate"]
            sx, sy = scaling.api_to_screen(sc[0], sc[1])
            params["start_coordinate"] = [sx, sy]
        if "coordinate" in params:
            ec = params["coordinate"]
            ex, ey = scaling.api_to_screen(ec[0], ec[1])
            params["coordinate"] = [ex, ey]

    return params
