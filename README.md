# Windic

Compact Windows 11 tray translator that uses Google Translate.

## Features

- Runs in system tray.
- Does not appear in taskbar when opened.
- Can auto-start with Windows login (HKCU Run).
- Global hotkey to open/hide panel: `Ctrl+Shift+Space`.
- Custom app icon for tray and EXE.
- Minimal UI with only two side-by-side rounded boxes:
	- Left: searched word input.
	- Right: translated explanation/output.

## Requirements

- Windows 11
- Python 3.11+

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## One-click Install + Run (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File .\install_and_run.ps1
```

This script now starts the app with a visible panel on first run (`--show`).
After that, the app stays in system tray and can be toggled with `Ctrl+Shift+Space`.

## Run

```bash
python app.py
```

The app starts hidden in tray. Use `Ctrl+Shift+Space` to show/hide.

## Build EXE (optional)

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name Windic app.py
```

Recommended single-command build on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

After build, run `dist\Windic.exe`. The app still registers startup automatically.

## Notes

- Translation target is Turkish (`dest="tr"`).
- If Google Translate is temporarily unreachable, output box shows a fallback message.
