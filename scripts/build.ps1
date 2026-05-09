Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $Root
try {
    python -m pytest
    python -m compileall main.py taplite tests
    python -m PyInstaller --onefile --windowed --name TapLite --icon assets\TapLite.ico main.py

    New-Item -ItemType Directory -Force -Path "releases" | Out-Null
    Copy-Item -Force -LiteralPath "dist\TapLite.exe" -Destination "releases\TapLite.exe"

    Write-Host "Build complete: releases\TapLite.exe"
}
finally {
    Pop-Location
}
