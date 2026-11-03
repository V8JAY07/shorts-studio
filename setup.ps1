$ErrorActionPreference = "Stop"
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { Write-Host "Install Python 3.12 first: https://www.python.org/downloads/windows/"; exit 1 }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Write-Host "Install FFmpeg: winget install -e --id Gyan.FFmpeg"; exit 1 }
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (Get-Command ollama -ErrorAction SilentlyContinue) { ollama pull qwen3:1.7b } else { Write-Host "Install Ollama: https://ollama.com/download/windows"; exit 1 }
Write-Host "Setup complete. Run .\run.ps1"
