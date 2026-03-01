from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from computer_use.adapters.base import FormatAdapter

_ADAPTER_REGISTRY: dict[str, type[FormatAdapter]] = {}


def register_adapter(name: str, cls: type[FormatAdapter]) -> None:
    _ADAPTER_REGISTRY[name] = cls


def get_adapter(format_name: str) -> FormatAdapter:
    _ensure_loaded()
    cls = _ADAPTER_REGISTRY.get(format_name)
    if cls is None:
        raise ValueError(f"Unknown format: {format_name}")
    return cls()


_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    from computer_use.adapters.anthropic import AnthropicAdapter
    from computer_use.adapters.openai import OpenAIAdapter

    register_adapter("anthropic", AnthropicAdapter)
    register_adapter("openai", OpenAIAdapter)
