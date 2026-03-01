from __future__ import annotations

from abc import ABC, abstractmethod


class OCREngine(ABC):
    @abstractmethod
    def recognize(self, image_bytes: bytes) -> str:
        """Recognize text from PNG image bytes."""
