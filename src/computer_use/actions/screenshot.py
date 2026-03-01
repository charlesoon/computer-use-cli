from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from computer_use.actions import register
from computer_use.actions.base import ActionHandler, ActionResult
from computer_use.platform.base import PlatformBackend
from computer_use.screenshot.capture import save_screenshot
from computer_use.screenshot.scaling import ScalingContext


@register("screenshot")
class ScreenshotHandler(ActionHandler):
    def validate(self, params: dict[str, Any]) -> None:
        pass

    def execute(
        self,
        params: dict[str, Any],
        backend: PlatformBackend,
        screenshot_dir: str | None = None,
    ) -> ActionResult:
        monitor = params.get("monitor", 0)
        try:
            png_bytes = backend.capture_screenshot(monitor)
            image = Image.open(BytesIO(png_bytes))

            region = params.get("region")
            cursor_region = params.get("cursor_region")

            if region is not None:
                x, y, w, h = region
                image = image.crop((x, y, x + w, y + h))
            elif cursor_region is not None:
                image = self._crop_cursor_region(image, cursor_region, backend, monitor)

            screen_info = backend.get_screen_info(monitor)
            scaling = ScalingContext(
                logical_width=image.width,
                logical_height=image.height,
                dpi_scale=screen_info.dpi_scale,
            )
            image = image.resize(
                (scaling.api_width, scaling.api_height), Image.LANCZOS
            )

            if params.get("ocr"):
                return self._handle_ocr(image, region)

            resized_bytes = self._image_to_png_bytes(image)
            path = save_screenshot(resized_bytes, screenshot_dir)
            return ActionResult(
                success=True,
                data={
                    "screenshot_path": path,
                    "display_width": scaling.api_width,
                    "display_height": scaling.api_height,
                },
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    def _crop_cursor_region(
        self,
        image: Image.Image,
        cursor_region: list[int],
        backend: PlatformBackend,
        monitor: int,
    ) -> Image.Image:
        w, h = cursor_region
        cx, cy = backend.get_cursor_position()
        screen_info = backend.get_screen_info(monitor)

        left = max(0, cx - w // 2)
        top = max(0, cy - h // 2)
        right = min(screen_info.logical_width, left + w)
        bottom = min(screen_info.logical_height, top + h)

        left = max(0, right - w)
        top = max(0, bottom - h)

        return image.crop((left, top, right, bottom))

    def _handle_ocr(
        self, image: Image.Image, region: list[int] | None
    ) -> ActionResult:
        try:
            from computer_use.ocr import get_ocr_engine
        except ImportError as exc:
            return ActionResult(success=False, error=str(exc))

        ocr_bytes = self._image_to_png_bytes(image)
        engine = get_ocr_engine()
        text = engine.recognize(ocr_bytes)
        data: dict[str, Any] = {"text": text}
        if region is not None:
            data["region"] = region
        return ActionResult(success=True, data=data)

    @staticmethod
    def _image_to_png_bytes(image: Image.Image) -> bytes:
        buf = BytesIO()
        image.save(buf, format="PNG", compress_level=1)
        return buf.getvalue()
