from __future__ import annotations

import sys

from computer_use.ocr.base import OCREngine


def get_ocr_engine() -> OCREngine:
    if sys.platform == "win32":
        try:
            from computer_use.ocr.windows import WindowsOCR
            return WindowsOCR()
        except ImportError:
            raise ImportError(
                "OCR requires PaddleOCR. Install with: pip install computer-use[ocr-windows]"
            )
    elif sys.platform == "darwin":
        try:
            from computer_use.ocr.macos import MacOSOCR
            return MacOSOCR()
        except ImportError:
            raise ImportError(
                "OCR requires pyobjc. Install with: pip install computer-use[ocr-macos]"
            )
    else:
        raise RuntimeError(f"OCR not supported on {sys.platform}")
