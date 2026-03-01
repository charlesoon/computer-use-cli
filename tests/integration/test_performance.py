"""Integration performance tests for computer-use CLI.

Runs each test case multiple times, measures e2e latency and internal elapsed_ms,
and produces a summary report. Results are written to integration_result.md.
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

import pytest

PYTHON = sys.executable
CLI_MODULE = [PYTHON, "-m", "computer_use"]
NUM_ITERATIONS = 12
WARMUP_ITERATIONS = 2

FALLBACK_THRESHOLDS = {
    "screenshot": 500,
    "screenshot_region": 400,
    "cursor_position": 200,
    "clipboard_read": 200,
    "clipboard_write": 200,
    "status": 300,
    "windows": 200,
    "monitors": 200,
    "mouse_move": 200,
    "scroll": 200,
    "type_text": 300,
    "key_press": 200,
    "wait": 400,
    "chain_2actions": 500,
    "format_openai_click": 300,
    "screenshot_cursor_region": 500,
    "focus_window": 300,
    "double_click": 200,
    "hold_key": 500,
}


def run_cli(*args: str, timeout: float = 15.0) -> tuple[dict, float]:
    """Run CLI command and return (parsed_json, e2e_ms)."""
    start = time.perf_counter()
    result = subprocess.run(
        [*CLI_MODULE, *args],
        capture_output=True,
        timeout=timeout,
    )
    e2e_ms = (time.perf_counter() - start) * 1000
    stdout = result.stdout.decode("utf-8", errors="replace").strip()
    if not stdout:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        return {"status": "error", "error": stderr or "empty output"}, e2e_ms
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        data = {"status": "error", "error": f"Invalid JSON: {stdout[:200]}"}
    return data, e2e_ms


class TestCase:
    def __init__(self, name: str, args: list[str], validate_fn=None):
        self.name = name
        self.args = args
        self.validate_fn = validate_fn or self._default_validate

    @staticmethod
    def _default_validate(data: dict) -> bool:
        return data.get("status") == "success"


def validate_screenshot(data: dict) -> bool:
    if data.get("status") != "success":
        return False
    d = data.get("data", {})
    path = d.get("screenshot_path", "")
    return os.path.exists(path) and d.get("display_width", 0) > 0


def validate_status(data: dict) -> bool:
    if data.get("status") != "success":
        return False
    d = data.get("data", {})
    return "monitors" in d and "windows" in d and "cursor" in d


def validate_windows(data: dict) -> bool:
    if data.get("status") != "success":
        return False
    return len(data.get("data", {}).get("windows", [])) > 0


def validate_cursor(data: dict) -> bool:
    if data.get("status") != "success":
        return False
    coord = data.get("data", {}).get("coordinate", [])
    return len(coord) == 2


def validate_clipboard_write(data: dict) -> bool:
    if data.get("status") != "success":
        return False
    return data.get("data", {}).get("written") is True


def validate_clipboard_read(data: dict) -> bool:
    if data.get("status") != "success":
        return False
    return "text" in data.get("data", {})


def validate_monitors(data: dict) -> bool:
    if data.get("status") != "success":
        return False
    return len(data.get("data", {}).get("monitors", [])) > 0


def validate_chain(data: dict) -> bool:
    if data.get("status") != "success":
        return False
    d = data.get("data", {})
    return d.get("executed", 0) >= 2


TEST_CASES = [
    TestCase("screenshot", ["screenshot"], validate_screenshot),
    TestCase("screenshot_region", ["screenshot", "--region", "0,0,500,400"], validate_screenshot),
    TestCase("screenshot_cursor_region", ["screenshot", "--cursor_region", "300,200"], validate_screenshot),
    TestCase("status", ["status"], validate_status),
    TestCase("windows", ["windows"], validate_windows),
    TestCase("monitors", ["monitors"], validate_monitors),
    TestCase("cursor_position", ["cursor_position"], validate_cursor),
    TestCase("clipboard_write", ["clipboard", "--params", '{"text": "test_perf_clip"}'], validate_clipboard_write),
    TestCase("clipboard_read", ["clipboard"], validate_clipboard_read),
    TestCase("mouse_move", ["mouse_move", "--params", '{"coordinate": [100, 100]}'], None),
    TestCase("scroll", ["scroll", "--params", '{"coordinate": [500, 400], "scroll_direction": "down", "scroll_amount": 1}'], None),
    TestCase("type_text", ["type", "--params", '{"text": "a"}'], None),
    TestCase("key_press", ["key", "--params", '{"text": "shift"}'], None),
    TestCase("wait", ["wait", "--params", '{"duration": 0.01}'], None),
    TestCase("double_click", ["double_click", "--params", '{"coordinate": [100, 100]}'], None),
    TestCase("hold_key", ["hold_key", "--params", '{"text": "shift", "duration": 0.05}'], None),
    TestCase(
        "chain_2actions",
        [
            "chain", "--actions",
            '[{"action": "mouse_move", "params": {"coordinate": [200, 200]}}, {"action": "cursor_position"}]',
        ],
        validate_chain,
    ),
    TestCase(
        "format_openai_click",
        ["click", "--format", "openai", "--params", '{"x": 100, "y": 100, "button": "left"}'],
        None,
    ),
    TestCase("focus_window", ["focus_window", "--params", '{"process_name": "WindowsTerminal.exe"}'], None),
]


def run_test_iterations(tc: TestCase, n: int, warmup: int = 0) -> list[dict]:
    results = []
    for i in range(warmup + n):
        data, e2e_ms = run_cli(*tc.args)
        if i < warmup:
            continue
        passed = tc.validate_fn(data)
        elapsed_ms = data.get("elapsed_ms", 0)
        est_tokens = data.get("estimated_tokens", 0)
        results.append({
            "iteration": i - warmup + 1,
            "e2e_ms": round(e2e_ms, 1),
            "elapsed_ms": round(elapsed_ms, 1),
            "est_tokens": est_tokens,
            "passed": passed,
            "error": data.get("error"),
        })
    return results


def generate_report(all_results: dict[str, list[dict]]) -> str:
    lines = []
    lines.append("# Integration Test Results")
    lines.append("")
    lines.append(f"- Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- Iterations per TC: {NUM_ITERATIONS} (+ {WARMUP_ITERATIONS} warmup)")
    lines.append(f"- Mode: Fallback (no server)")
    lines.append(f"- Platform: Windows")
    lines.append("")

    lines.append("## Summary Table")
    lines.append("")
    header = "| Test Case | Avg e2e (ms) | P50 (ms) | P95 (ms) | Min (ms) | Max (ms) | Threshold (ms) | Tokens | Pass Rate |"
    sep = "|---|---|---|---|---|---|---|---|---|"
    lines.append(header)
    lines.append(sep)

    for tc_name, results in all_results.items():
        e2e_times = [r["e2e_ms"] for r in results]
        tokens_list = [r["est_tokens"] for r in results]
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        pass_rate = f"{passed}/{total}"

        avg = round(statistics.mean(e2e_times), 1)
        p50 = round(statistics.median(e2e_times), 1)
        sorted_times = sorted(e2e_times)
        p95_idx = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
        p95 = round(sorted_times[p95_idx], 1)
        mn = round(min(e2e_times), 1)
        mx = round(max(e2e_times), 1)
        threshold = FALLBACK_THRESHOLDS.get(tc_name, "N/A")
        avg_tokens = round(statistics.mean(tokens_list)) if tokens_list else 0

        status = "PASS" if passed == total and avg <= threshold else "FAIL" if passed < total else "SLOW"
        lines.append(
            f"| {tc_name} | {avg} | {p50} | {p95} | {mn} | {mx} | {threshold} | {avg_tokens} | {pass_rate} {status} |"
        )

    lines.append("")
    lines.append("## Detailed Results Per TC")
    lines.append("")

    for tc_name, results in all_results.items():
        lines.append(f"### {tc_name}")
        lines.append("")
        lines.append("| Iter | e2e (ms) | internal (ms) | tokens | pass |")
        lines.append("|---|---|---|---|---|")
        for r in results:
            p = "OK" if r["passed"] else f"FAIL: {r.get('error', 'unknown')}"
            lines.append(f"| {r['iteration']} | {r['e2e_ms']} | {r['elapsed_ms']} | {r['est_tokens']} | {p} |")
        lines.append("")

    return "\n".join(lines)


@pytest.mark.integration
def test_all_performance():
    all_results = {}
    for tc in TEST_CASES:
        results = run_test_iterations(tc, NUM_ITERATIONS, WARMUP_ITERATIONS)
        all_results[tc.name] = results

    report = generate_report(all_results)
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "integration_result.md",
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    for tc_name, results in all_results.items():
        passed = sum(1 for r in results if r["passed"])
        assert passed == len(results), f"{tc_name}: {passed}/{len(results)} passed"


if __name__ == "__main__":
    print("Running integration performance tests...")
    all_results = {}
    for tc in TEST_CASES:
        print(f"  {tc.name}...", end=" ", flush=True)
        results = run_test_iterations(tc, NUM_ITERATIONS, WARMUP_ITERATIONS)
        all_results[tc.name] = results
        avg = statistics.mean([r["e2e_ms"] for r in results])
        passed = sum(1 for r in results if r["passed"])
        print(f"avg={avg:.0f}ms pass={passed}/{len(results)}")

    report = generate_report(all_results)
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "integration_result.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport written to {report_path}")
