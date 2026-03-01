from __future__ import annotations

from computer_use.ocr.base import OCREngine


class MacOSOCR(OCREngine):
    def recognize(self, image_bytes: bytes) -> str:
        import objc
        from Foundation import NSData
        from Quartz import (
            CGImageSourceCreateWithData,
            CGImageSourceCreateImageAtIndex,
        )
        from Vision import (
            VNImageRequestHandler,
            VNRecognizeTextRequest,
        )

        ns_data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
        source = CGImageSourceCreateWithData(ns_data, None)
        cg_image = CGImageSourceCreateImageAtIndex(source, 0, None)

        handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
        request = VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(1)  # accurate

        handler.performRequests_error_([request], None)

        results = request.results()
        if not results:
            return ""
        lines = []
        for obs in results:
            candidate = obs.topCandidates_(1)
            if candidate:
                lines.append(candidate[0].string())
        return "\n".join(lines)
