from __future__ import annotations

from typing import Any

from computer_use.adapters.base import FormatAdapter


class AnthropicAdapter(FormatAdapter):
    """Passthrough adapter - internal format is Anthropic format."""

    def normalize(self, action: str, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return action, params

    def denormalize_result(self, action: str, result: dict[str, Any]) -> dict[str, Any]:
        return result
