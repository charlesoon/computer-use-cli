from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ScalingContext:
    logical_width: int
    logical_height: int
    dpi_scale: float = 1.0

    @property
    def api_scale(self) -> float:
        w, h = self.logical_width, self.logical_height
        if w == 0 or h == 0:
            return 1.0
        return min(
            1.0,
            1568 / max(w, h),
            math.sqrt(1_150_000 / (w * h)),
        )

    @property
    def api_width(self) -> int:
        return round(self.logical_width * self.api_scale)

    @property
    def api_height(self) -> int:
        return round(self.logical_height * self.api_scale)

    def api_to_screen(self, x: int, y: int) -> tuple[int, int]:
        scale = self.api_scale
        if scale == 0:
            return x, y
        lx = round(x / scale)
        ly = round(y / scale)
        return lx, ly

    def screen_to_api(self, x: int, y: int) -> tuple[int, int]:
        scale = self.api_scale
        ax = round(x * scale)
        ay = round(y * scale)
        return ax, ay

    def physical_to_logical(self, x: int, y: int) -> tuple[int, int]:
        if self.dpi_scale == 0:
            return x, y
        return round(x / self.dpi_scale), round(y / self.dpi_scale)

    def logical_to_physical(self, x: int, y: int) -> tuple[int, int]:
        return round(x * self.dpi_scale), round(y * self.dpi_scale)
