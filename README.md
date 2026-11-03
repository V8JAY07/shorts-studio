# Shorts Studio — Windows / 8 GB RAM

A lightweight, local-first YouTube Shorts draft creator. Ollama is the free default. Optional GPT and Claude APIs can write scripts. The app can retrieve available YouTube transcripts, generate offline Windows narration, create vertical title-card scenes with Pillow, and render an MP4 with FFmpeg. It does not upload or publish videos.

## Requirements
- Windows 10/11 64-bit
- Python 3.12
- FFmpeg on PATH
- Ollama for local/free AI

## Install
1. Install Python: https://www.python.org/downloads/windows/
2. Install FFmpeg in PowerShell: `winget install -e --id Gyan.FFmpeg`
3. Install Ollama: https://ollama.com/download/windows
4. Open PowerShell in this folder and run:
   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\setup.ps1
   ```
5. Start it:
   ```powershell
   .\run.ps1
   ```
6. Open `http://localhost:8501` if the browser does not open automatically.

## Use
1. Enter a topic and select a duration/style.
2. Optionally paste YouTube links and click **Gather research**. Transcript retrieval only works when captions are available and YouTube permits the request. Optional web search uses the `ddgs` package.
3. Choose Ollama, GPT, or Claude in the sidebar. Ollama is the no-API-cost default. For GPT/Claude, enter your API key in the password field. The app does not save keys.
4. Generate and edit the script.
5. Choose a Windows voice, optionally upload music you have rights to use, and render.
6. Preview and download the MP4. Publishing remains manual.

## Models and billing
The setup pulls `qwen3:1.7b` for modest hardware. Check installed models with `ollama list`. If a GPT/Claude model name is unavailable, replace it in the sidebar with one enabled for your API account. API use is separate from most ChatGPT/Claude chat subscriptions and may be billed separately.

## Notes and limitations
- This starter creates stylized typographic scene cards, not AI-generated moving footage. It is intentionally lightweight for 8 GB RAM.
- Windows offline speech depends on installed SAPI voices. It uses `pyttsx3` and does not send narration to a cloud service.
- YouTube transcript retrieval and optional web search require internet.
- Close memory-heavy apps while rendering. Keep scripts concise on an 8 GB PC.
- Use only footage, music, images and voices you have permission to use.

## Troubleshooting
- Ollama connection refused: launch Ollama from Start Menu and retry.
- FFmpeg not found: reopen PowerShell after installing; test `ffmpeg -version`.
- Transcript unavailable: video may have no captions, be restricted, or YouTube may throttle requests.
- API error: check API key, account billing, model name and limits.
- No speech output: check Windows sound output and installed speech voices.

## Privacy
Ollama prompts are sent to your local Ollama service. Selecting GPT or Claude sends the prompt to that provider. Transcript retrieval sends requests to YouTube-related endpoints. Optional web search sends the query to the search service. Do not paste confidential material unless you are comfortable sharing it with the selected service.
