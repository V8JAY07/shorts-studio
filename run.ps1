$ErrorActionPreference = "Stop"
if (-not (Test-Path ".\.venv\Scripts\streamlit.exe")) { Write-Host "Run .\setup.ps1 first"; exit 1 }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Write-Host "FFmpeg missing. Install: winget install -e --id Gyan.FFmpeg"; exit 1 }
& .\.venv\Scripts\streamlit.exe run .\app.py
