$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller pillow

python .\tools\make_icon.py

pyinstaller --noconfirm --clean --noconsole --onefile --name Windic --icon .\assets\windic.ico .\app.py

Write-Host "Build completed: .\dist\Windic.exe"
