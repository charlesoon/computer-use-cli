from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from computer_use.platform.base import PlatformBackend


@dataclass
class ActionResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ActionHandler(ABC):
    @abstractmethod
    def validate(self, params: dict[str, Any]) -> None:
        """Validate params. Raise ValueError on invalid input."""

    @abstractmethod
    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        """Execute the action and return result."""
