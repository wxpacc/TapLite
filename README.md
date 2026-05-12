# TapLite

[中文说明](README.zh-CN.md)

TapLite is a lightweight Windows auto clicker built with the Python standard library:

- `tkinter` for the desktop UI
- Windows `SendInput` for mouse input
- `RegisterHotKey` for global hotkeys
- local `json` settings storage

TapLite is intended for normal Windows desktop use. It does not bypass anti-cheat systems, inject into other processes, or provide hidden background automation.

## Download

- Latest release page: https://github.com/wxpacc/TapLite/releases/tag/v0.3.1
- Direct download: https://github.com/wxpacc/TapLite/releases/download/v0.3.1/TapLite.exe

## Version

Current version: `v0.3.1`

## Features

- Left / right / middle mouse button support
- Single-click and double-click modes
- Millisecond interval control
- Infinite loop or fixed repeat count
- Current cursor position or fixed screen coordinates
- Guided coordinate capture for fixed-position and multi-point setup
- Multi-point click list with per-point wait time
- Random interval and random offset options
- Start delay and run time limit
- Running-state overlay in the bottom-right corner
- System tray integration
- Single-instance startup behavior
- Custom global hotkeys for start/stop and emergency stop
- Local presets saved in `data/settings.json`

## Local Data

- TapLite stores settings and presets only in the local `data/settings.json` file beside the app.
- It does not upload configuration to any server.
- It does not write registry startup items, services, or other persistent background components.
- To remove the app and all local data, delete the TapLite folder directly. No extra residue is left behind.

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
