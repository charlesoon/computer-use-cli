from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FormatAdapter(ABC):
    @abstractmethod
    def normalize(self, action: str, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Convert external format to internal canonical format."""

    @abstractmethod
    def denormalize_result(self, action: str, result: dict[str, Any]) -> dict[str, Any]:
        """Convert internal result to external format."""
