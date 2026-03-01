# Computer Use CLI - Swarm Execution Plan

## Context

LLM 에이전트가 데스크톱을 원격 제어할 수 있는 크로스플랫폼 CLI 도구. Anthropic Computer Use API(computer_20251124)와 OpenAI Computer Use(computer_use_preview) 두 스펙을 지원한다. Python CLI로 JSON stdout 출력, Windows + macOS 지원.

**원본 설계**: `plan.md` 참조 (아키텍처, JSON 응답 포맷, 매핑 테이블 등 상세 스펙)

## Tech Stack

- Python 3.10+, mss (screenshot), pynput (input), Pillow (resize), argparse (CLI), hatchling (build)
- OCR: Windows - PaddleOCR, macOS - Vision framework (pyobjc)

## Project Structure

```
computer_use/
├── pyproject.toml
├── .gitignore
├── src/
│   └── computer_use/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── actions/
│       │   ├── __init__.py          # registry + @register
│       │   ├── base.py              # ActionHandler ABC, ActionResult
│       │   ├── screenshot.py
│       │   ├── click.py
│       │   ├── type_text.py
│       │   ├── key_press.py
│       │   ├── mouse_move.py
│       │   ├── scroll.py
│       │   ├── drag.py
│       │   ├── mouse_state.py
│       │   ├── hold_key.py
│       │   ├── wait.py
│       │   ├── windows.py
│       │   ├── focus_window.py
│       │   ├── cursor_position.py
│       │   ├── clipboard.py
│       │   └── status.py
│       ├── platform/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── windows.py
│       │   └── macos.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── anthropic.py
│       │   └── openai.py
│       ├── screenshot/
│       │   ├── __init__.py
│       │   ├── capture.py
│       │   └── scaling.py
│       ├── ocr/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── windows.py
│       │   └── macos.py
│       ├── server/
│       │   ├── __init__.py
│       │   ├── server.py
│       │   └── client.py
│       ├── chain.py
│       └── key_parser.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_cli.py
│   │   ├── test_key_parser.py
│   │   ├── test_scaling.py
│   │   ├── test_chain.py
│   │   ├── test_actions/
│   │   ├── test_adapters/
│   │   ├── test_ocr/
│   │   └── test_server/
│   ├── integration/
│   │   ├── test_screenshot.py
│   │   ├── test_mouse.py
│   │   ├── test_keyboard.py
│   │   ├── test_ocr.py
│   │   ├── test_chain.py
│   │   ├── test_format.py
│   │   └── test_performance.py
│   └── fixtures/
│       ├── screenshots/
│       └── expected_ocr/
└── skill/
    └── SKILL.md
```

---

## Swarm Execution Strategy

### Wave 개요

```
Wave 0: [Foundation]                    ← 단독, 모든 것의 기반
            │
Wave 1: [A1] [A2] [A3] [A4] [A5] [A6] [A7]  ← 7개 병렬, 독립 파일
            │
         (merge)
            │
Wave 2: [B1] [B2] [B3]                 ← 3개 병렬, 플랫폼 통합
            │
         (merge)
            │
Wave 3: [C1] [C2] [C3]                 ← 3개 병렬, 테스트 + 스킬
            │
         (merge + verify)
```

### 핵심 원칙

1. **파일 소유권**: 각 에이전트는 자신이 **생성(create)**하는 파일만 건드림. 다른 에이전트의 파일 수정 금지.
2. **스텁 의존**: Wave 0이 모든 ABC + 스텁을 생성하므로, Wave 1 에이전트는 import만으로 개발 가능.
3. **머지 포인트**: Wave 완료 시 모든 에이전트 결과를 main에 머지 후 다음 Wave 시작.

---

## Wave 0: Foundation (단독 에이전트)

**목적**: 모든 에이전트가 의존하는 인터페이스, 레지스트리, CLI 스켈레톤을 생성한다. Platform backend는 **전체 메서드 시그니처 + NotImplementedError 스텁**으로 작성하여, Wave 1 에이전트가 `backend.move_mouse()` 등을 호출하는 코드를 즉시 작성할 수 있게 한다.

### 생성 파일

| 파일 | 내용 |
|------|------|
| `pyproject.toml` | hatchling 빌드, 모든 dependencies, entry_points `computer-use` |
| `.gitignore` | Python, IDE, __pycache__, .env |
| `src/computer_use/__init__.py` | 패키지 초기화, `__version__` |
| `src/computer_use/__main__.py` | `from .cli import main; main()` |
| `src/computer_use/cli.py` | argparse 기반 전체 CLI 스켈레톤 (모든 서브커맨드, --params, --format, --screenshot-dir, --region, --cursor_region, --ocr, --monitor, --actions). 서버 fallback 로직 골격. JSON 출력 유틸 (elapsed_ms, estimated_tokens 포함). 좌표 스케일링 호출 지점 (ScalingContext 사용) |
| `src/computer_use/actions/__init__.py` | `_registry: dict[str, ActionHandler]`, `@register(name)` 데코레이터, `get_handler(name)` 함수 |
| `src/computer_use/actions/base.py` | `ActionHandler` ABC (`validate`, `execute`), `ActionResult` dataclass (`success`, `data`, `error`) |
| `src/computer_use/platform/__init__.py` | `get_backend() -> PlatformBackend` 팩토리 (sys.platform 분기) |
| `src/computer_use/platform/base.py` | `PlatformBackend` ABC 전체 메서드, `ScreenInfo`, `MonitorInfo`, `WindowInfo`, `MousePosition` dataclass |
| `src/computer_use/platform/windows.py` | `WindowsBackend(PlatformBackend)` 전체 메서드 **스텁** (`raise NotImplementedError`) |
| `src/computer_use/platform/macos.py` | `MacOSBackend(PlatformBackend)` 전체 메서드 **스텁** (`raise NotImplementedError`) |
| `src/computer_use/screenshot/__init__.py` | 빈 파일 |
| `src/computer_use/screenshot/scaling.py` | `ScalingContext` 클래스: `api_scale` 계산, `api_to_screen()`, `screen_to_api()`, `physical_to_logical()`, `logical_to_physical()` |
| `src/computer_use/screenshot/capture.py` | `save_screenshot(png_bytes, directory) -> path` 유틸 |
| `src/computer_use/key_parser.py` | `parse_key_combination(text) -> list[Key]`, `KEY_NAME_MAP` 딕셔너리 (완전 구현) |
| `src/computer_use/ocr/__init__.py` | `get_ocr_engine() -> OCREngine` 팩토리 스켈레톤 |
| `src/computer_use/ocr/base.py` | `OCREngine` ABC (`recognize(image_bytes) -> str`) |
| `src/computer_use/adapters/__init__.py` | `get_adapter(format_name) -> FormatAdapter` 팩토리 스켈레톤 |
| `src/computer_use/adapters/base.py` | `FormatAdapter` ABC (`normalize`, `denormalize_result`) |
| `src/computer_use/server/__init__.py` | 빈 파일 |

### PlatformBackend ABC 전체 메서드 목록

```python
class PlatformBackend(ABC):
    # Screen
    @abstractmethod
    def get_monitors(self) -> list[MonitorInfo]: ...
    @abstractmethod
    def get_screen_info(self, monitor: int = 0) -> ScreenInfo: ...
    @abstractmethod
    def capture_screenshot(self, monitor: int = 0) -> bytes: ...  # PNG

    # Mouse
    @abstractmethod
    def move_mouse(self, x: int, y: int) -> None: ...
    @abstractmethod
    def click(self, x: int, y: int, button: str = "left", count: int = 1, modifier_keys: list[str] | None = None) -> None: ...
    @abstractmethod
    def mouse_down(self, x: int, y: int, button: str = "left") -> None: ...
    @abstractmethod
    def mouse_up(self, x: int, y: int, button: str = "left") -> None: ...
    @abstractmethod
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None: ...

    # Keyboard
    @abstractmethod
    def type_text(self, text: str) -> None: ...
    @abstractmethod
    def press_key(self, keys: list) -> None: ...
    @abstractmethod
    def hold_key(self, keys: list, duration: float) -> None: ...

    # Scroll
    @abstractmethod
    def scroll(self, x: int, y: int, direction: str, amount: int, modifier_keys: list[str] | None = None) -> None: ...

    # Window Management
    @abstractmethod
    def get_windows(self) -> list[WindowInfo]: ...
    @abstractmethod
    def get_active_window(self) -> WindowInfo | None: ...
    @abstractmethod
    def focus_window(self, pid: int | None = None, title: str | None = None, process_name: str | None = None) -> bool: ...

    # Environment
    @abstractmethod
    def get_cursor_position(self) -> tuple[int, int]: ...
    @abstractmethod
    def get_clipboard(self) -> str: ...
    @abstractmethod
    def set_clipboard(self, text: str) -> None: ...
```

### 검증

```bash
pip install -e .
computer-use --help          # CLI 도움말 출력
python -c "from computer_use.actions import get_handler"  # import 성공
python -c "from computer_use.platform.base import PlatformBackend"  # import 성공
python -c "from computer_use.screenshot.scaling import ScalingContext"  # import 성공
python -c "from computer_use.key_parser import parse_key_combination"  # import 성공
```

### 커밋 후 main에 머지

---

## Wave 1: Feature Agents (7개 병렬)

> Wave 0 머지 완료 후 시작. 각 에이전트는 자신의 파일만 **생성**하고, Foundation이 만든 파일은 **읽기만** 한다.

### Agent A1: Mouse Actions

**생성 파일:**
- `src/computer_use/actions/mouse_move.py`
- `src/computer_use/actions/click.py`
- `src/computer_use/actions/drag.py`
- `src/computer_use/actions/mouse_state.py`

**상세:**
- `MouseMoveHandler`: `@register("mouse_move")`, coordinate → `backend.move_mouse(x, y)`
- `BaseClickHandler` + 5종 클릭: `@register("left_click")`, `@register("right_click")`, `@register("middle_click")`, `@register("double_click")`, `@register("triple_click")`. button/count 매핑 → `backend.click(x, y, button, count, modifier_keys)`
- `LeftClickDragHandler`: `@register("left_click_drag")`, start_coordinate + coordinate → `backend.drag()`
- `LeftMouseDownHandler`, `LeftMouseUpHandler`: `@register("left_mouse_down")`, `@register("left_mouse_up")` → `backend.mouse_down/up()`

**읽기 의존 (수정 금지):**
- `actions/base.py` (ActionHandler, ActionResult)
- `actions/__init__.py` (@register)
- `platform/base.py` (PlatformBackend 타입 힌트)

**검증:**
```python
from computer_use.actions import get_handler
assert get_handler("left_click") is not None
assert get_handler("mouse_move") is not None
assert get_handler("left_click_drag") is not None
assert get_handler("left_mouse_down") is not None
```

---

### Agent A2: Keyboard Actions

**생성 파일:**
- `src/computer_use/actions/type_text.py`
- `src/computer_use/actions/key_press.py`
- `src/computer_use/actions/hold_key.py`

**상세:**
- `TypeTextHandler`: `@register("type")`, text → `backend.type_text(text)`
- `KeyPressHandler`: `@register("key")`, text → `key_parser.parse_key_combination(text)` → `backend.press_key(keys)`
- `HoldKeyHandler`: `@register("hold_key")`, text + duration → `key_parser.parse_key_combination(text)` → `backend.hold_key(keys, duration)`

**읽기 의존:** `actions/base.py`, `actions/__init__.py`, `key_parser.py`

**검증:**
```python
from computer_use.actions import get_handler
assert get_handler("type") is not None
assert get_handler("key") is not None
assert get_handler("hold_key") is not None
```

---

### Agent A3: Scroll + Wait + Screenshot Handler

**생성 파일:**
- `src/computer_use/actions/scroll.py`
- `src/computer_use/actions/wait.py`
- `src/computer_use/actions/screenshot.py`

**상세:**
- `ScrollHandler`: `@register("scroll")`, coordinate + scroll_direction + scroll_amount → `backend.scroll()`
- `WaitHandler`: `@register("wait")`, duration → `time.sleep(duration)`
- `ScreenshotHandler`: `@register("screenshot")`, 기본 캡처 로직만. `backend.capture_screenshot(monitor)` → `capture.save_screenshot()`. region/cursor_region/ocr 옵션은 params에서 읽되, OCR 엔진 호출은 `get_ocr_engine()` import (lazy, ImportError 무시). cursor_region은 `backend.get_cursor_position()`으로 중심점 계산 → region으로 변환 (경계 클램핑)

**읽기 의존:** `actions/base.py`, `actions/__init__.py`, `screenshot/capture.py`, `screenshot/scaling.py`, `ocr/__init__.py` (lazy import)

**검증:**
```python
from computer_use.actions import get_handler
assert get_handler("screenshot") is not None
assert get_handler("scroll") is not None
assert get_handler("wait") is not None
```

---

### Agent A4: Window Management + Environment

**생성 파일:**
- `src/computer_use/actions/windows.py`
- `src/computer_use/actions/focus_window.py`
- `src/computer_use/actions/cursor_position.py`
- `src/computer_use/actions/clipboard.py`
- `src/computer_use/actions/status.py`

**상세:**
- `WindowsListHandler`: `@register("windows")` → `backend.get_windows()` → z-order 순 리스트
- `FocusWindowHandler`: `@register("focus_window")` → process_name/title/pid로 `backend.focus_window()`. 복수 매칭 시 z-order 최상위 선택
- `CursorPositionHandler`: `@register("cursor_position")` → `backend.get_cursor_position()` → coordinate
- `ClipboardHandler`: `@register("clipboard")` → text param 유무에 따라 `backend.get_clipboard()` 또는 `backend.set_clipboard(text)`
- `StatusHandler`: `@register("status")` → `backend.get_monitors()` + `backend.get_windows()` + `backend.get_cursor_position()` + `backend.get_active_window()` 조합

**읽기 의존:** `actions/base.py`, `actions/__init__.py`, `platform/base.py`

**검증:**
```python
from computer_use.actions import get_handler
assert get_handler("status") is not None
assert get_handler("windows") is not None
assert get_handler("focus_window") is not None
assert get_handler("cursor_position") is not None
assert get_handler("clipboard") is not None
```

---

### Agent A5: OCR Engines

**생성 파일:**
- `src/computer_use/ocr/windows.py`
- `src/computer_use/ocr/macos.py`

**수정 파일:**
- `src/computer_use/ocr/__init__.py` (Wave 0에서 스켈레톤 생성, 이 에이전트가 팩토리 로직 완성)

**상세:**
- `WindowsOCR(OCREngine)`: PaddleOCR 래퍼. `__init__`에서 `PaddleOCR(use_angle_cls=False, enable_mkldnn=True, show_log=False)`. `recognize()` → PIL Image → PaddleOCR → 텍스트 결합
- `MacOSOCR(OCREngine)`: pyobjc Vision framework 래퍼. `VNRecognizeTextRequest` → `recognize()` → 결과 텍스트 추출
- `get_ocr_engine()` 팩토리: `sys.platform` 분기 → WindowsOCR 또는 MacOSOCR. import 실패 시 명확한 에러 메시지 ("pip install computer-use[ocr-windows]")

**읽기 의존:** `ocr/base.py`

**검증:**
```python
from computer_use.ocr import get_ocr_engine
# Windows에서: engine = get_ocr_engine(); isinstance(engine, WindowsOCR)
# macOS에서: engine = get_ocr_engine(); isinstance(engine, MacOSOCR)
```

---

### Agent A6: Format Adapters

**생성 파일:**
- `src/computer_use/adapters/anthropic.py`
- `src/computer_use/adapters/openai.py`

**수정 파일:**
- `src/computer_use/adapters/__init__.py` (Wave 0에서 스켈레톤 생성, 이 에이전트가 팩토리 완성)

**상세:**
- `AnthropicAdapter(FormatAdapter)`: 패스스루 (내부 포맷 = Anthropic 기반이므로 변환 불필요)
- `OpenAIAdapter(FormatAdapter)`:
  - `normalize()`: OpenAI 액션명 → 내부 액션명 변환 (click→left_click, keypress→key, drag→left_click_drag 등). 파라미터 변환 (x,y → coordinate, keys → text join, scroll_x/y → direction+amount)
  - `denormalize_result()`: 내부 결과 → OpenAI 응답 포맷
  - OpenAI 키 이름 매핑: `"Control"` → `"ctrl"`, `"Meta"` → `"super"`, `"ArrowUp"` → `"up"`, `"Enter"` → `"return"` 등
  - 스크롤 변환: `scroll_y < 0` → down, `scroll_y > 0` → up, `scroll_x` 동일 패턴

**매핑 테이블 (구현 참조):**

| OpenAI Action | → Internal Action | 파라미터 변환 |
|---|---|---|
| `click` (button:"left") | `left_click` | `x,y → coordinate:[x,y]` |
| `click` (button:"right") | `right_click` | `x,y → coordinate:[x,y]` |
| `click` (button:"middle") | `middle_click` | `x,y → coordinate:[x,y]` |
| `double_click` | `double_click` | `x,y → coordinate:[x,y]` |
| `type` | `type` | 동일 |
| `keypress` | `key` | `keys:["Control","s"] → text:"ctrl+s"` |
| `scroll` | `scroll` | `scroll_y<0 → down, >0 → up` |
| `drag` | `left_click_drag` | `path[0]→start_coordinate, path[-1]→coordinate` |
| `mouse_move` | `mouse_move` | `x,y → coordinate:[x,y]` |
| `screenshot` | `screenshot` | 동일 |
| `wait` | `wait` | 동일 |

**읽기 의존:** `adapters/base.py`

**검증:**
```python
from computer_use.adapters import get_adapter
a = get_adapter("anthropic")
o = get_adapter("openai")
action, params = o.normalize("click", {"x": 500, "y": 300, "button": "left"})
assert action == "left_click"
assert params == {"coordinate": [500, 300]}
```

---

### Agent A7: Server Mode

**생성 파일:**
- `src/computer_use/server/server.py`
- `src/computer_use/server/client.py`

**상세:**
- `server.py`:
  - localhost TCP 소켓 서버 (기본 포트 자동 할당 또는 `--port`)
  - 시작 시: `get_backend()` → PlatformBackend 인스턴스 생성, mss/pynput/Pillow 로딩 완료
  - OCR lazy loading: 첫 `--ocr` 요청 시 `get_ocr_engine()` 호출
  - 프로토콜: JSON-over-TCP (length-prefixed). 요청 `{"action": "screenshot", "params": {...}}` → 응답 `{"status": "success", ...}`
  - idle 5분 타이머 → 자동 종료
  - 상태 파일: `~/.computer_use/server.json` (PID, port, 시작 시간)
  - `computer-use serve [--port PORT]` 시작, `serve --stop` 종료, `serve --status` 상태

- `client.py`:
  - `try_server_request(action, params) -> dict | None`: 서버 소켓 연결 시도 → 성공하면 JSON 응답, 실패하면 None (fallback 신호)
  - 상태 파일에서 port 읽기 → 연결 → 요청/응답

**읽기 의존:** `platform/__init__.py`, `actions/__init__.py`, `ocr/__init__.py`

**검증:**
```python
from computer_use.server.client import try_server_request
# 서버 미실행 시 None 반환
assert try_server_request("screenshot", {}) is None
```

---

### Agent A8: Action Chaining

**생성 파일:**
- `src/computer_use/chain.py`

**상세:**
- `ChainExecutor` 클래스:
  - `execute(actions_list, backend, screenshot_dir) -> ActionResult`
  - 액션 리스트를 순차 실행
  - 개별 액션 실패 시 즉시 중단 + 에러 반환 (실행된 수 포함)
  - 마지막 액션 결과를 최종 결과로 반환
  - `executed` 카운트, `last_action` 이름 포함

**읽기 의존:** `actions/__init__.py` (`get_handler`), `actions/base.py` (ActionResult)

**검증:**
```python
from computer_use.chain import ChainExecutor
# MockBackend로 3개 액션 체인 실행 → executed=3
```

---

### Wave 1 머지

모든 A1~A8 에이전트 결과를 main에 머지한다.
**충돌 가능 파일**: `ocr/__init__.py`, `adapters/__init__.py` (A5, A6가 각각 수정). 이 두 파일은 Wave 0에서 스켈레톤으로 생성하되, 팩토리 함수 본문을 `pass`로 비워두어 A5/A6가 채우는 구조.

머지 후 검증:
```python
# 모든 21개 액션 핸들러 등록 확인
from computer_use.actions import get_handler
actions = [
    "status", "monitors", "windows", "focus_window", "cursor_position", "clipboard",
    "screenshot", "left_click", "right_click", "middle_click", "double_click",
    "triple_click", "type", "key", "mouse_move", "scroll", "left_click_drag",
    "left_mouse_down", "left_mouse_up", "hold_key", "wait",
]
for a in actions:
    assert get_handler(a) is not None, f"Missing handler: {a}"
```

---

## Wave 2: Platform Integration (3개 병렬)

> Wave 1 머지 완료 후 시작. 이제 모든 액션 핸들러와 서브시스템이 존재하므로, 플랫폼 백엔드의 스텁을 실제 구현으로 교체한다.

### Agent B1: Windows Backend

**수정 파일:**
- `src/computer_use/platform/windows.py` (스텁 → 실제 구현)

**구현 상세:**

```
모든 메서드의 NotImplementedError를 실제 구현으로 교체:

[Screen]
- get_monitors(): mss.monitors + ctypes.windll.shcore DPI 감지
- get_screen_info(): get_monitors()[index] 기반
- capture_screenshot(): mss.grab(monitor) → PNG bytes

[Mouse] - pynput.mouse.Controller 사용
- move_mouse(): controller.position = (x, y)
- click(): modifier 키 누름 → controller.click(button, count) → modifier 키 놓음
- mouse_down/up(): controller.press/release(button)
- drag(): mouse_down → 중간점 이동 (부드러운 드래그) → mouse_up

[Keyboard] - pynput.keyboard.Controller 사용
- type_text(): controller.type(text)
- press_key(): modifier 키 순서대로 press → 마지막 키 tap → modifier 역순 release
- hold_key(): press → sleep(duration) → release

[Scroll]
- scroll(): controller.scroll(dx, dy) 방향 변환

[Window Management] - ctypes only (추가 의존성 없음)
- get_windows(): EnumWindows (z-order 보존) + GetWindowTextW + GetWindowRect + GetWindowThreadProcessId + GetModuleBaseNameW
- get_active_window(): GetForegroundWindow → WindowInfo
- focus_window(): 대상 찾기 → AttachThreadInput + ShowWindow(SW_RESTORE) + SetForegroundWindow + BringWindowToTop

[Environment]
- get_cursor_position(): pynput controller.position (논리 좌표)
- get_clipboard(): ctypes.windll.user32 OpenClipboard + GetClipboardData(CF_UNICODETEXT)
- set_clipboard(): OpenClipboard + EmptyClipboard + SetClipboardData
```

**DPI 처리:**
- `ctypes.windll.shcore.SetProcessDpiAwareness(2)` (Per-Monitor V2) 프로세스 시작 시 호출
- mss는 물리 해상도 캡처 → DPI scale로 나눠서 논리 해상도 반환

**검증:**
```bash
computer-use screenshot  # 실제 캡처 + JSON
computer-use status      # 모니터/윈도우/커서 정보
computer-use left_click --params '{"coordinate": [500, 300]}'  # 실제 클릭
computer-use type --params '{"text": "hello"}'  # 실제 입력
computer-use windows     # 윈도우 목록
```

---

### Agent B2: macOS Backend

**수정 파일:**
- `src/computer_use/platform/macos.py` (스텁 → 실제 구현)

**구현 상세:**

```
[Screen]
- get_monitors(): mss.monitors + NSScreen.screens() backingScaleFactor
- capture_screenshot(): mss.grab(monitor) → PNG bytes

[Mouse] - pynput.mouse.Controller (Quartz 백엔드 자동)
- (Windows와 동일 패턴, pynput이 추상화)

[Keyboard] - pynput.keyboard.Controller (Quartz 백엔드 자동)
- (Windows와 동일 패턴)

[Scroll]
- (Windows와 동일 패턴)

[Window Management] - pyobjc
- get_windows(): CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID) → kCGWindowLayer==0 필터 → z-order 순 WindowInfo 리스트
- get_active_window(): NSWorkspace.sharedWorkspace().frontmostApplication() → PID → get_windows() 에서 매칭
- focus_window(): NSRunningApplication.runningApplicationWithProcessIdentifier_(pid) → activateWithOptions_(NSApplicationActivateIgnoringOtherApps)

[Environment]
- get_cursor_position(): pynput controller.position
- get_clipboard(): NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString)
- set_clipboard(): NSPasteboard.generalPasteboard() → clearContents() → setString_forType_()
```

**접근성 권한:**
- pynput + CGWindowList 사용 시 접근성 권한 필요
- 권한 없으면 명확한 에러 메시지: "System Preferences > Privacy & Security > Accessibility 에서 터미널 앱 허용"

**검증:**
```bash
# macOS 환경에서
computer-use screenshot
computer-use status
computer-use left_click --params '{"coordinate": [500, 300]}'
```

---

### Agent B3: CLI Integration + Scaling

**수정 파일:**
- `src/computer_use/cli.py` (Wave 0 스켈레톤 → 전체 로직 완성)
- `src/computer_use/screenshot/scaling.py` (Wave 0 기본 구현 → DPI + multi-monitor 확장)

**구현 상세:**

`cli.py` 완성:
1. args 파싱 (이미 Wave 0에서 구조 생성)
2. `server/client.py`로 서버 연결 시도 → 성공하면 위임
3. 실패 시 fallback: `get_backend()` → backend 직접 사용
4. `--format` 옵션 → `get_adapter(format)` → `adapter.normalize()` → 핸들러 실행 → `adapter.denormalize_result()`
5. `--region`, `--cursor_region`, `--ocr`, `--monitor` 옵션을 screenshot params에 주입
6. `chain` 서브커맨드 → `ChainExecutor` 사용
7. `serve` 서브커맨드 → 서버 start/stop/status
8. `monitors` 서브커맨드 → `backend.get_monitors()`
9. 좌표 스케일링: coordinate가 있는 액션에 대해 `ScalingContext.api_to_screen()` 적용
10. JSON 출력: `elapsed_ms` (time.perf_counter), `estimated_tokens` 계산

`scaling.py` 확장:
- 물리→논리→API 3단계 변환 체인
- `api_scale = min(1.0, 1568/max(w,h), sqrt(1150000/(w*h)))` (논리 해상도 기준)
- `api_to_screen(x, y, scaling_ctx)`: API → 논리 (÷ api_scale) → 물리 (× dpi_scale)
- `screen_to_api(x, y, scaling_ctx)`: 물리 → 논리 (÷ dpi_scale) → API (× api_scale)
- 모니터별 독립 ScalingContext (각 모니터의 dpi_scale 반영)

**읽기 의존:** `server/client.py`, `adapters/__init__.py`, `chain.py`, `actions/__init__.py`, 모든 액션 핸들러

**검증:**
```bash
# 전체 CLI 동작 (fallback 모드)
computer-use screenshot                                    # 캡처 + JSON
computer-use left_click --params '{"coordinate": [500, 300]}'  # 좌표 스케일링 적용된 클릭
computer-use screenshot --region 100,200,500,400           # 영역 캡처
computer-use screenshot --cursor_region 200,300            # 커서 중심 캡처
computer-use chain --actions '[{"action":"left_click","params":{"coordinate":[500,300]}},{"action":"screenshot"}]'
computer-use click --format openai --params '{"x": 500, "y": 300, "button": "left"}'
computer-use status                                        # 환경 전체 상태
computer-use monitors                                      # 모니터 목록
```

---

### Wave 2 머지

B1, B2, B3 결과를 main에 머지.
**충돌 없음**: B1은 `platform/windows.py`만, B2는 `platform/macos.py`만, B3는 `cli.py` + `scaling.py`만 수정.

머지 후 전체 기능 검증:
```bash
pip install -e .
computer-use screenshot                    # 실제 캡처
computer-use left_click --params '{"coordinate": [500, 300]}'
computer-use type --params '{"text": "test"}'
computer-use key --params '{"text": "ctrl+a"}'
computer-use status
computer-use windows
computer-use focus_window --params '{"process_name": "notepad.exe"}'
computer-use clipboard
computer-use cursor_position
computer-use screenshot --region 100,200,500,400
computer-use screenshot --cursor_region 200,300
computer-use screenshot --ocr              # OCR 의존성 설치 시
computer-use chain --actions '[{"action":"left_click","params":{"coordinate":[500,300]}},{"action":"screenshot"}]'
computer-use click --format openai --params '{"x": 500, "y": 300, "button": "left"}'
```

---

## Wave 3: Tests + Skill (3개 병렬)

> Wave 2 머지 완료 후 시작. 전체 기능이 동작하는 상태에서 테스트와 SKILL.md를 작성한다.

### Agent C1: Unit Tests

**생성 파일:**
- `tests/conftest.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_key_parser.py`
- `tests/unit/test_scaling.py`
- `tests/unit/test_chain.py`
- `tests/unit/test_actions/test_click.py`
- `tests/unit/test_actions/test_screenshot.py`
- `tests/unit/test_actions/test_keyboard.py`
- `tests/unit/test_actions/test_scroll.py`
- `tests/unit/test_actions/test_window_mgmt.py`
- `tests/unit/test_actions/__init__.py`
- `tests/unit/test_adapters/test_anthropic.py`
- `tests/unit/test_adapters/test_openai.py`
- `tests/unit/test_adapters/__init__.py`
- `tests/unit/test_server/test_server.py`
- `tests/unit/test_server/__init__.py`
- `tests/unit/__init__.py`

**상세:**
- `conftest.py`: `MockPlatformBackend` (전체 메서드 stub, 호출 기록 리스트), pytest markers 설정
- `test_cli.py`: argparse 파싱, JSON 출력 포맷, elapsed_ms/estimated_tokens 존재, 에러 핸들링
- `test_key_parser.py`: 단순 키 ("a"), 모디파이어 ("ctrl+s"), 조합 ("ctrl+shift+s"), F키, 특수 키
- `test_scaling.py`: api_scale 계산 (1920x1080→0.745, 3840x2160→0.409), api_to_screen/screen_to_api 왕복, DPI 변환
- `test_chain.py`: 순차 실행 (3개→executed=3), 에러 시 중단 (2번째 실패→executed=1), 빈 리스트
- `test_actions/*`: 각 핸들러의 validate (잘못된 params→ValueError) + execute (MockBackend 호출 확인)
- `test_adapters/*`: Anthropic 패스스루, OpenAI 전체 매핑 (click→left_click, keypress→key 등), 스크롤 변환, 키 이름 변환
- `test_server/*`: 프로토콜 테스트 (JSON-over-TCP), idle 타이머, mock backend

**검증:** `pytest tests/unit/ -v` → 전체 통과

---

### Agent C2: Integration Tests + Performance

**생성 파일:**
- `tests/integration/test_screenshot.py`
- `tests/integration/test_mouse.py`
- `tests/integration/test_keyboard.py`
- `tests/integration/test_ocr.py`
- `tests/integration/test_chain.py`
- `tests/integration/test_format.py`
- `tests/integration/test_performance.py`
- `tests/integration/__init__.py`
- `tests/fixtures/screenshots/` (빈 디렉토리 또는 샘플)
- `tests/fixtures/expected_ocr/` (빈 디렉토리 또는 샘플)
- `pytest.ini` 또는 `pyproject.toml` 내 pytest 설정 (`markers = integration`)

**상세:**
모든 테스트는 `subprocess.run(["computer-use", ...])` → stdout JSON 파싱 → assert.
`@pytest.mark.integration` 마커. 기본 skip: `-m "not integration"`.

- `test_screenshot.py`: CLI 캡처 → JSON status=success + 파일 존재 + PNG 유효성
- `test_mouse.py`: mouse_move → screenshot → 커서 위치 확인
- `test_keyboard.py`: type/key → screenshot → OCR로 결과 확인
- `test_ocr.py`: `screenshot --ocr` → 텍스트에 기대 문자열 포함
- `test_chain.py`: chain → executed 수 + 최종 파일 확인
- `test_format.py`: 동일 동작을 `--format anthropic` / `--format openai`로 비교
- `test_performance.py`: 벤치마크 + 리포트 테이블 출력

**test_performance.py 리포트:**
```
╔══════════════════════════╦════════════════╦════════════════╦═══════════╦════════╗
║ Test Case                ║ Fallback (ms)  ║ Server (ms)    ║ tokens    ║ Result ║
╠══════════════════════════╬════════════════╬════════════════╬═══════════╬════════╣
║ screenshot               ║   250          ║    42          ║   1,049   ║ PASS   ║
║ screenshot --region      ║   120          ║    25          ║     267   ║ PASS   ║
║ screenshot --ocr         ║  7,200         ║   820          ║      85   ║ PASS   ║
║ left_click               ║   110          ║    18          ║      12   ║ PASS   ║
║ status                   ║   130          ║    20          ║      80   ║ PASS   ║
║ windows                  ║    80          ║    12          ║      45   ║ PASS   ║
║ clipboard                ║    65          ║    10          ║      15   ║ PASS   ║
║ chain (3+screenshot)     ║   520          ║    85          ║   1,049   ║ PASS   ║
║ click --format openai    ║   115          ║    20          ║      12   ║ PASS   ║
╠══════════════════════════╬════════════════╬════════════════╬═══════════╬════════╣
║ Memory (fallback)        ║                ║                ║           ║  72MB  ║
║ Memory (server)          ║                ║                ║           ║  85MB  ║
║ Memory (server+OCR)      ║                ║                ║           ║ 320MB  ║
╚══════════════════════════╩════════════════╩════════════════╩═══════════╩════════╝
```

**PASS/FAIL 기준:**

| 작업 | Fallback | Server |
|---|---|---|
| screenshot | < 300ms | < 50ms |
| screenshot --region | < 150ms | < 30ms |
| screenshot --ocr | < 8s | < 1s |
| status | < 150ms | < 25ms |
| mouse/keyboard | < 150ms | < 30ms |
| Fallback memory | < 80MB | - |
| Server memory (no OCR) | - | < 100MB |
| Server memory (OCR, Win) | - | < 400MB |

**검증:** `pytest tests/integration/ -m integration -v` → 수동 실행

---

### Agent C3: SKILL.md

**생성 파일:**
- `skill/SKILL.md`

**상세:**

SKILL.md는 이 프로젝트의 **가장 핵심적인 파일**. LLM이 도구를 올바른 패턴으로 사용하도록 안내한다.

구조:
```markdown
---
name: computer-use
description: "Control mouse, keyboard, and capture screenshots.
Use when: (1) Take screenshots, (2) Click/drag/move mouse,
(3) Type text or press keyboard shortcuts, (4) Automate desktop interactions"
---

# Computer Use

## Quick Reference
(전체 21개 액션 테이블 + CLI 예시)

## Core Loop
0. Init - status로 환경 전체 파악 (최초 1회)
1. Locate - 타겟 앱이 활성창이 아니면 focus_window
2. See - screenshot으로 현재 화면 확인
3. Plan - 어떤 UI 요소를 어떻게 조작할지
4. Act - 하나의 액션 실행
5. Verify - screenshot으로 결과 확인
6. Repeat

## Coordinate Tips
(정중앙 노리기, 작은 버튼 확대, 좌상단=(0,0))

## When Actions Fail
(클릭 실패, UI 불일치, 타이핑 실패 대응)

## Token Optimization Guide
(status/windows/screenshot/region/cursor_region/ocr/chain/clipboard 판단 기준)

## Server Mode
(computer-use serve)

## Key Names
(modifiers, special, navigation, function, combos)
```

**검증 방법 (수동):**
LLM에게 SKILL.md 제공 후 아래 태스크 수행 테스트:

| 태스크 | 성공 기준 |
|---|---|
| 메모장 열고 "Hello World" 입력 후 저장 | 파일 생성됨 |
| 브라우저에서 URL 열기 | 페이지 로딩 완료 |
| 파일 탐색기에서 폴더 이동 | 원하는 폴더에 도착 |
| 설정 앱에서 설정 변경 | 설정값 변경됨 |

---

### Wave 3 머지

C1, C2, C3 결과를 main에 머지.
**충돌 없음**: C1은 `tests/unit/`과 `tests/conftest.py`, C2는 `tests/integration/`과 `tests/fixtures/`, C3는 `skill/SKILL.md`만 생성.

---

## 최종 검증 체크리스트

머지 완료 후 전체 검증:

```bash
# 1. 설치
pip install -e ".[dev]"

# 2. Unit tests
pytest tests/unit/ -v

# 3. 기능 검증 (수동)
computer-use status
computer-use screenshot
computer-use left_click --params '{"coordinate": [500, 300]}'
computer-use type --params '{"text": "test"}'
computer-use key --params '{"text": "ctrl+a"}'
computer-use windows
computer-use focus_window --params '{"process_name": "notepad.exe"}'
computer-use cursor_position
computer-use clipboard
computer-use screenshot --region 100,200,500,400
computer-use screenshot --cursor_region 200,300
computer-use chain --actions '[{"action":"left_click","params":{"coordinate":[500,300]}},{"action":"screenshot"}]'
computer-use click --format openai --params '{"x": 500, "y": 300, "button": "left"}'

# 4. Server mode
computer-use serve &
computer-use screenshot      # < 50ms
computer-use serve --stop

# 5. Integration tests (수동)
pytest tests/integration/ -m integration -v

# 6. OCR (optional dependency 설치 시)
pip install ".[ocr-windows]"  # 또는 ocr-macos
computer-use screenshot --ocr
```

---

## 에이전트별 소요 시간 추정

| 에이전트 | 예상 복잡도 | 비고 |
|---|---|---|
| Wave 0: Foundation | 중 | ABC + 스텁 + CLI 스켈레톤 |
| A1: Mouse | 중 | 5종 클릭 + 드래그 + 상태 |
| A2: Keyboard | 소 | 3개 핸들러 |
| A3: Screenshot+ | 중 | region/cursor_region/ocr 옵션 |
| A4: Window Mgmt | 소 | 5개 핸들러 (backend 위임) |
| A5: OCR | 중 | PaddleOCR + Vision 래핑 |
| A6: Adapters | 중 | OpenAI 매핑 테이블 |
| A7: Server | 대 | TCP 서버 + 프로토콜 + idle |
| A8: Chain | 소 | 순차 실행기 |
| B1: Windows BE | 대 | ctypes + pynput 전체 구현 |
| B2: macOS BE | 대 | pyobjc + pynput 전체 구현 |
| B3: CLI Integration | 대 | 모든 것 연결 + 스케일링 |
| C1: Unit Tests | 중 | MockBackend + 전체 핸들러 |
| C2: Integration | 중 | subprocess + 벤치마크 |
| C3: SKILL.md | 소 | 문서 작성 |

**총 에이전트**: 15개 (Wave 0: 1 + Wave 1: 8 + Wave 2: 3 + Wave 3: 3)
**병렬 최대폭**: Wave 1에서 8개 동시

---

## Dependencies

```toml
[project]
name = "computer-use"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pynput>=1.7.6",
    "mss>=9.0.0",
    "Pillow>=10.0.0",
]

[project.optional-dependencies]
ocr-windows = ["paddleocr>=2.7.0", "paddlepaddle>=2.5.0"]
ocr-macos = ["pyobjc-framework-Vision>=10.0", "pyobjc-framework-Quartz>=10.0", "pyobjc-framework-Cocoa>=10.0"]
dev = ["pytest>=8.0", "pytest-mock>=3.12", "ruff>=0.4.0", "mypy>=1.10"]

[project.scripts]
computer-use = "computer_use.cli:main"
```
