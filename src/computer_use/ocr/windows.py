from __future__ import annotations

from computer_use.ocr.base import OCREngine


class WindowsOCR(OCREngine):
    def __init__(self):
        from paddleocr import PaddleOCR
        self._engine = PaddleOCR(use_angle_cls=False, enable_mkldnn=True, show_log=False)

    def recognize(self, image_bytes: bytes) -> str:
        import io
        from PIL import Image
        import numpy as np

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)
        result = self._engine.ocr(img_array, cls=False)
        if not result or not result[0]:
            return ""
        lines = []
        for line in result[0]:
            if line and len(line) >= 2:
                text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                lines.append(text)
        return "\n".join(lines)
