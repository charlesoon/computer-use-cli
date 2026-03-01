from __future__ import annotations

import os
import time


def save_screenshot(png_bytes: bytes, directory: str | None = None) -> str:
    if directory is None:
        directory = os.path.join(os.path.expanduser("~"), ".computer_use", "screenshots")
    os.makedirs(directory, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    unique_suffix = time.perf_counter_ns()
    filename = f"screenshot_{timestamp}_{unique_suffix}.png"
    filepath = os.path.join(directory, filename)
    with open(filepath, "wb") as f:
        f.write(png_bytes)
    return filepath
