# TapLite

[中文说明](README.zh-CN.md)

TapLite is a lightweight Windows auto clicker built with the Python standard library:

- `tkinter` for the desktop UI
- Windows `SendInput` for mouse events
- `RegisterHotKey` for global hotkeys
- local `json` settings storage

TapLite is designed for normal desktop use on Windows. It does not bypass anti-cheat systems, inject into game processes, or provide hidden background clicking for other windows.

## Download

- Latest release page: https://github.com/wxpacc/TapLite/releases/tag/v0.3.0
- Direct download: https://github.com/wxpacc/TapLite/releases/download/v0.3.0/TapLite.exe

## Version

Current version: `v0.3.0`

## Features

- Left / right / middle mouse button support
- Single-click and double-click modes
- Millisecond interval control
- Infinite loop or fixed repeat count
- Current cursor position or fixed screen coordinates
- Multi-point click list with per-point wait time
- Random interval and random offset options
- Start delay and run time limit
- Running-state overlay in the bottom-right corner
- System tray integration
- Single-instance startup behavior
- Local presets saved in `data/settings.json`
- Default global hotkeys: `F6` start/stop, `F8` emergency stop

## Run from Source

```powershell
python main.py
```

If the target program is running as administrator, start TapLite as administrator too.

## Build

```powershell
.\scripts\build.ps1
```

The build uses `assets/TapLite.ico` as the application icon and outputs:

```text
releases\TapLite.exe
```

## Development Checks

```powershell
python -m pytest
python -m compileall main.py taplite tests
```

## Project Layout

```text
TapLite/
├─ assets/
├─ taplite/
├─ tests/
├─ scripts/
├─ docs/
├─ releases/
├─ .github/
├─ main.py
├─ pyproject.toml
└─ README.md
```

See also: [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)

## Safety Boundary

- No anti-cheat bypass
- No hidden process tricks
- No background injection
- No driver-level input
- No privilege bypass attempts
