# TapLite

TapLite is a lightweight Windows auto clicker built with Python and Tkinter. It uses the Windows `SendInput` API for mouse events and `RegisterHotKey` for global hotkeys.

## Features

- Left, right, or middle mouse button.
- Single-click or double-click actions.
- Millisecond click interval.
- Infinite repeat or a fixed repeat count.
- Current cursor position or fixed screen coordinates.
- Global hotkeys: `F6` toggles clicking, `F8` stops immediately.
- Local `settings.json` persistence.

TapLite does not bypass anti-cheat systems, inject into games, or click hidden background windows. If a game blocks simulated input, TapLite will not try to evade that behavior.

## Run

```powershell
python main.py
```

If the target game is running as administrator, start TapLite as administrator too.

## Test

```powershell
python -m pytest
```

## Package

Install PyInstaller and build a single executable:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --onefile --windowed --name TapLite main.py
```

The executable will be created under `dist\TapLite.exe`.
