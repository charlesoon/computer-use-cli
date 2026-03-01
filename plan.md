# Computer Use CLI - Implementation Plan

## Context

LLM 에이전트가 데스크톱을 원격 제어할 수 있는 크로스플랫폼 CLI 도구를 개발한다. **Anthropic Computer Use API(computer_20251124)와 OpenAI Computer Use(computer_use_preview)** 두 스펙을 모두 지원한다. Python CLI로 JSON stdout 출력을 통해 LLM이 Bash tool로 직접 호출할 수 있다. Windows와 macOS를 지원한다.

## Tech Stack

- **Language**: Python 3.10+
- **Screenshot**: mss (~3ms, PIL 대비 30-40x 빠름)
- **Input Control**: pynput (Win32/Quartz 자동 감지)
- **Image Resize**: Pillow (LANCZOS)
- **OCR**: Windows - PaddleOCR (CJK 94-97%, pip only), macOS - Vision framework (pyobjc, 내장 30+언어)
- **CLI**: argparse (stdlib, 외부 의존성 없음)
- **Build**: hatchling (PEP 517)

## Project Structure

```
computer_use/
├── pyproject.toml
├── .gitignore
├── src/
│   └── computer_use/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py                  # CLI 진입점, JSON 출력, 좌표 스케일링
│       ├── actions/
│       │   ├── __init__.py         # Action registry (@register 데코레이터)
│       │   ├── base.py             # ActionHandler ABC, ActionResult
│       │   ├── screenshot.py
│       │   ├── click.py            # left/right/middle/double/triple_click
│       │   ├── type_text.py
│       │   ├── key_press.py
│       │   ├── mouse_move.py
│       │   ├── scroll.py
│       │   ├── drag.py
│       │   ├── mouse_state.py      # left_mouse_down / left_mouse_up
│       │   ├── hold_key.py
│       │   ├── wait.py
│       │   ├── windows.py          # 보이는 윈도우 목록 (z-order, 제목, 프로세스, 좌표)
│       │   ├── focus_window.py     # 특정 윈도우를 전면으로 활성화
│       │   ├── cursor_position.py  # 현재 마우스 좌표
│       │   ├── clipboard.py        # 클립보드 읽기/쓰기
│       │   └── status.py           # 환경 전체 상태 일괄 조회
│       ├── platform/
│       │   ├── __init__.py         # get_backend() 팩토리
│       │   ├── base.py             # PlatformBackend ABC
│       │   ├── windows.py          # pynput + mss (Win32)
│       │   └── macos.py            # pynput + mss (Quartz)
│       ├── adapters/
│       │   ├── __init__.py         # get_adapter() 팩토리
│       │   ├── base.py             # FormatAdapter ABC
│       │   ├── anthropic.py        # Anthropic 파라미터 어댑터
│       │   └── openai.py           # OpenAI 파라미터 어댑터
│       ├── screenshot/
│       │   ├── __init__.py
│       │   ├── capture.py          # save_screenshot 유틸
│       │   └── scaling.py          # ScalingContext (좌표 변환)
│       ├── ocr/
│       │   ├── __init__.py         # get_ocr_engine() 팩토리
│       │   ├── base.py             # OCREngine ABC
│       │   ├── windows.py          # PaddleOCR (CJK 94-97%, 언어팩 불필요)
│       │   └── macos.py            # macOS Vision framework (내장 30+언어)
│       ├── server/
│       │   ├── __init__.py
│       │   ├── server.py           # TCP 소켓 서버 (모든 라이브러리 상주)
│       │   └── client.py           # CLI → 서버 위임 클라이언트
│       ├── chain.py                # Action chaining 실행기
│       └── key_parser.py           # "ctrl+s" → pynput Key 파싱
├── tests/
│   ├── conftest.py                 # MockPlatformBackend, pytest markers
│   ├── unit/                       # pytest (CI 가능, mock 기반)
│   │   ├── test_cli.py             # CLI 파싱 + JSON 출력
│   │   ├── test_key_parser.py      # 키 조합 파싱 로직
│   │   ├── test_scaling.py         # 좌표 스케일링 수학
│   │   ├── test_chain.py           # 액션 체이닝 로직
│   │   ├── test_actions/           # 모든 핸들러 (mock backend)
│   │   │   ├── test_click.py
│   │   │   ├── test_screenshot.py
│   │   │   └── ...
│   │   ├── test_adapters/          # 포맷 변환 (순수 데이터)
│   │   │   ├── test_anthropic.py
│   │   │   └── test_openai.py
│   │   ├── test_ocr/               # OCR 엔진 로직
│   │   │   └── test_*.py
│   │   └── test_server/            # 서버/클라이언트 프로토콜
│   │       └── test_server.py
│   ├── integration/                # @pytest.mark.integration (실제 머신 수동)
│   │   ├── test_screenshot.py      # 실제 캡처 + 파일 생성
│   │   ├── test_mouse.py           # 실제 커서 이동/클릭
│   │   ├── test_keyboard.py        # 실제 키 입력
│   │   ├── test_ocr.py             # 실제 OCR 엔진 추론
│   │   └── test_performance.py     # 응답 시간/메모리 기준 검증
│   └── fixtures/                   # 테스트용 정적 데이터
│       ├── screenshots/            # 미리 캡처한 스크린샷 (OCR 테스트용)
│       │   ├── english_ui.png
│       │   ├── korean_ui.png
│       │   └── mixed_lang.png
│       └── expected_ocr/           # OCR 기대 결과 텍스트
│           ├── english_ui.txt
│           ├── korean_ui.txt
│           └── mixed_lang.txt
└── skill/
    └── SKILL.md                    # LLM 사용 가이드
```

## Architecture

### Pattern: Registry + Strategy + Adapter

- **Action Registry** (OCP): `@register` 데코레이터로 핸들러 등록. 새 액션 = 새 파일 추가만으로 확장
- **Platform Strategy** (DIP): `PlatformBackend` ABC에 의존, `get_backend()` 팩토리가 OS별 구현 주입
- **Format Adapter** (OCP/DIP): `FormatAdapter` ABC로 Anthropic/OpenAI 파라미터 변환. 새 포맷 = 새 어댑터 파일 추가
- **Server + Fallback**: 서버 실행 중이면 위임(빠름), 없으면 직접 실행(느리지만 동작)
- **Boundary Scaling**: 좌표 스케일링은 CLI 레이어에서 처리, 핸들러는 스크린 좌표만 취급 (SRP)

### Core Abstractions

**PlatformBackend ABC** (`platform/base.py`):
- `get_monitors() -> list[MonitorInfo]` (index, primary, logical/physical size, dpi_scale, position)
- `get_screen_info(monitor) -> ScreenInfo` (logical_width, logical_height, dpi_scale)
- `get_windows() -> list[WindowInfo]` (z-order순, title, process_name, pid, bounds, is_minimized)
- `get_active_window() -> WindowInfo | None` (현재 포커스된 윈도우)
- `focus_window(pid, title) -> bool` (윈도우를 전면으로 활성화)
- `get_cursor_position() -> (x, y)` (논리 좌표)
- `get_clipboard() -> str`, `set_clipboard(text)` (클립보드 읽기/쓰기)
- `move_mouse(x, y)`, `click(x, y, button, count, modifier_keys)`
- `mouse_down/up(x, y, button)`, `drag(start_x, start_y, end_x, end_y)`
- `type_text(text)`, `press_key(key)`, `hold_key(key, duration)`
- `scroll(x, y, direction, amount, modifier_keys)`
- `capture_screenshot(monitor_index) -> bytes` (PNG, 물리 해상도)

**ActionHandler ABC** (`actions/base.py`):
- `validate(params)` → ValueError on invalid
- `execute(params, backend, screenshot_dir) -> ActionResult`
- `ActionResult`: `success: bool`, `data: dict`, `error: str | None`

**FormatAdapter ABC** (`adapters/base.py`):
- `normalize(action, params) -> (canonical_action, canonical_params)`: 외부 포맷 → 내부 정규화
- `denormalize_result(action, result) -> dict`: 내부 결과 → 외부 포맷 JSON

내부 정규화 포맷은 Anthropic 스펙 기반 (coordinate 배열, direction+amount 스크롤 등)

### Token Optimization Features

스크린샷이 토큰의 90%+를 차지 (1024x768 = ~1,049 토큰/장). 3가지 최적화로 비용 대폭 절감:

**1. Region Capture (`--region`, `--cursor_region`)**
전체 화면 대신 관심 영역만 캡처. 두 가지 모드:
- `--region x,y,w,h`: 절대 좌표로 영역 지정
- `--cursor_region w,h`: 현재 마우스 위치 중심으로 w×h 영역 캡처 (컨텍스트 메뉴, 툴팁 확인에 최적)
- 500x400 영역 = ~267 토큰 vs 전체 ~1,049 토큰 (75% 절감)
- `capture.py`의 mss `monitor` 파라미터로 영역 지정
- cursor_region은 마우스 위치를 자동 조회하여 region으로 변환 (화면 경계 클램핑 포함)

**2. Action Chaining (`chain`)**
여러 액션을 한 번에 실행, 마지막에만 스크린샷. 별도 서브커맨드.
- 중간 LLM 추론 토큰 + 불필요한 스크린샷 제거
- `chain.py`가 액션 리스트를 순차 실행, 최종 결과만 반환
- 개별 액션 실패 시 즉시 중단 + 에러 반환

**3. OCR Mode (`--ocr`)**
이미지 대신 텍스트로 화면 내용 반환. `screenshot` 액션의 `--ocr` 옵션.
- 이미지 1,049 토큰 → 텍스트 ~100 토큰 (90% 절감)
- 플랫폼별 최적 엔진 사용 (pip만으로 설치, 언어팩 불필요):
  - Windows: PaddleOCR (CJK 94-97% 정확도, 자동 언어 감지)
  - macOS: Vision framework (OS 내장 30+언어, 95%+ CJK 정확도)
- `--ocr`과 `--region` 조합 가능: 영역 OCR

**OCREngine ABC** (`ocr/base.py`):
- `recognize(image_bytes) -> str`: PNG bytes → 인식된 텍스트
- Platform Strategy 패턴으로 OS별 구현 주입

### Window Management (확장 기능)

Anthropic/OpenAI Computer Use API에 없는 **우리만의 확장 액션**.
SKILL.md에 사용법을 안내하여 LLM이 활용. 스크린샷 없이 앱 위치 파악 → 토큰 대폭 절약.

**`windows` 액션:**
- 보이는 윈도우를 z-order(전면→후면) 순서로 반환
- 각 윈도우: title, process_name, pid, bounds [x, y, w, h], is_minimized
- 최소화된 윈도우도 포함 (is_minimized=true)
- 시스템 tray, 도구 윈도우, 제목 없는 윈도우 제외

**`focus_window` 액션:**
- process_name, title, pid 중 하나로 대상 지정
- 최소화된 윈도우는 복원 후 전면 전환
- 복수 매칭 시 z-order 최상위 윈도우 선택

**플랫폼 구현:**
- **Windows**: ctypes only (추가 의존성 없음)
  - `EnumWindows` (z-order 보존), `GetWindowRect`, `GetWindowTextW`
  - `GetWindowThreadProcessId` + `OpenProcess` + `GetModuleBaseNameW` (프로세스명)
  - `AttachThreadInput` + `SetForegroundWindow` + `ShowWindow(SW_RESTORE)` (활성화)
  - DPI-aware: `SetProcessDPIAware()` 호출하여 정확한 좌표 반환
- **macOS**: pyobjc (이미 OCR용으로 의존)
  - `CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly)` (z-order 보존)
  - `kCGWindowLayer == 0`만 필터 (일반 윈도우만, 메뉴바/오버레이 제외)
  - `NSRunningApplication.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)`

### CLI Usage & JSON Output

```bash
computer-use <action> --params '<json>' [--format anthropic|openai] [--screenshot-dir <path>]
```

**Anthropic 형식 (기본, `--format anthropic`):**
```bash
computer-use screenshot
computer-use left_click --params '{"coordinate": [500, 300]}'
computer-use type --params '{"text": "Hello"}'
computer-use key --params '{"text": "ctrl+s"}'
computer-use scroll --params '{"coordinate": [500, 400], "scroll_direction": "down", "scroll_amount": 3}'
computer-use left_click_drag --params '{"start_coordinate": [100, 100], "coordinate": [400, 400]}'
computer-use left_mouse_down --params '{"coordinate": [300, 200]}'
computer-use left_mouse_up --params '{"coordinate": [500, 400]}'
computer-use hold_key --params '{"text": "shift", "duration": 2.0}'
computer-use wait --params '{"duration": 1.5}'
```

**환경 조회 + 윈도우 관리 (확장 액션 - Anthropic/OpenAI 스펙에 없는 우리만의 기능):**
```bash
# 환경 전체 상태 일괄 조회 (모니터 + 윈도우 + 커서 + 활성창)
computer-use status

# 보이는 윈도우 목록 조회 (z-order, 제목, 프로세스, 좌표)
computer-use windows

# 특정 윈도우를 전면으로 활성화 (프로세스명 또는 제목으로)
computer-use focus_window --params '{"process_name": "notepad.exe"}'
computer-use focus_window --params '{"title": "Untitled - Notepad"}'
computer-use focus_window --params '{"pid": 12345}'

# 현재 마우스 좌표 조회
computer-use cursor_position

# 클립보드 읽기/쓰기
computer-use clipboard                                    # 현재 클립보드 내용 읽기
computer-use clipboard --params '{"text": "복사할 텍스트"}'  # 클립보드에 쓰기
```

**Status response (환경 전체 상태 일괄 조회):**
```json
{
  "status": "success",
  "action": "status",
  "elapsed_ms": 15,
  "estimated_tokens": 80,
  "data": {
    "monitors": [
      {"index": 0, "primary": true, "logical": [1920, 1080], "physical": [3840, 2160], "dpi_scale": 2.0, "position": [0, 0]},
      {"index": 1, "primary": false, "logical": [1920, 1080], "physical": [1920, 1080], "dpi_scale": 1.0, "position": [1920, 0]}
    ],
    "active_window": {"title": "computer_use – cli.py", "process_name": "Code.exe", "pid": 1234, "bounds": [0, 0, 1920, 1040]},
    "cursor": [960, 540],
    "windows": [
      {"z_order": 0, "title": "computer_use – cli.py", "process_name": "Code.exe", "pid": 1234, "bounds": [0, 0, 1920, 1040], "is_minimized": false},
      {"z_order": 1, "title": "Untitled - Notepad", "process_name": "notepad.exe", "pid": 5678, "bounds": [100, 50, 800, 600], "is_minimized": false},
      {"z_order": 2, "title": "File Explorer", "process_name": "explorer.exe", "pid": 9012, "bounds": [200, 100, 1000, 700], "is_minimized": true}
    ]
  }
}
```

**Cursor position response:**
```json
{
  "status": "success",
  "action": "cursor_position",
  "elapsed_ms": 3,
  "estimated_tokens": 8,
  "data": {
    "coordinate": [960, 540]
  }
}
```

**Clipboard response (읽기):**
```json
{
  "status": "success",
  "action": "clipboard",
  "elapsed_ms": 5,
  "estimated_tokens": 15,
  "data": {
    "text": "클립보드에 있던 텍스트"
  }
}
```

**Clipboard response (쓰기):**
```json
{
  "status": "success",
  "action": "clipboard",
  "elapsed_ms": 5,
  "estimated_tokens": 8,
  "data": {
    "written": true
  }
}
```

**Windows response:**
```json
{
  "status": "success",
  "action": "windows",
  "elapsed_ms": 8,
  "estimated_tokens": 45,
  "data": {
    "windows": [
      {"z_order": 0, "title": "computer_use – cli.py", "process_name": "Code.exe", "pid": 1234, "bounds": [0, 0, 1920, 1040], "is_minimized": false},
      {"z_order": 1, "title": "Untitled - Notepad", "process_name": "notepad.exe", "pid": 5678, "bounds": [100, 50, 800, 600], "is_minimized": false},
      {"z_order": 2, "title": "File Explorer", "process_name": "explorer.exe", "pid": 9012, "bounds": [200, 100, 1000, 700], "is_minimized": true}
    ]
  }
}
```

**Focus window response:**
```json
{
  "status": "success",
  "action": "focus_window",
  "elapsed_ms": 15,
  "estimated_tokens": 12,
  "data": {
    "title": "Untitled - Notepad",
    "process_name": "notepad.exe",
    "pid": 5678
  }
}
```

**Token Optimization:**
```bash
# Region Capture: 관심 영역만 캡처 (x, y, width, height)
computer-use screenshot --region 100,200,500,400

# Cursor Region: 현재 마우스 위치 중심으로 캡처 (width, height)
computer-use screenshot --cursor_region 200,300       # 우클릭 후 컨텍스트 메뉴 확인에 최적

# OCR Mode: 이미지 대신 텍스트 반환
computer-use screenshot --ocr
computer-use screenshot --ocr --region 0,0,800,200   # 영역 OCR 조합
computer-use screenshot --ocr --cursor_region 300,200 # 마우스 근처 텍스트만 읽기

# Action Chaining: 여러 액션 일괄 실행, 최종 스크린샷 1장
computer-use chain --actions '[
  {"action": "left_click", "params": {"coordinate": [500, 300]}},
  {"action": "type", "params": {"text": "hello world"}},
  {"action": "key", "params": {"text": "return"}},
  {"action": "screenshot"}
]'

# Chaining + Region + OCR 조합
computer-use chain --actions '[
  {"action": "left_click", "params": {"coordinate": [500, 300]}},
  {"action": "screenshot", "params": {"ocr": true, "region": [0, 0, 800, 200]}}
]'
```

**OpenAI 형식 (`--format openai`):**
```bash
computer-use screenshot --format openai
computer-use click --format openai --params '{"x": 500, "y": 300, "button": "left"}'
computer-use double_click --format openai --params '{"x": 200, "y": 150}'
computer-use type --format openai --params '{"text": "Hello"}'
computer-use keypress --format openai --params '{"keys": ["Control", "s"]}'
computer-use scroll --format openai --params '{"x": 500, "y": 400, "scroll_x": 0, "scroll_y": -3}'
computer-use drag --format openai --params '{"path": [[100, 100], [400, 400]]}'
computer-use mouse_move --format openai --params '{"x": 400, "y": 300}'
computer-use wait --format openai --params '{"duration": 1.5}'
```

**모든 응답에 공통 필드:**
- `elapsed_ms`: CLI 프로세스 시작 ~ JSON 출력 직전까지 소요 시간
- `estimated_tokens`: 이 응답이 LLM에게 전달될 때 예상 토큰 수

토큰 추정 공식:
- 스크린샷 이미지: `(width × height) / 750` (Claude 기준)
- OCR 텍스트: `len(text) / 4` (영어 기준 근사, 한국어는 문자당 ~2토큰)
- JSON 텍스트: `len(json_str) / 4`
- 액션 응답 (이미지 없음): JSON 텍스트 토큰만

**Screenshot response:**
```json
{
  "status": "success",
  "action": "screenshot",
  "elapsed_ms": 142,
  "estimated_tokens": 1049,
  "data": {
    "screenshot_path": "/tmp/computer_use/screenshot_20260301.png",
    "display_width": 1024,
    "display_height": 768
  }
}
```

**Action response (이미지 없음):**
```json
{
  "status": "success",
  "action": "left_click",
  "elapsed_ms": 45,
  "estimated_tokens": 12,
  "data": {
    "coordinate": [500, 300]
  }
}
```

**OCR response:**
```json
{
  "status": "success",
  "action": "screenshot",
  "elapsed_ms": 1230,
  "estimated_tokens": 85,
  "data": {
    "text": "File  Edit  View  Help\nUntitled - Notepad\nHello world",
    "region": [0, 0, 800, 200]
  }
}
```

**Chain response:**
```json
{
  "status": "success",
  "action": "chain",
  "elapsed_ms": 1580,
  "estimated_tokens": 1049,
  "data": {
    "executed": 4,
    "last_action": "screenshot",
    "screenshot_path": "/tmp/computer_use/screenshot_20260301.png",
    "display_width": 1024,
    "display_height": 768
  }
}
```

**Error response:**
```json
{
  "status": "error",
  "action": "left_click",
  "elapsed_ms": 38,
  "estimated_tokens": 18,
  "error": "Coordinates (1500, 900) are outside display bounds (1280x800)"
}
```

### Format Adapter: OpenAI ↔ Internal Mapping

OpenAI 파라미터를 내부 정규화 포맷(Anthropic 기반)으로 변환하는 매핑:

| OpenAI Action | OpenAI Params | → Internal Action | → Internal Params |
|---|---|---|---|
| `click` | `x, y, button:"left"` | `left_click` | `coordinate: [x, y]` |
| `click` | `x, y, button:"right"` | `right_click` | `coordinate: [x, y]` |
| `click` | `x, y, button:"middle"` | `middle_click` | `coordinate: [x, y]` |
| `double_click` | `x, y` | `double_click` | `coordinate: [x, y]` |
| `type` | `text` | `type` | `text` (동일) |
| `keypress` | `keys: ["Control", "s"]` | `key` | `text: "ctrl+s"` (join +) |
| `scroll` | `x, y, scroll_x, scroll_y` | `scroll` | `coordinate, scroll_direction, scroll_amount` |
| `drag` | `path: [[x1,y1],[x2,y2]]` | `left_click_drag` | `start_coordinate, coordinate` |
| `mouse_move` | `x, y` | `mouse_move` | `coordinate: [x, y]` |
| `screenshot` | - | `screenshot` | - (동일) |
| `wait` | `duration` | `wait` | `duration` (동일) |

**스크롤 변환 로직:**
- `scroll_y < 0` → `direction: "down"`, `amount: abs(scroll_y)`
- `scroll_y > 0` → `direction: "up"`, `amount: scroll_y`
- `scroll_x < 0` → `direction: "left"`, `amount: abs(scroll_x)`
- `scroll_x > 0` → `direction: "right"`, `amount: scroll_x`

**키 이름 변환 (OpenAI → Internal):**
- `"Control"` → `"ctrl"`, `"Meta"` → `"super"`, `"ArrowUp"` → `"up"`, `"Enter"` → `"return"` 등

### Coordinate Scaling + Display Handling

#### 4K / HiDPI 대응

mss는 물리 해상도(3840x2160)로 캡처하지만, LLM에게는 **논리 해상도 기준** 스크린샷을 전달해야 한다.
사용자가 보는 화면 = 논리 해상도. 클릭 좌표도 논리 해상도 기준으로 동작.

```
물리: 3840x2160 (mss 캡처)
      ↓ DPI scale factor (200%) 적용하여 리사이즈
논리: 1920x1080
      ↓ API scale 적용 (max 1568px)
API:  1430x804 (LLM이 보는 스크린샷)
```

**DPI scale factor 감지:**
- Windows: `ctypes.windll.shcore.GetProcessDpiAwareness` + `GetDeviceCaps`
- macOS: `NSScreen.backingScaleFactor` (Retina = 2.0)

**좌표 변환 체인:**
```
LLM 좌표 (API space)
  → ÷ api_scale → 논리 좌표 (logical space)
  → × dpi_scale → 물리 좌표 (physical space, 실제 클릭 위치)
```

**예시 (4K, 200% 스케일링):**
```
물리: 3840x2160 → 논리: 1920x1080 → API: 1430x804
LLM이 (715, 402) 클릭
  → 논리: (960, 540) [÷ 0.745]
  → 물리: (1920, 1080) [× 2.0]
  = 화면 정중앙 ✓
```

**예시 (1920x1080, 100% 스케일링):**
```
물리 = 논리: 1920x1080 → API: 1430x804
LLM이 (715, 402) 클릭
  → 논리/물리: (960, 540) [÷ 0.745, × 1.0]
  = 화면 정중앙 ✓
```

#### 멀티 모니터

**`--monitor` 옵션으로 대상 모니터 지정** (기본: 프라이머리 = 0):

```bash
computer-use screenshot                     # 프라이머리 모니터 (기본)
computer-use screenshot --monitor 1         # 두 번째 모니터
computer-use monitors                       # 모니터 목록 조회
```

**`monitors` 액션 응답:**
```json
{
  "status": "success",
  "action": "monitors",
  "data": {
    "monitors": [
      {"index": 0, "primary": true, "logical": [1920, 1080], "physical": [3840, 2160], "dpi_scale": 2.0, "position": [0, 0]},
      {"index": 1, "primary": false, "logical": [1920, 1080], "physical": [1920, 1080], "dpi_scale": 1.0, "position": [1920, 0]}
    ]
  }
}
```

**좌표 체계:** 각 모니터는 독립된 좌표계.
- `--monitor 0`에서 클릭 (500, 300) → 모니터 0의 논리 좌표 (500, 300)
- `--monitor 1`에서 클릭 (500, 300) → 모니터 1의 논리 좌표 (500, 300)
- 모니터 간 절대 좌표 변환은 `monitors` 응답의 `position`으로 계산

**screenshot 응답에 모니터 정보 포함:**
```json
{
  "status": "success",
  "action": "screenshot",
  "data": {
    "screenshot_path": "...",
    "monitor": 0,
    "logical_width": 1920,
    "logical_height": 1080,
    "display_width": 1430,
    "display_height": 804,
    "dpi_scale": 2.0
  }
}
```

**API scale 공식** (논리 해상도 기준으로 적용):
```
api_scale = min(1.0, 1568/max(logical_w, logical_h), sqrt(1150000/(logical_w × logical_h)))
```

## Performance Criteria

### 응답 시간 기준 (e2e = subprocess 시작 ~ stdout 수신)

| 작업 | Fallback (서버 없음) | Server 모드 | 비고 |
|---|---|---|---|
| screenshot | < 300ms | **< 50ms** | 서버: 소켓 통신 + mss + resize |
| screenshot --region | < 150ms | **< 30ms** | 영역 캡처, 리사이즈 부하 감소 |
| screenshot --ocr | < 8초 (cold) | **< 1초** | 서버: 모델 이미 로딩 |
| status | < 150ms | **< 25ms** | 서버: monitors + windows + cursor 일괄 |
| windows / focus_window | < 100ms | **< 20ms** | 서버: ctypes/pyobjc 즉시 호출 |
| cursor_position / clipboard | < 80ms | **< 15ms** | 서버: 즉시 호출 |
| mouse/keyboard 액션 | < 150ms | **< 30ms** | 서버: 소켓 통신 + pynput |
| chain (N 액션) | < N×150ms + screenshot | **< N×10ms + screenshot** | 서버: import 오버헤드 없음 |
| serve 시작 (OCR 포함) | - | **< 10초** | PaddleOCR 모델 로딩 1회 |
| serve 시작 (OCR 제외) | - | **< 1초** | mss + pynput + Pillow만 |

### 메모리 기준

| 모드 | 목표 | 비고 |
|---|---|---|
| Fallback (직접 실행) | **< 80MB** | mss + pynput + Pillow, 프로세스 종료 시 해제 |
| Server (OCR 없이) | **< 100MB** | mss + pynput + Pillow 상주 |
| Server (OCR 포함, Win) | **< 400MB** | + PaddleOCR 모델 상주 |
| Server (OCR 포함, Mac) | **< 200MB** | + Vision framework (OS 공유) |
| Server idle 자동 종료 | **5분** | 메모리 자동 해제 |

### Server Mode 아키텍처

모든 라이브러리(mss, pynput, Pillow, PaddleOCR)를 미리 로딩한 상주 서버.
CLI는 서버가 있으면 위임(빠름), 없으면 직접 실행(fallback).

```
[Server Process - 상주]              [CLI Client - 매 호출마다 생성/종료]
 │ mss, pynput, Pillow 로딩 완료     │
 │ PaddleOCR 모델 로딩 완료 (OCR용)  │
 │                                    │
 │◄── 소켓 요청 ──────────────────── │ $ computer-use screenshot
 │── 캡처 + 리사이즈 (3ms+50ms)      │
 │── JSON 응답 ───────────────────► │ stdout 출력 (e2e ~15ms)
 │                                    │
 │◄── 소켓 요청 ──────────────────── │ $ computer-use left_click --params ...
 │── 클릭 실행 (1ms)                  │
 │── JSON 응답 ───────────────────► │ stdout 출력 (e2e ~15ms)
 │                                    │
 │◄── 소켓 요청 ──────────────────── │ $ computer-use screenshot --ocr
 │── 캡처 + OCR 추론 (500ms)         │
 │── JSON 응답 ───────────────────► │ stdout 출력 (e2e ~520ms)
 │                                    │
 │ (5분 idle)                         │
 │ 자동 종료, 메모리 해제             │
```

**Fallback 동작 (서버 없을 때):**
```
$ computer-use screenshot          → 직접 실행 (~200ms, 서버 대비 느리지만 동작)
$ computer-use screenshot --ocr    → 직접 실행 (~7초, PaddleOCR 콜드 스타트 포함)
```

**구현:**
- `server/server.py` - localhost TCP 소켓 서버, 전체 실행 엔진 내장
- `server/client.py` - 서버 연결 → 명령 전송 → 응답 수신 (얇은 클라이언트)
- 서버 상태 파일: `~/.computer_use/server.json` (PID, port)
- `computer-use serve [--port PORT]` 서버 시작
- `computer-use serve --stop` 서버 종료
- `computer-use serve --status` 상태 확인

**CLI 실행 흐름 (`cli.py`):**
1. args 파싱
2. `server/client.py`로 서버 소켓 연결 시도
3. 연결 성공 → 명령 + params JSON 전송 → 응답 수신 → stdout 출력
4. 연결 실패 → fallback: 직접 backend 초기화 + 액션 실행 → stdout 출력

**서버가 OCR 데몬을 대체:**
- 서버에 모든 라이브러리가 상주하므로 별도 OCR 데몬 불필요
- `--ocr`도 서버 모드에서는 추가 콜드 스타트 없이 바로 추론

## Implementation Phases

### Phase 1: Foundation (Core + Screenshot)
- [ ] `pyproject.toml`, `.gitignore` 생성
- [ ] `platform/base.py` - PlatformBackend ABC, ScreenInfo, MousePosition
- [ ] `actions/base.py` - ActionHandler ABC, ActionResult
- [ ] `actions/__init__.py` - registry + @register
- [ ] `screenshot/scaling.py` - ScalingContext
- [ ] `screenshot/capture.py` - save_screenshot
- [ ] `actions/screenshot.py` - ScreenshotHandler
- [ ] `platform/windows.py` - WindowsBackend (capture + screen_info)
- [ ] `cli.py` + `__main__.py` + `__init__.py`
- [ ] **검증**: `computer-use screenshot` → JSON + 파일

### Phase 2: Mouse Actions
- [ ] `actions/mouse_move.py` - MouseMoveHandler
- [ ] `actions/click.py` - 5종 클릭 (BaseClickHandler 상속)
- [ ] `actions/drag.py` - LeftClickDragHandler
- [ ] `actions/mouse_state.py` - MouseDown/UpHandler
- [ ] `platform/windows.py` 마우스 메서드 완성
- [ ] `platform/macos.py` 생성 + 마우스 메서드
- [ ] **검증**: 모든 마우스 액션 동작 확인

### Phase 3: Keyboard Actions
- [ ] `key_parser.py` - parse_key_combination + KEY_NAME_MAP
- [ ] `actions/type_text.py` - TypeTextHandler
- [ ] `actions/key_press.py` - KeyPressHandler
- [ ] `actions/hold_key.py` - HoldKeyHandler
- [ ] 양 플랫폼 키보드 메서드 완성
- [ ] **검증**: 키보드 액션 동작 확인

### Phase 4: Scroll + Wait
- [ ] `actions/scroll.py` - ScrollHandler
- [ ] `actions/wait.py` - WaitHandler
- [ ] 양 플랫폼 스크롤 메서드 완성
- [ ] **검증**: 전체 14개 액션 동작 확인

### Phase 5: Environment Query + Window Management
- [ ] `actions/cursor_position.py` - CursorPositionHandler (pynput mouse position → 논리 좌표)
- [ ] `actions/clipboard.py` - ClipboardHandler (읽기/쓰기, 플랫폼별 구현)
- [ ] `actions/windows.py` - WindowsListHandler (보이는 윈도우 z-order 순 반환)
- [ ] `actions/focus_window.py` - FocusWindowHandler (process_name/title/pid로 활성화)
- [ ] `actions/status.py` - StatusHandler (monitors + windows + cursor + active_window 일괄 조회)
- [ ] `platform/windows.py` - `get_windows()` (ctypes: EnumWindows + GetWindowRect + GetWindowTextW)
- [ ] `platform/windows.py` - `get_active_window()` (ctypes: GetForegroundWindow)
- [ ] `platform/windows.py` - `focus_window()` (ctypes: AttachThreadInput + SetForegroundWindow)
- [ ] `platform/windows.py` - `get_cursor_position()` / `get_clipboard()` / `set_clipboard()`
- [ ] `platform/macos.py` - `get_windows()` (pyobjc: CGWindowListCopyWindowInfo, z-order 보존)
- [ ] `platform/macos.py` - `focus_window()` (pyobjc: NSRunningApplication.activateWithOptions_)
- [ ] `platform/macos.py` - `get_active_window()` / `get_cursor_position()` / `get_clipboard()` / `set_clipboard()`
- [ ] **검증**: `computer-use status` → 전체 환경 JSON, `focus_window` → 윈도우 전면 전환, `clipboard` → 읽기/쓰기

### Phase 6: Token Optimization - Region + Chain
- [ ] `screenshot` 액션에 `--region x,y,w,h` 옵션 추가 (mss 영역 캡처)
- [ ] `chain.py` - ChainExecutor (액션 리스트 순차 실행, 에러 시 중단)
- [ ] `cli.py`에 `chain` 서브커맨드 추가
- [ ] **검증**: region < 100ms, chain N 액션 < N×100ms + screenshot

### Phase 7: OCR
- [ ] `ocr/base.py` - OCREngine ABC (`recognize(image_bytes) -> str`)
- [ ] `ocr/windows.py` - WindowsOCR (PaddleOCR, `use_angle_cls=False`, `enable_mkldnn=True`)
- [ ] `ocr/macos.py` - MacOSOCR (pyobjc Vision framework)
- [ ] `ocr/__init__.py` - `get_ocr_engine()` 팩토리
- [ ] `screenshot` 액션에 `--ocr` 옵션 + `--region` 조합 지원
- [ ] **검증**: fallback 모드에서 OCR 동작 확인

### Phase 8: Server Mode
- [ ] `server/server.py` - TCP 소켓 서버 (전체 실행 엔진 내장, idle 5분 자동 종료)
- [ ] `server/client.py` - 서버 연결 → 명령 전송 → 응답 수신 클라이언트
- [ ] `cli.py`에 서버 우선/fallback 로직 통합
- [ ] `cli.py`에 `serve [--port] [--stop] [--status]` 서브커맨드
- [ ] 서버 상태 파일: `~/.computer_use/server.json` (PID, port)
- [ ] 서버에 OCR 엔진 lazy loading (첫 `--ocr` 요청 시 로딩)
- [ ] **검증**: serve 시작 → CLI 호출 < 50ms, OCR < 1초, idle 5분 자동 종료

### Phase 9: Format Adapters (Anthropic + OpenAI)
- [ ] `adapters/base.py` - FormatAdapter ABC (`normalize`, `denormalize_result`)
- [ ] `adapters/anthropic.py` - AnthropicAdapter (패스스루, 내부 포맷 = Anthropic 기반)
- [ ] `adapters/openai.py` - OpenAIAdapter (액션명 + 파라미터 변환)
- [ ] `adapters/__init__.py` - `get_adapter(format_name)` 팩토리
- [ ] `cli.py`에 `--format` 플래그 + 어댑터 통합
- [ ] OpenAI 키 이름 매핑 (`"Control"` → `"ctrl"`, `"Meta"` → `"super"` 등)
- [ ] **검증**: 동일 동작을 Anthropic/OpenAI 두 형식으로 실행

### Phase 10: Coordinate Scaling + Display
- [ ] `ScalingContext` 확장: 물리→논리→API 3단계 변환 체인
- [ ] 플랫폼별 DPI scale factor 감지 (Windows: shcore API, macOS: NSScreen)
- [ ] mss 물리 캡처 → 논리 해상도로 리사이즈 → API 스케일 적용
- [ ] 좌표 역변환: API → 논리 → 물리 (클릭/드래그 등)
- [ ] `monitors` 액션 추가 (모니터 목록, 해상도, DPI, 위치)
- [ ] `screenshot --monitor N` 옵션
- [ ] screenshot 응답에 monitor, logical_width/height, dpi_scale 포함
- [ ] **검증**: 4K(200%) + FHD(100%) 듀얼모니터에서 양쪽 정확한 좌표 클릭

### Phase 11: Polish + Skill
- [ ] macOS 접근성 권한 체크 + 에러 메시지
- [ ] `skill/SKILL.md` 작성 (아래 SKILL.md 설계 참조)
- [ ] **검증**: LLM에게 SKILL.md 제공 후 실제 태스크 수행 테스트

### Phase 12: Tests

**Unit Tests** (`tests/unit/`, CI 가능, mock 기반):
- [ ] `test_cli.py` - CLI 파싱, JSON 출력 포맷, 에러 핸들링
- [ ] `test_key_parser.py` - 키 조합 파싱 ("ctrl+s", "Return", F키 등)
- [ ] `test_scaling.py` - scale factor 계산, api_to_screen/screen_to_api 변환
- [ ] `test_actions/` - 모든 21개 핸들러: validate + execute (MockPlatformBackend)
- [ ] `test_adapters/` - Anthropic 패스스루, OpenAI→Internal 변환 (액션명, 좌표, 키, 스크롤)
- [ ] `test_chain.py` - 순차 실행, 에러 시 중단, 마지막 결과 반환
- [ ] `test_ocr/` - OCR 엔진 로직 (mock image → 텍스트 변환)
- [ ] `test_server/test_server.py` - 서버 프로토콜 (start/stop/요청/idle 타이머, mock backend)
- [ ] **실행**: `pytest tests/unit/` → CI에서 자동

**Integration Tests** (`tests/integration/`, CLI subprocess 실행, 실제 머신 수동):

모든 테스트가 `subprocess.run(["computer-use", ...])` → stdout JSON 파싱 → assert.
LLM이 Bash tool로 호출하는 것과 동일한 방식으로 검증.

속도 측정 = subprocess 시작 ~ stdout 수신 (end-to-end, CLI 자체 `elapsed_ms`도 검증).
각 테스트 결과에 응답 속도, 예상 토큰량 포함.

- [ ] `test_screenshot.py` - CLI로 캡처 → JSON status + 파일 존재 + PNG 유효성
- [ ] `test_mouse.py` - CLI로 mouse_move → CLI로 screenshot → 스크린샷에서 커서 위치 변경 확인
- [ ] `test_keyboard.py` - CLI로 type/key → CLI로 screenshot → OCR로 입력 결과 확인
- [ ] `test_ocr.py` - CLI로 `screenshot --ocr` → 반환 텍스트에 기대 문자열 포함 확인
- [ ] `test_chain.py` - CLI로 chain → JSON executed 수 + 최종 screenshot 파일 확인
- [ ] `test_format.py` - 동일 동작을 `--format anthropic` / `--format openai`로 실행 → 결과 동일
- [ ] `test_performance.py` - 전체 벤치마크 + 리포트 생성 (아래 참조)
- [ ] **실행**: `pytest tests/integration/ -m integration` → 수동

**test_performance.py 리포트 출력:**

각 CLI 명령을 실행하고 subprocess 소요 시간 + JSON의 `elapsed_ms` + `estimated_tokens`를 수집하여 테이블 출력:

```
╔══════════════════════════════════╦════════════════════╦════════════════════╦═════════════╦════════╗
║ Test Case                        ║ Fallback e2e (ms)  ║ Server e2e (ms)    ║ est_tokens  ║ Result ║
╠══════════════════════════════════╬════════════════════╬════════════════════╬═════════════╬════════╣
║ screenshot                       ║   250              ║    42              ║   1,049     ║ PASS   ║
║ screenshot --region 0,0,500,400  ║   120              ║    25              ║     267     ║ PASS   ║
║ screenshot --ocr                 ║  7,200 (cold)      ║   820              ║      85     ║ PASS   ║
║ screenshot --ocr --region        ║  6,800 (cold)      ║   650              ║      42     ║ PASS   ║
║ left_click                       ║   110              ║    18              ║      12     ║ PASS   ║
║ type                             ║   105              ║    15              ║      12     ║ PASS   ║
║ key (ctrl+s)                     ║   100              ║    15              ║      12     ║ PASS   ║
║ mouse_move                       ║    95              ║    12              ║      12     ║ PASS   ║
║ scroll                           ║   108              ║    18              ║      12     ║ PASS   ║
║ status                           ║   130              ║    20              ║      80     ║ PASS   ║
║ windows                          ║    80              ║    12              ║      45     ║ PASS   ║
║ focus_window                     ║    85              ║    15              ║      12     ║ PASS   ║
║ cursor_position                  ║    60              ║     8              ║       8     ║ PASS   ║
║ clipboard (read)                 ║    65              ║    10              ║      15     ║ PASS   ║
║ chain (3 actions + screenshot)   ║   520              ║    85              ║   1,049     ║ PASS   ║
║ click --format openai            ║   115              ║    20              ║      12     ║ PASS   ║
╠══════════════════════════════════╬════════════════════╬════════════════════╬═════════════╬════════╣
║ Memory (fallback)                ║                    ║                    ║             ║  72MB  ║
║ Memory (server, no OCR)          ║                    ║                    ║             ║  85MB  ║
║ Memory (server, OCR loaded)      ║                    ║                    ║             ║ 320MB  ║
╚══════════════════════════════════╩════════════════════╩════════════════════╩═════════════╩════════╝

e2e: subprocess 시작 ~ stdout 수신 (Python time.perf_counter)
est_tokens: JSON 응답의 estimated_tokens
Fallback/Server 양쪽 모두 측정하여 비교
```

**PASS/FAIL 기준**: Performance Criteria 섹션의 목표값 초과 시 FAIL

**OCR Fixture Tests** (`tests/unit/test_ocr/`, CI 가능):
- [ ] 미리 캡처한 스크린샷(fixtures/)으로 OCR 정확도 검증 (디스플레이 불필요)
- [ ] 한국어/영어/혼합 텍스트 fixture 포함

**conftest.py 설정:**
- [ ] `MockPlatformBackend` (전체 메서드 stub, 호출 기록)
- [ ] `pytest.ini`: `markers = integration: requires real display`
- [ ] integration 기본 skip: `pytest.ini`에 `-m "not integration"` 기본값

## Dependencies

```toml
[project]
dependencies = [
    "pynput>=1.7.6",
    "mss>=9.0.0",
    "Pillow>=10.0.0",
]

[project.optional-dependencies]
ocr-windows = ["paddleocr>=2.7.0", "paddlepaddle>=2.5.0"]
ocr-macos = ["pyobjc-framework-Vision>=10.0"]
dev = ["pytest>=8.0", "pytest-mock>=3.12", "ruff>=0.4.0", "mypy>=1.10"]
```

> OCR은 optional dependency. `--ocr` 없이도 핵심 기능 정상 동작. OS별로 필요한 것만 설치.
> Windows PaddleOCR: 언어팩 없이 CJK 94-97% 정확도. macOS Vision: OS 내장 30+언어.

## Supported Actions

### Internal Actions (21)

| Action | Params | Description |
|--------|--------|-------------|
| `status` | - | 환경 전체 상태 일괄 조회 (모니터 + 윈도우 + 커서 + 활성창) |
| `monitors` | - | 모니터 목록 조회 (index, 해상도, DPI, 위치) |
| `windows` | - | 보이는 윈도우 목록 (z-order, 제목, 프로세스, 좌표) |
| `focus_window` | process_name \| title \| pid | 특정 윈도우를 전면으로 활성화 |
| `cursor_position` | - | 현재 마우스 좌표 (논리 좌표) |
| `clipboard` | [text] | 클립보드 읽기 (text 없음) / 쓰기 (text 있음) |
| `screenshot` | [monitor], [region], [cursor_region], [ocr] | 화면 캡처 → 파일 저장 |
| `left_click` | coordinate, [text] | 좌클릭 (modifier 지원) |
| `right_click` | coordinate | 우클릭 |
| `middle_click` | coordinate | 중간 클릭 |
| `double_click` | coordinate | 더블클릭 |
| `triple_click` | coordinate | 트리플클릭 |
| `type` | text | 텍스트 입력 |
| `key` | text | 키보드 단축키 (ctrl+s) |
| `mouse_move` | coordinate | 마우스 이동 |
| `scroll` | coordinate, scroll_direction, scroll_amount | 스크롤 |
| `left_click_drag` | start_coordinate, coordinate | 드래그 |
| `left_mouse_down` | coordinate | 마우스 버튼 누름 |
| `left_mouse_up` | coordinate | 마우스 버튼 놓음 |
| `hold_key` | text, duration | 키 홀드 |
| `wait` | duration | 대기 |

### Format Support Matrix

| Internal Action | Anthropic Action | OpenAI Action |
|---|---|---|
| `screenshot` | `screenshot` | `screenshot` |
| `left_click` | `left_click` | `click` (button:"left") |
| `right_click` | `right_click` | `click` (button:"right") |
| `middle_click` | `middle_click` | `click` (button:"middle") |
| `double_click` | `double_click` | `double_click` |
| `triple_click` | `triple_click` | - (미지원) |
| `type` | `type` | `type` |
| `key` | `key` | `keypress` |
| `mouse_move` | `mouse_move` | `mouse_move` |
| `scroll` | `scroll` | `scroll` |
| `left_click_drag` | `left_click_drag` | `drag` |
| `left_mouse_down` | `left_mouse_down` | - (미지원) |
| `left_mouse_up` | `left_mouse_up` | - (미지원) |
| `hold_key` | `hold_key` | - (미지원) |
| `wait` | `wait` | `wait` |
| `status` | - (확장) | - (확장) |
| `windows` | - (확장) | - (확장) |
| `focus_window` | - (확장) | - (확장) |
| `cursor_position` | - (확장) | - (확장) |
| `clipboard` | - (확장) | - (확장) |

> OpenAI에서 미지원하는 액션(triple_click, mouse_down/up, hold_key)은 OpenAI 포맷에서도 내부 액션명으로 직접 호출 가능
> `status`, `windows`, `focus_window`, `cursor_position`, `clipboard`는 양쪽 API 스펙에 없는 **확장 액션**. SKILL.md에서 사용법을 안내하여 LLM이 활용

## Verification

### 기능 검증
1. `pip install -e .` → CLI 설치
2. `computer-use screenshot` → JSON + 스크린샷 파일
3. `computer-use left_click --params '{"coordinate": [500, 300]}'` → 클릭 발생
4. `computer-use type --params '{"text": "test"}'` → 텍스트 입력
5. `computer-use key --params '{"text": "ctrl+a"}'` → 단축키 동작
6. `computer-use click --format openai --params '{"x": 500, "y": 300, "button": "left"}'` → Anthropic과 동일 동작
7. `computer-use keypress --format openai --params '{"keys": ["Control", "a"]}'` → Anthropic과 동일 동작
8. `computer-use screenshot --region 100,200,500,400` → 영역 캡처, 파일 크기 축소
9. `computer-use screenshot --cursor_region 200,300` → 마우스 위치 중심 영역 캡처
10. `computer-use screenshot --ocr` → 이미지 없이 텍스트 반환
11. `computer-use chain --actions '[{"action":"left_click","params":{"coordinate":[500,300]}},{"action":"screenshot"}]'` → 일괄 실행 + 스크린샷 1장
12. `computer-use status` → 모니터 + 윈도우 + 커서 + 활성창 JSON 일괄 반환
13. `computer-use windows` → 윈도우 목록 JSON (z-order, 제목, 프로세스, 좌표)
14. `computer-use focus_window --params '{"process_name": "notepad.exe"}'` → 메모장 전면 전환
15. `computer-use cursor_position` → 현재 마우스 좌표 JSON
16. `computer-use clipboard` → 클립보드 내용 읽기
17. `computer-use clipboard --params '{"text": "test"}'` → 클립보드에 쓰기
18. `computer-use serve --status` → 서버 상태 확인
19. `pytest tests/` → 전체 통과

### 성능 검증
20. `computer-use screenshot` → **< 200ms** (mss + resize + file I/O)
21. `computer-use screenshot --region 100,200,500,400` → **< 100ms**
22. `computer-use screenshot --cursor_region 200,300` → **< 100ms**
23. `computer-use left_click --params '{"coordinate":[500,300]}'` → **< 100ms**
24. `computer-use status` → **< 150ms** (monitors + windows + cursor 일괄)
25. `computer-use windows` → **< 30ms** (EnumWindows / CGWindowList)
26. `computer-use screenshot` (serve 모드) → **< 50ms**
27. `computer-use screenshot --ocr` (serve 모드) → **< 1초**
28. `computer-use screenshot --ocr` (fallback) → **< 8초**
29. Fallback 메모리 → **< 80MB**
30. Server 메모리 (OCR 포함, Win) → **< 400MB**
31. Server 5분 idle → 자동 종료 확인

### 4K / 멀티모니터 검증
32. `computer-use monitors` → 모니터 목록 + 해상도 + DPI 정보
33. 4K(200%) 모니터에서 `screenshot` → 논리 해상도(1920x1080) 기준 스크린샷
34. 4K에서 화면 정중앙 클릭 → 실제 정중앙에 클릭됨 (좌표 체인 검증)
35. `screenshot --monitor 1` → 두 번째 모니터 캡처
36. 서로 다른 DPI 모니터 간 좌표 정확도 검증

### 환경 조회 + 윈도우 관리 검증
37. `computer-use status` → 모니터 + 윈도우 + 커서 + 활성창 일괄 반환
38. `computer-use windows` → 보이는 윈도우 목록 (z-order 순서, 전면 윈도우가 z_order=0)
39. `focus_window` → 지정한 윈도우가 실제로 전면으로 전환됨 (screenshot으로 확인)
40. 최소화된 윈도우 → `is_minimized: true`로 표시, `focus_window` 시 복원됨
41. `clipboard` → 쓰기 후 읽기 → 동일 텍스트 반환
42. `cursor_position` → mouse_move 후 좌표 일치 확인

## SKILL.md 설계

이 프로젝트의 **가장 핵심적인 파일**. LLM이 도구를 사용하는 행동 패턴을 결정한다.
도구가 아무리 정확해도 LLM이 잘못된 패턴으로 사용하면 태스크 성공률이 떨어진다.

### 설계 원칙

1. **Act-Verify 루프 강제**: 매 액션 후 screenshot으로 결과 확인을 기본 패턴으로
2. **실패 복구 전략 명시**: "안 됐을 때 어떻게 하라"를 구체적으로
3. **좌표 정확도 팁**: 클릭 실패의 80%는 좌표 오차 → 예방법 제시
4. **토큰 최적화 가이드**: 언제 region/ocr/chain을 쓰면 좋은지 판단 기준
5. **간결함**: LLM 컨텍스트를 아끼기 위해 최소한의 토큰으로 최대 정보

### SKILL.md 구조

```markdown
---
name: computer-use
description: "Control mouse, keyboard, and capture screenshots.
Use when: (1) Take screenshots, (2) Click/drag/move mouse,
(3) Type text or press keyboard shortcuts, (4) Automate desktop interactions"
---

# Computer Use

## Quick Reference
| Action | Example |
|--------|---------|
| status | `computer-use status` |
| focus_window | `computer-use focus_window --params '{"process_name": "notepad.exe"}'` |
| screenshot | `computer-use screenshot` |
| left_click | `computer-use left_click --params '{"coordinate": [x, y]}'` |
| type | `computer-use type --params '{"text": "hello"}'` |
| key | `computer-use key --params '{"text": "ctrl+s"}'` |
| clipboard | `computer-use clipboard` |
| scroll | `computer-use scroll --params '{"coordinate": [x, y], "scroll_direction": "down", "scroll_amount": 3}'` |
(전체 21개 액션 테이블)

## Core Loop (반드시 따를 것)

0. **Init** - `status`로 환경 전체 파악 (모니터, 윈도우, 커서, 활성창) ← **최초 1회**
1. **Locate** - 타겟 앱이 활성창이 아니면 → focus_window로 전면 전환
2. **See** - screenshot으로 현재 화면 상태 확인
3. **Plan** - 어떤 UI 요소를 어떻게 조작할지 결정
4. **Act** - 하나의 액션 실행 (클릭, 타이핑 등)
5. **Verify** - screenshot으로 액션 결과 확인
6. **Repeat** - 목표 달성까지 반복

⚠ 절대 screenshot 없이 연속 액션 금지.
⚠ 한 번에 하나의 액션만. 여러 단계를 한꺼번에 하지 말 것.
⚠ 타겟 앱이 전면에 있는지 확신 없으면 → status 또는 windows로 확인 먼저.
⚠ 긴 텍스트 입력은 type 대신 clipboard 쓰기 + ctrl+v가 빠르고 안정적.

## Coordinate Tips

- 클릭 대상의 **정중앙**을 노릴 것. 텍스트 왼쪽 끝이 아닌 중앙.
- 작은 버튼(< 30px)은 screenshot --region으로 확대 후 좌표 재계산.
- 좌표를 추정할 때 주변 UI 요소 위치를 기준점으로 활용.
- 스크린샷의 좌상단이 (0, 0). x는 오른쪽, y는 아래쪽 증가.

## When Actions Fail

**클릭이 안 먹혔을 때:**
1. screenshot으로 현재 상태 확인
2. 의도한 위치와 실제 클릭 위치 비교
3. 좌표를 조정하여 재시도
4. 3회 실패 시 → 다른 방법 시도 (키보드 단축키, Tab 이동 등)

**UI가 예상과 다를 때:**
1. 로딩 중일 수 있음 → wait 1-2초 후 screenshot
2. 팝업/다이얼로그 → 먼저 처리 (닫기/확인)
3. 완전히 다른 화면 → 상태 재평가, 계획 수정

**타이핑이 안 될 때:**
1. 입력 필드에 포커스가 있는지 screenshot으로 확인
2. 포커스 없으면 → 먼저 입력 필드 클릭
3. 기존 텍스트 있으면 → ctrl+a로 전체 선택 후 type

## Token Optimization Guide

**screenshot (기본)**: ~1,049 tokens
- 전체 화면 상태 파악이 필요할 때

**screenshot --region x,y,w,h**: ~267 tokens (75% 절감)
- 특정 영역만 확인하면 될 때 (결과 확인, 작은 버튼 확대)

**screenshot --cursor_region w,h**: ~200 tokens (80% 절감)
- 우클릭 후 컨텍스트 메뉴, 툴팁, 호버 결과 확인
- 마우스 근처만 보면 되고 정확한 region 좌표를 모를 때

**screenshot --ocr**: ~85 tokens (90% 절감)
- 텍스트 내용만 알면 되고 UI 위치가 불필요할 때
- 에러 메시지 읽기, 상태 텍스트 확인

**chain**: 중간 screenshot 제거
- 확실한 연속 동작 (예: 필드 클릭 → 텍스트 입력 → Enter)
- 마지막에만 screenshot으로 결과 확인

**판단 기준:**
- "작업 시작, 뭐부터?" → status (~80 토큰, 환경 전체 파악)
- "어떤 앱이 열려있나?" → windows (~45 토큰, 스크린샷보다 95% 절약)
- "어디를 클릭해야 하나?" → screenshot (전체 이미지 필요)
- "클릭이 잘 됐나?" → screenshot --region (클릭 주변만)
- "우클릭 메뉴가 뭐가 있나?" → screenshot --cursor_region 200,300
- "텍스트가 뭐라고 써있나?" → screenshot --ocr
- "선택된 텍스트를 읽고 싶다" → key(ctrl+c) → clipboard (~15 토큰)
- "긴 텍스트를 입력해야 한다" → clipboard 쓰기 + key(ctrl+v) (type보다 안정적)
- "입력 후 Enter만 치면 됨" → chain

## Server Mode (Optional)

`computer-use serve`로 미리 서버를 시작하면 모든 응답이 10x 빨라진다.
서버 없어도 동작하지만 느림.

## Key Names
Modifiers: ctrl, alt, shift, super/cmd
Special: return, tab, backspace, delete, escape, space
Navigation: up, down, left, right, home, end, page_up, page_down
Function: f1-f20
Combos: ctrl+c, ctrl+shift+s, alt+tab
```

### SKILL.md 검증 방법

SKILL.md의 품질은 **LLM이 실제 태스크를 수행하는 성공률**로 측정:

| 태스크 | 성공 기준 |
|---|---|
| 메모장 열고 "Hello World" 입력 후 저장 | 파일 생성됨 |
| 브라우저에서 특정 URL 열기 | 페이지 로딩 완료 |
| 파일 탐색기에서 폴더 이동 | 원하는 폴더에 도착 |
| 설정 앱에서 특정 설정 변경 | 설정값 변경됨 |

이 태스크들을 SKILL.md 제공 후 LLM에게 수행시켜 성공률을 측정한다.
SKILL.md를 반복 개선하여 성공률을 높이는 것이 이 프로젝트의 최종 목표.
