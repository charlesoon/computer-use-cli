from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

_SERVER_BYPASS_ACTIONS = {"serve", "monitors", "chain", "screenshot"}

def estimate_tokens(data: dict[str, Any]) -> int:
    if "screenshot_path" in data:
        w = data.get("display_width", 1024)
        h = data.get("display_height", 768)
        return round((w * h) / 750)
    if "text" in data and isinstance(data["text"], str):
        text = data["text"]
        return max(1, round(len(text) / 4))
    json_str = json.dumps(data)
    return max(1, round(len(json_str) / 4))


def build_response(
    status: str,
    action: str,
    elapsed_ms: float,
    data: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    resp: dict[str, Any] = {
        "status": status,
        "action": action,
        "elapsed_ms": round(elapsed_ms, 1),
    }
    if error is not None:
        resp["error"] = error
        resp["estimated_tokens"] = max(1, round(len(error) / 4))
    elif data:
        resp["estimated_tokens"] = estimate_tokens(data)
        resp["data"] = data
    else:
        resp["estimated_tokens"] = 1
        resp["data"] = {}
    return resp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="computer-use",
        description="Cross-platform desktop automation CLI",
    )
    parser.add_argument(
        "action",
        help="Action to execute (screenshot, left_click, type, key, serve, monitors, etc.)",
    )
    parser.add_argument(
        "--params",
        type=str,
        default="{}",
        help="JSON parameters for the action",
    )
    parser.add_argument(
        "--format",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="Input/output format (default: anthropic)",
    )
    parser.add_argument(
        "--screenshot-dir",
        type=str,
        default=None,
        help="Directory to save screenshots",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="Screenshot region: x,y,w,h",
    )
    parser.add_argument(
        "--cursor_region",
        type=str,
        default=None,
        help="Screenshot region centered on cursor: w,h",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        default=False,
        help="Use OCR instead of image for screenshot",
    )
    parser.add_argument(
        "--monitor",
        type=int,
        default=0,
        help="Monitor index (default: 0 = primary)",
    )
    parser.add_argument(
        "--actions",
        type=str,
        default=None,
        help="JSON array of actions for chain command",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        default=False,
        help="Stop the running server (use with 'serve')",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        default=False,
        help="Show server status (use with 'serve')",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port for server mode (default: auto-assign)",
    )
    return parser.parse_args(argv)


def _run_serve(args: argparse.Namespace) -> dict[str, Any]:
    from computer_use.server.server import serve, server_status, stop_server

    if args.stop:
        stopped = stop_server()
        if stopped:
            return {"stopped": True}
        return {"error": "No running server found"}

    if args.status:
        state = server_status()
        if state is not None:
            return {"running": True, "pid": state["pid"], "port": state["port"]}
        return {"running": False}

    serve(port=args.port)
    return {"started": True}


def _run_monitors(args: argparse.Namespace) -> dict[str, Any]:
    from computer_use.platform import get_backend

    backend = get_backend()
    monitors = backend.get_monitors()
    return {
        "monitors": [
            {
                "index": m.index,
                "primary": m.primary,
                "logical": [m.logical_width, m.logical_height],
                "physical": [m.physical_width, m.physical_height],
                "dpi_scale": m.dpi_scale,
                "position": [m.position_x, m.position_y],
            }
            for m in monitors
        ]
    }


def run_action(args: argparse.Namespace) -> dict[str, Any]:
    from computer_use.actions import get_handler
    from computer_use.adapters import get_adapter
    from computer_use.coordinate import scale_params
    from computer_use.platform import get_backend
    from computer_use.screenshot.scaling import ScalingContext

    action_name = args.action

    if action_name == "serve":
        return _run_serve(args)

    if action_name == "monitors":
        return _run_monitors(args)

    params = json.loads(args.params)

    adapter = get_adapter(args.format)
    action_name, params = adapter.normalize(action_name, params)

    if action_name == "chain":
        from computer_use.chain import ChainExecutor

        actions_list = json.loads(args.actions) if args.actions else params.get("actions", [])
        backend = get_backend()
        executor = ChainExecutor()
        screen_info = backend.get_screen_info(args.monitor)
        scaling = ScalingContext(
            logical_width=screen_info.logical_width,
            logical_height=screen_info.logical_height,
            dpi_scale=screen_info.dpi_scale,
        )
        result = executor.execute(actions_list, backend, args.screenshot_dir, scaling, adapter)
        if result.success:
            return adapter.denormalize_result(action_name, result.data)
        return adapter.denormalize_result(action_name, {"error": result.error or "Unknown chain error"})

    backend = get_backend()

    if action_name == "screenshot":
        if args.region:
            parts = [int(x) for x in args.region.split(",")]
            params["region"] = parts
        if args.cursor_region:
            parts = [int(x) for x in args.cursor_region.split(",")]
            params["cursor_region"] = parts
        if args.ocr:
            params["ocr"] = True
        params["monitor"] = args.monitor

    handler = get_handler(action_name)
    if handler is None:
        raise ValueError(f"Unknown action: {action_name}")

    handler.validate(params)

    screen_info = backend.get_screen_info(args.monitor)
    scaling = ScalingContext(
        logical_width=screen_info.logical_width,
        logical_height=screen_info.logical_height,
        dpi_scale=screen_info.dpi_scale,
    )

    scale_params(action_name, params, scaling)

    result = handler.execute(params, backend, args.screenshot_dir)

    if result.success and result.data:
        if "screenshot_path" in result.data:
            if "display_width" not in result.data:
                result.data["display_width"] = scaling.api_width
            if "display_height" not in result.data:
                result.data["display_height"] = scaling.api_height
        if "coordinate" in result.data and action_name == "cursor_position":
            cx, cy = result.data["coordinate"]
            ax, ay = scaling.screen_to_api(cx, cy)
            result.data["coordinate"] = [ax, ay]

    return adapter.denormalize_result(
        action_name,
        result.data if result.success else {"error": result.error},
    )


def _try_server_fallback(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.action in _SERVER_BYPASS_ACTIONS:
        return None

    from computer_use.server.client import try_server_request

    params = json.loads(args.params)
    return try_server_request(
        action=args.action,
        params=params,
        screenshot_dir=args.screenshot_dir,
        format_name=args.format,
    )


def _output(resp: dict[str, Any]) -> None:
    text = json.dumps(resp, ensure_ascii=False)
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> None:
    start = time.perf_counter()
    action_label = "unknown"
    try:
        args = parse_args(argv)
        action_label = args.action

        server_result = _try_server_fallback(args)
        if server_result is not None:
            elapsed = (time.perf_counter() - start) * 1000
            status_val = server_result.get("status", "success")
            if status_val == "error":
                error_msg = server_result.get("error", "Unknown server error")
                resp = build_response("error", action_label, elapsed, error=error_msg)
            else:
                data = server_result.get("data", {})
                resp = build_response("success", action_label, elapsed, data=data)
            _output(resp)
            return

        data = run_action(args)
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            resp = build_response("error", action_label, elapsed, error=data["error"])
        else:
            resp = build_response("success", action_label, elapsed, data=data)
        _output(resp)
    except SystemExit:
        raise
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        resp = build_response("error", action_label, elapsed, error=str(exc))
        _output(resp)
        sys.exit(1)
