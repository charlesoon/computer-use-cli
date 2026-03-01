# Integration Test Results

- Date: 2026-03-02 03:13:55
- Iterations per TC: 12 (+ 2 warmup)
- Mode: Fallback (no server)
- Platform: Windows
- Python startup overhead: ~320ms (subprocess creation + interpreter init)
- Import + Backend init overhead: ~370ms (mss + pynput + Pillow loading)

## Summary Table

| Test Case | Avg e2e (ms) | P50 (ms) | P95 (ms) | Min (ms) | Max (ms) | Threshold (ms) | Tokens | Pass Rate |
|---|---|---|---|---|---|---|---|---|
| screenshot | 1056.8 | 1045.1 | 1159.3 | 1007.3 | 1159.3 | 500 | 1533 | 12/12 SLOW |
| screenshot_region | 979.6 | 971.7 | 1081.5 | 949.7 | 1081.5 | 400 | 1533 | 12/12 SLOW |
| screenshot_cursor_region | 976.5 | 968.1 | 1025.2 | 957.8 | 1025.2 | 500 | 1533 | 12/12 SLOW |
| status | 771.5 | 758.8 | 841.1 | 710.6 | 841.1 | 300 | 1432 | 12/12 SLOW |
| windows | 765.8 | 786.0 | 810.2 | 716.0 | 810.2 | 200 | 1319 | 12/12 SLOW |
| monitors | 732.7 | 735.8 | 772.1 | 692.3 | 772.1 | 200 | 65 | 12/12 SLOW |
| cursor_position | 760.1 | 790.5 | 804.7 | 695.8 | 804.7 | 200 | 6 | 12/12 SLOW |
| clipboard_write | 758.8 | 756.1 | 803.0 | 713.9 | 803.0 | 200 | 4 | 12/12 SLOW |
| clipboard_read | 741.0 | 718.2 | 804.8 | 707.5 | 804.8 | 200 | 4 | 12/12 SLOW |
| mouse_move | 767.2 | 781.1 | 825.1 | 707.7 | 825.1 | 200 | 6 | 12/12 SLOW |
| scroll | 769.3 | 781.3 | 834.4 | 700.1 | 834.4 | 200 | 18 | 12/12 SLOW |
| type_text | 742.2 | 729.1 | 796.4 | 707.9 | 796.4 | 300 | 1 | 12/12 SLOW |
| key_press | 745.3 | 724.3 | 842.3 | 701.1 | 842.3 | 200 | 1 | 12/12 SLOW |
| wait | 773.6 | 791.1 | 831.7 | 713.0 | 831.7 | 400 | 4 | 12/12 SLOW |
| double_click | 772.0 | 785.0 | 829.9 | 720.0 | 829.9 | 200 | 6 | 12/12 SLOW |
| hold_key | 817.3 | 829.8 | 869.3 | 763.5 | 869.3 | 500 | 1 | 12/12 SLOW |
| chain_2actions | 740.5 | 743.2 | 774.9 | 693.7 | 774.9 | 500 | 19 | 12/12 SLOW |
| format_openai_click | 759.3 | 747.4 | 851.2 | 710.4 | 851.2 | 300 | 6 | 12/12 SLOW |
| focus_window | 770.1 | 745.7 | 874.6 | 709.4 | 874.6 | 300 | 46 | 12/12 SLOW |

## Optimization History

### Round 1: Initial baseline (before optimizations)

| TC | Before (ms) | Issue |
|---|---|---|
| clipboard_write | 1551 | powershell subprocess for clipboard operations |
| clipboard_read | 1479 | powershell subprocess for clipboard operations |
| screenshot | 1177 | High PNG compression level (default=6) |

### Round 2: Clipboard ctypes fix

**Change**: Replaced powershell subprocess with proper Win32 ctypes API (OpenClipboard/GetClipboardData/SetClipboardData with correct 64-bit pointer types)

**Files modified**: `src/computer_use/platform/windows.py` - `get_clipboard()`, `set_clipboard()`

| TC | Before (ms) | After (ms) | Improvement |
|---|---|---|---|
| clipboard_write | 1551 | 759 | **-51%** |
| clipboard_read | 1479 | 741 | **-50%** |

**Root cause**: powershell process spawn added ~800ms per call. ctypes direct Win32 API call is <5ms.

### Round 3: PNG compression optimization

**Change**: Reduced PNG compress_level from default (6) to 1 in both capture_screenshot() and screenshot handler _image_to_png_bytes()

**Files modified**: `src/computer_use/platform/windows.py`, `src/computer_use/actions/screenshot.py`

| TC | Before (ms) | After (ms) | Improvement |
|---|---|---|---|
| screenshot | 1177 | 1057 | **-10%** |
| screenshot_region | 1097 | 980 | **-11%** |

### Round 4: Backend singleton

**Change**: Made PlatformBackend a singleton via `get_backend()` factory cache. Avoids reinitializing mss/pynput on repeated calls within same process (relevant for chain and server mode).

**Files modified**: `src/computer_use/platform/__init__.py`

### Performance breakdown (after all optimizations)

| Component | Time (ms) | Notes |
|---|---|---|
| Python subprocess start | ~320 | OS process creation + Python interpreter |
| Module imports | ~100 | computer_use package modules |
| Backend init (first call) | ~280 | mss.mss() + pynput Controllers |
| Action execution | 1-5 | Actual mouse/keyboard/query operations |
| Screenshot capture | ~100 | mss.grab() + PIL convert |
| Screenshot resize | ~100 | Pillow LANCZOS |
| Screenshot PNG encode | ~150 | compress_level=1 |
| File I/O | ~10 | Write PNG to disk |

**Key insight**: ~690ms of every CLI call is fixed Python startup + import overhead. Server mode eliminates this by keeping the process alive, reducing action latency to <50ms.

## Detailed Results Per TC

### screenshot

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 1007.3 | 685.7 | 1533 | OK |
| 2 | 1037.0 | 709.3 | 1533 | OK |
| 3 | 1038.2 | 711.2 | 1533 | OK |
| 4 | 1051.9 | 719.2 | 1533 | OK |
| 5 | 1026.8 | 704.8 | 1533 | OK |
| 6 | 1053.0 | 708.4 | 1533 | OK |
| 7 | 1031.9 | 710.9 | 1533 | OK |
| 8 | 1159.3 | 774.3 | 1533 | OK |
| 9 | 1074.7 | 748.8 | 1533 | OK |
| 10 | 1057.5 | 721.4 | 1533 | OK |
| 11 | 1026.3 | 706.4 | 1533 | OK |
| 12 | 1117.3 | 731.4 | 1533 | OK |

### screenshot_region

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 986.3 | 660.4 | 1533 | OK |
| 2 | 963.5 | 619.4 | 1533 | OK |
| 3 | 969.4 | 641.2 | 1533 | OK |
| 4 | 982.6 | 643.9 | 1533 | OK |
| 5 | 970.3 | 645.4 | 1533 | OK |
| 6 | 971.2 | 640.5 | 1533 | OK |
| 7 | 972.2 | 642.2 | 1533 | OK |
| 8 | 1081.5 | 703.6 | 1533 | OK |
| 9 | 973.8 | 650.7 | 1533 | OK |
| 10 | 982.7 | 644.4 | 1533 | OK |
| 11 | 949.7 | 627.7 | 1533 | OK |
| 12 | 951.7 | 627.5 | 1533 | OK |

### screenshot_cursor_region

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 1025.2 | 695.4 | 1533 | OK |
| 2 | 962.6 | 619.7 | 1533 | OK |
| 3 | 979.7 | 657.9 | 1533 | OK |
| 4 | 959.4 | 628.5 | 1533 | OK |
| 5 | 974.3 | 649.2 | 1533 | OK |
| 6 | 965.5 | 640.7 | 1533 | OK |
| 7 | 994.0 | 663.6 | 1533 | OK |
| 8 | 959.4 | 629.7 | 1533 | OK |
| 9 | 1004.4 | 680.5 | 1533 | OK |
| 10 | 957.8 | 621.4 | 1533 | OK |
| 11 | 970.5 | 652.5 | 1533 | OK |
| 12 | 965.8 | 641.9 | 1533 | OK |

### status

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 782.1 | 390.3 | 1432 | OK |
| 2 | 749.3 | 417.3 | 1432 | OK |
| 3 | 710.6 | 392.2 | 1432 | OK |
| 4 | 746.6 | 411.2 | 1432 | OK |
| 5 | 768.4 | 386.8 | 1432 | OK |
| 6 | 826.4 | 428.0 | 1432 | OK |
| 7 | 833.5 | 457.5 | 1432 | OK |
| 8 | 841.1 | 468.4 | 1432 | OK |
| 9 | 717.2 | 397.1 | 1432 | OK |
| 10 | 826.2 | 420.6 | 1432 | OK |
| 11 | 728.8 | 399.0 | 1432 | OK |
| 12 | 728.4 | 393.6 | 1432 | OK |

### windows

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 733.8 | 413.8 | 1319 | OK |
| 2 | 799.2 | 394.2 | 1319 | OK |
| 3 | 717.2 | 399.1 | 1319 | OK |
| 4 | 716.0 | 385.9 | 1319 | OK |
| 5 | 802.4 | 415.5 | 1319 | OK |
| 6 | 790.6 | 388.8 | 1319 | OK |
| 7 | 791.3 | 398.1 | 1319 | OK |
| 8 | 720.4 | 401.7 | 1319 | OK |
| 9 | 810.2 | 431.7 | 1319 | OK |
| 10 | 731.0 | 396.9 | 1319 | OK |
| 11 | 781.4 | 387.4 | 1319 | OK |
| 12 | 796.4 | 401.9 | 1319 | OK |

### monitors

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 702.0 | 380.7 | 65 | OK |
| 2 | 729.4 | 413.5 | 65 | OK |
| 3 | 772.1 | 441.5 | 65 | OK |
| 4 | 704.0 | 385.8 | 65 | OK |
| 5 | 742.2 | 402.4 | 65 | OK |
| 6 | 761.7 | 376.4 | 65 | OK |
| 7 | 767.9 | 438.0 | 65 | OK |
| 8 | 692.3 | 373.6 | 65 | OK |
| 9 | 761.0 | 427.4 | 65 | OK |
| 10 | 705.9 | 385.5 | 65 | OK |
| 11 | 707.8 | 373.5 | 65 | OK |
| 12 | 745.6 | 372.1 | 65 | OK |

### cursor_position

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 726.0 | 397.8 | 6 | OK |
| 2 | 794.8 | 402.1 | 6 | OK |
| 3 | 801.0 | 432.4 | 6 | OK |
| 4 | 795.7 | 410.0 | 6 | OK |
| 5 | 795.0 | 392.1 | 6 | OK |
| 6 | 695.8 | 377.5 | 6 | OK |
| 7 | 799.8 | 394.2 | 6 | OK |
| 8 | 704.9 | 381.5 | 6 | OK |
| 9 | 804.7 | 400.9 | 6 | OK |
| 10 | 786.2 | 416.2 | 6 | OK |
| 11 | 717.0 | 394.7 | 6 | OK |
| 12 | 700.5 | 385.0 | 6 | OK |

### clipboard_write

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 777.6 | 446.9 | 4 | OK |
| 2 | 754.3 | 381.8 | 4 | OK |
| 3 | 733.2 | 404.1 | 4 | OK |
| 4 | 752.5 | 431.7 | 4 | OK |
| 5 | 789.1 | 393.2 | 4 | OK |
| 6 | 792.6 | 399.0 | 4 | OK |
| 7 | 781.7 | 396.9 | 4 | OK |
| 8 | 757.9 | 389.6 | 4 | OK |
| 9 | 723.1 | 399.7 | 4 | OK |
| 10 | 803.0 | 407.6 | 4 | OK |
| 11 | 726.9 | 393.9 | 4 | OK |
| 12 | 713.9 | 390.8 | 4 | OK |

### clipboard_read

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 715.3 | 398.8 | 4 | OK |
| 2 | 791.9 | 394.4 | 4 | OK |
| 3 | 715.4 | 396.6 | 4 | OK |
| 4 | 714.2 | 391.4 | 4 | OK |
| 5 | 779.7 | 396.4 | 4 | OK |
| 6 | 796.0 | 393.0 | 4 | OK |
| 7 | 719.6 | 397.2 | 4 | OK |
| 8 | 708.5 | 383.4 | 4 | OK |
| 9 | 707.5 | 385.4 | 4 | OK |
| 10 | 716.9 | 384.8 | 4 | OK |
| 11 | 804.8 | 434.1 | 4 | OK |
| 12 | 722.2 | 393.4 | 4 | OK |

### mouse_move

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 716.8 | 398.1 | 6 | OK |
| 2 | 707.7 | 382.9 | 6 | OK |
| 3 | 819.8 | 456.0 | 6 | OK |
| 4 | 792.3 | 414.6 | 6 | OK |
| 5 | 719.4 | 400.2 | 6 | OK |
| 6 | 825.1 | 437.3 | 6 | OK |
| 7 | 800.8 | 418.9 | 6 | OK |
| 8 | 727.8 | 400.4 | 6 | OK |
| 9 | 782.6 | 390.2 | 6 | OK |
| 10 | 715.5 | 391.1 | 6 | OK |
| 11 | 779.6 | 391.6 | 6 | OK |
| 12 | 819.6 | 432.0 | 6 | OK |

### scroll

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 771.9 | 381.5 | 18 | OK |
| 2 | 738.9 | 406.0 | 18 | OK |
| 3 | 821.9 | 448.6 | 18 | OK |
| 4 | 794.1 | 428.0 | 18 | OK |
| 5 | 808.9 | 430.4 | 18 | OK |
| 6 | 715.7 | 392.5 | 18 | OK |
| 7 | 805.0 | 430.8 | 18 | OK |
| 8 | 725.7 | 396.3 | 18 | OK |
| 9 | 700.1 | 380.7 | 18 | OK |
| 10 | 790.7 | 399.4 | 18 | OK |
| 11 | 834.4 | 457.0 | 18 | OK |
| 12 | 724.6 | 397.0 | 18 | OK |

### type_text

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 713.1 | 394.7 | 1 | OK |
| 2 | 707.9 | 393.8 | 1 | OK |
| 3 | 776.0 | 397.9 | 1 | OK |
| 4 | 720.1 | 398.3 | 1 | OK |
| 5 | 730.8 | 399.2 | 1 | OK |
| 6 | 794.6 | 402.6 | 1 | OK |
| 7 | 717.1 | 385.7 | 1 | OK |
| 8 | 728.4 | 406.7 | 1 | OK |
| 9 | 729.8 | 402.6 | 1 | OK |
| 10 | 796.4 | 401.8 | 1 | OK |
| 11 | 781.6 | 386.6 | 1 | OK |
| 12 | 710.8 | 387.2 | 1 | OK |

### key_press

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 721.3 | 396.4 | 1 | OK |
| 2 | 701.1 | 387.8 | 1 | OK |
| 3 | 725.0 | 397.5 | 1 | OK |
| 4 | 768.9 | 384.3 | 1 | OK |
| 5 | 723.6 | 396.7 | 1 | OK |
| 6 | 774.3 | 387.2 | 1 | OK |
| 7 | 842.3 | 452.7 | 1 | OK |
| 8 | 710.5 | 390.5 | 1 | OK |
| 9 | 711.1 | 393.6 | 1 | OK |
| 10 | 719.3 | 399.3 | 1 | OK |
| 11 | 816.0 | 437.3 | 1 | OK |
| 12 | 730.7 | 415.9 | 1 | OK |

### wait

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 828.6 | 442.1 | 4 | OK |
| 2 | 797.9 | 404.8 | 4 | OK |
| 3 | 724.7 | 402.4 | 4 | OK |
| 4 | 713.0 | 399.6 | 4 | OK |
| 5 | 831.7 | 459.9 | 4 | OK |
| 6 | 716.3 | 401.4 | 4 | OK |
| 7 | 818.8 | 443.3 | 4 | OK |
| 8 | 816.6 | 444.4 | 4 | OK |
| 9 | 724.4 | 400.6 | 4 | OK |
| 10 | 797.0 | 407.1 | 4 | OK |
| 11 | 729.6 | 411.7 | 4 | OK |
| 12 | 785.2 | 402.1 | 4 | OK |

### double_click

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 723.8 | 395.5 | 6 | OK |
| 2 | 722.4 | 404.1 | 6 | OK |
| 3 | 782.5 | 382.6 | 6 | OK |
| 4 | 810.5 | 419.3 | 6 | OK |
| 5 | 812.1 | 434.0 | 6 | OK |
| 6 | 829.9 | 466.3 | 6 | OK |
| 7 | 727.8 | 397.3 | 6 | OK |
| 8 | 720.0 | 403.1 | 6 | OK |
| 9 | 801.5 | 400.8 | 6 | OK |
| 10 | 787.4 | 397.4 | 6 | OK |
| 11 | 818.3 | 428.4 | 6 | OK |
| 12 | 727.5 | 409.3 | 6 | OK |

### hold_key

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 763.5 | 436.3 | 1 | OK |
| 2 | 825.6 | 442.6 | 1 | OK |
| 3 | 775.0 | 445.5 | 1 | OK |
| 4 | 859.8 | 496.4 | 1 | OK |
| 5 | 866.3 | 485.3 | 1 | OK |
| 6 | 771.4 | 454.4 | 1 | OK |
| 7 | 777.3 | 450.2 | 1 | OK |
| 8 | 834.4 | 448.0 | 1 | OK |
| 9 | 834.0 | 446.2 | 1 | OK |
| 10 | 869.3 | 480.3 | 1 | OK |
| 11 | 864.1 | 480.2 | 1 | OK |
| 12 | 766.5 | 444.3 | 1 | OK |

### chain_2actions

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 763.6 | 440.4 | 19 | OK |
| 2 | 774.9 | 442.6 | 19 | OK |
| 3 | 754.3 | 378.1 | 19 | OK |
| 4 | 771.3 | 392.6 | 19 | OK |
| 5 | 755.3 | 438.7 | 19 | OK |
| 6 | 719.0 | 397.8 | 19 | OK |
| 7 | 766.7 | 440.5 | 19 | OK |
| 8 | 703.7 | 388.8 | 19 | OK |
| 9 | 732.1 | 402.7 | 19 | OK |
| 10 | 693.7 | 374.8 | 19 | OK |
| 11 | 720.6 | 392.9 | 19 | OK |
| 12 | 730.9 | 413.9 | 19 | OK |

### format_openai_click

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 851.2 | 462.9 | 6 | OK |
| 2 | 784.2 | 392.6 | 6 | OK |
| 3 | 748.6 | 423.0 | 6 | OK |
| 4 | 711.2 | 393.8 | 6 | OK |
| 5 | 816.1 | 413.7 | 6 | OK |
| 6 | 719.0 | 399.4 | 6 | OK |
| 7 | 734.8 | 413.3 | 6 | OK |
| 8 | 710.4 | 397.1 | 6 | OK |
| 9 | 765.2 | 434.7 | 6 | OK |
| 10 | 723.4 | 399.8 | 6 | OK |
| 11 | 746.2 | 410.4 | 6 | OK |
| 12 | 801.6 | 428.3 | 6 | OK |

### focus_window

| Iter | e2e (ms) | internal (ms) | tokens | pass |
|---|---|---|---|---|
| 1 | 748.6 | 417.3 | 46 | OK |
| 2 | 709.4 | 389.9 | 46 | OK |
| 3 | 874.6 | 481.7 | 46 | OK |
| 4 | 807.2 | 422.9 | 46 | OK |
| 5 | 845.3 | 461.3 | 46 | OK |
| 6 | 805.2 | 409.8 | 46 | OK |
| 7 | 739.2 | 402.7 | 46 | OK |
| 8 | 786.1 | 405.1 | 46 | OK |
| 9 | 742.8 | 414.2 | 46 | OK |
| 10 | 724.0 | 405.5 | 46 | OK |
| 11 | 731.5 | 400.2 | 46 | OK |
| 12 | 727.9 | 409.9 | 46 | OK |
